#!/usr/bin/env bash

set -eo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
FAST=0
[[ "${1:-}" == "--fast" ]] && FAST=1

# ── Couleurs ──────────────────────────────────────────────────────────────────
R='\033[0;31m'; G='\033[0;32m'; Y='\033[1;33m'
B='\033[0;34m'; BOLD='\033[1m'; NC='\033[0m'

log()    { echo -e "${BOLD}${B}[>]${NC} $*"; }
ok()     { echo -e "${G}[✓]${NC} $*"; }
err()    { echo -e "${R}[✗]${NC} $*"; }
warn()   { echo -e "${Y}[!]${NC} $*"; }
section(){ echo -e "\n${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"; \
           echo -e "${BOLD}  $*${NC}"; \
           echo -e "${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"; }

# ── Liste des services ────────────────────────────────────────────────────────
# Format : "NOM_AFFICHAGE|CHEMIN_RELATIF"
SERVICES=(
    "API Gateway|backend/api-gateway"
    "Analyze Service|backend/services/analyze"
    "Configuration Service|backend/services/configuration"
    "Collection Service|backend/services/collection"
)

# ── Gestion du venv ───────────────────────────────────────────────────────────
# En contexte CI (variable CI=true) ou si un venv est déjà actif, on saute
# la création du venv pour utiliser l'environnement Python existant.
if [[ -z "${CI:-}" && -z "${VIRTUAL_ENV:-}" ]]; then
    VENV="$SCRIPT_DIR/.venv"
    if [[ ! -f "$VENV/bin/activate" ]]; then
        log "Création du venv Python à : $VENV"
        python3 -m venv "$VENV"
    fi
    # shellcheck source=/dev/null
    source "$VENV/bin/activate"
    log "venv activé  →  $VIRTUAL_ENV"
else
    log "Environnement Python détecté : ${VIRTUAL_ENV:-CI/système}"
fi

# ── Mise à jour de pip ────────────────────────────────────────────────────────
pip install --quiet --upgrade pip || warn "Impossible de mettre à jour pip — ignoré"

# ── Charger le .env global ────────────────────────────────────────────────────
# Un seul fichier .env à la racine du projet — toutes les variables
# de base de données sont préfixées par service (ANALYZE_*, COLLECTION_*, etc.)
if [[ -f "$SCRIPT_DIR/.env" ]]; then
    set -a
    # shellcheck disable=SC1090
    source "$SCRIPT_DIR/.env"
    set +a
    log "Variables d'environnement chargées depuis $SCRIPT_DIR/.env"
else
    warn "Aucun fichier .env trouvé à $SCRIPT_DIR — utilisation des valeurs par défaut"
fi

# ── Variables de résultat ─────────────────────────────────────────────────────
declare -a PASSED_SERVICES=()
declare -a FAILED_SERVICES=()
START=$SECONDS

# ══════════════════════════════════════════════════════════════════════════════
#  Boucle principale
# ══════════════════════════════════════════════════════════════════════════════
for entry in "${SERVICES[@]}"; do
    name="${entry%%|*}"
    relpath="${entry##*|}"
    svcdir="$SCRIPT_DIR/$relpath"

    section "Service : $name  ($relpath)"

    # Vérification que le répertoire existe
    if [[ ! -d "$svcdir" ]]; then
        err "Répertoire introuvable : $svcdir — service ignoré"
        FAILED_SERVICES+=("$name  (répertoire manquant)")
        continue
    fi

    # Vérification que requirements.txt existe
    if [[ ! -f "$svcdir/requirements.txt" ]]; then
        err "Fichier requirements.txt manquant dans $svcdir — service ignoré"
        FAILED_SERVICES+=("$name  (requirements.txt manquant)")
        continue
    fi

    # ── Installation des dépendances ──────────────────────────────────────────
    if [[ $FAST -eq 0 ]]; then
        log "Installation des dépendances pip..."
        if pip install --quiet -r "$svcdir/requirements.txt" 2>&1; then
            # kafka-python et kafka-python-ng partagent le même namespace 'kafka'.
            # Si les deux sont présents, réinstaller kafka-python-ng pour garantir
            # un état cohérent.
            if pip show kafka-python &>/dev/null && pip show kafka-python-ng &>/dev/null; then
                warn "kafka-python et kafka-python-ng coexistent — suppression de kafka-python"
                pip uninstall -y kafka-python &>/dev/null || true
                pip install --quiet --force-reinstall kafka-python-ng &>/dev/null || true
            fi
            ok "Dépendances installées"
        else
            err "Échec pip install pour $name — service ignoré"
            FAILED_SERVICES+=("$name  (pip install)")
            continue
        fi
    else
        warn "Mode --fast : réinstallation pip ignorée"
    fi

    # ── Exécution de pytest ───────────────────────────────────────────────────
    log "Lancement de pytest (avec couverture)..."
    # Les options --cov et --cov-report=xml sont définies dans pytest.ini.
    # Les coverage.xml générés ici ont des chemins locaux absolus (usage local).
    # Pour SonarQube, les coverage.xml sont regénérés avec les bons chemins
    # (/usr/src/...) par le service test-runner dans docker-compose.sonar.yml.
    if (cd "$svcdir" && python -m pytest); then
        ok "Tous les tests passent ✅  →  ${BOLD}$name${NC}"
        PASSED_SERVICES+=("$name")
    else
        err "Des tests ont ÉCHOUÉ ❌  →  ${BOLD}$name${NC}"
        FAILED_SERVICES+=("$name")
    fi
done

# ── Durée d'exécution ─────────────────────────────────────────────────────────
ELAPSED=$((SECONDS - START))

# ══════════════════════════════════════════════════════════════════════════════
#  RÉSUMÉ GLOBAL
# ══════════════════════════════════════════════════════════════════════════════
echo ""
echo -e "${BOLD}══════════════════════════════════════════════════════${NC}"
echo -e "${BOLD}  RÉSUMÉ DES TESTS  —  $(date '+%H:%M:%S')  —  ${ELAPSED}s${NC}"
echo -e "${BOLD}══════════════════════════════════════════════════════${NC}"

TOTAL=$(( ${#PASSED_SERVICES[@]} + ${#FAILED_SERVICES[@]} ))
for s in "${PASSED_SERVICES[@]}"; do ok "$s"; done
for s in "${FAILED_SERVICES[@]}"; do err "$s"; done

echo ""
if [[ ${#FAILED_SERVICES[@]} -gt 0 ]]; then
    err "${#FAILED_SERVICES[@]}/${TOTAL} service(s) en ÉCHEC — code de sortie : 1"
    exit 1
else
    ok "Tous les ${TOTAL}/${TOTAL} services passent ✅"
    exit 0
fi
