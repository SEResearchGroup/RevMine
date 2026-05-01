"""
Test de robustesse du pipeline CI/CD
======================================
Ce fichier contient une fonction de test VOLONTAIREMENT CASSÉE pour démontrer
que le pipeline échoue correctement (stage 'test') lorsqu'un test échoue.

─── COMMENT L'UTILISER ───────────────────────────────────────────────────────
1. Pour déclencher l'échec du pipeline :
   Décommentez la fonction `test_pipeline_must_fail()` ci-dessous, puis
   poussez ce fichier sur GitLab.

2. Résultat attendu :
   - Le job pytest (ex: test:api-gateway) échoue avec un AssertionError.
   - Le stage 'quality' (SonarQube) ne démarre PAS (bloqué par l'échec).
   - Le pipeline est marqué FAILED ❌.
   - Vous recevez une notification GitLab d'échec.

3. Pour revenir à un état normal :
   Recommentez (ou supprimez) la fonction `test_pipeline_must_fail()` et
   poussez à nouveau. Le pipeline repasse au vert ✅.

─── EMPLACEMENT ─────────────────────────────────────────────────────────────
Ce fichier est placé dans backend/api-gateway/ pour être découvert
automatiquement par pytest (correspond au pattern test_*.py).
Vous pouvez le copier/déplacer vers n'importe quel autre service.
─────────────────────────────────────────────────────────────────────────────
"""


# ── Exemple de test cassé — DÉCOMMENTEZ pour provoquer l'échec ───────────────
#
# def test_pipeline_must_fail():
#     """
#     Ce test échoue INTENTIONNELLEMENT pour valider le comportement du pipeline.
#     Il doit provoquer FAILED sur GitLab.
#     """
#     assert 1 == 2, (
#         "ÉCHEC INTENTIONNEL — ce test vérifie que le pipeline CI/CD "
#         "détecte correctement un test cassé."
#     )


# ── Test normal (toujours actif) ──────────────────────────────────────────────
def test_pipeline_is_healthy():
    """
    Test sentinelle — doit toujours passer.
    Indique que le pipeline est dans un état sain.
    """
    assert True, "Le pipeline est sain : ce test ne doit jamais échouer."
