# Welcome to RevMine

**RevMine** is an open-source tool for *mining and analyzing modern code review data*. It connects to your Git hosting provider (GitHub or GitLab), collects merge/pull request activity, and surfaces process metrics — lead time, rework, review size, reviewer workload, and more — through an interactive dashboard with an LLM-assisted exploration interface.

RevMine is designed for researchers and practitioners who want reproducible, end-to-end code review analytics without stitching together ad-hoc scripts.

### Key features

- **Multi-provider collection** — pull review history from GitHub and GitLab via OAuth.
- **Process analytics** — lead time, rework size, review iteration counts, and distribution histograms with adaptive binning and time-based filters.
- **LLM-assisted insights** — ask natural-language questions over collected data (via local Ollama or OpenRouter-hosted models).
- **Microservice architecture** — each concern (collection, configuration, analysis, notification, LLM) runs as an independent service, orchestrated with Docker Compose.
- **Observability built in** — Grafana + Loki + Promtail for logs out of the box.

### Paper

If you use RevMine in your research, please cite our paper:

> *RevMine: A Tool for Mining and Analyzing Modern Code Review Data* — **[link to paper](#)** *(https://ieeexplore.ieee.org/abstract/document/11344241)*

```bibtex
@inproceedings{revmine,
  title     = {RevMine: A Tool for Mining and Analyzing Modern Code Review Data},
  author    = {Kansab, Samah and others},
  year      = {2026},
  note      = {TODO: fill in venue / DOI}
}
```

---

## Architecture

| Service | Port | Stack |
|---|---|---|
| Frontend | 5173 | React + Vite |
| API Gateway | 8000 | Django |
| Configuration Service | 8001 | Django |
| Collection Service | 8002 | Django |
| Analyze Service | 8003 | Django + Celery |
| LLM Service | 8004 | FastAPI + Ollama / OpenRouter |
| Notification Service | 8005 | Go |
| Kafka | 9092 / 29092 | Confluent |
| MinIO | 9000 / 9001 | Object storage |
| Redis | 6379 | Celery broker |
| Grafana / Loki / Promtail | 3001 / 3100 / 9080 | Observability |
| Postgres (per service) | 5432–5436 | — |

---

## Requirements

- [Docker](https://www.docker.com/) and Docker Compose (v2+)
- Git
- ~8 GB free RAM recommended
- Optional for local dev outside Docker: Node.js 18+, Python 3.11+, Go 1.21+

---

## Installation

```bash
git clone https://gitlab.com/samah37/revmine.git
cd revmine
```

Before starting, create the `.env` files described in the [Environment Setup](#environment-setup) section. They are gitignored and must be created locally.

Then start everything:

```bash
docker compose up --build
```

The frontend will be available at `http://localhost:5173`.

---

## Environment Setup

Each service that requires secrets ships with a `.env.example`. Copy it to `.env` in the same folder and fill in the values.

```bash
cp backend/api-gateway/.env.example            backend/api-gateway/.env
cp backend/services/configuration/.env.example backend/services/configuration/.env
cp backend/services/collection/.env.example    backend/services/collection/.env
cp backend/services/analyze/.env.example       backend/services/analyze/.env
# LLM service has no .env.example — create it manually (see below)
touch backend/services/llm/.env
```

Below is what each variable means and where to get it.

### 1. `backend/api-gateway/.env`

Central auth + routing service. Needs OAuth credentials for each provider users can sign in with.

```env
SECRET_KEY=<any long random string>
DEBUG=True
DATABASE_HOST=gateway-db
DATABASE_NAME=gateway_db
DATABASE_USER=postgres
DATABASE_PASSWORD=postgres
DATABASE_PORT=5432
ALLOWED_HOSTS=localhost,127.0.0.1
CORS_ALLOWED_ORIGINS=http://localhost:5173

CONFIGURATION_SERVICE_URL=http://configuration-service:8001/api/workspaces
LLM_SERVICE_URL=http://llm-service:8004
COLLECTION_SERVICE_URL=http://collection-service:8002/api/collections

# --- GitHub OAuth ---
GITHUB_CLIENT_ID=
GITHUB_CLIENT_SECRET=
GITHUB_REDIRECT_URI=http://localhost:5173/auth/github/callback

# --- GitLab OAuth ---
GITLAB_CLIENT_ID=
GITLAB_CLIENT_SECRET=
GITLAB_REDIRECT_URI=http://localhost:5173/auth/gitlab/callback

# --- Google OAuth ---
GOOGLE_CLIENT_ID=
GOOGLE_CLIENT_SECRET=
GOOGLE_REDIRECT_URI=http://localhost:5173/auth/google/callback

FRONTEND_URL=http://localhost:5173
```

**Where to get the OAuth credentials:**

- **GitHub** → https://github.com/settings/developers → *New OAuth App*
  - Homepage URL: `http://localhost:5173`
  - Authorization callback URL: `http://localhost:5173/auth/github/callback`
  - Copy the Client ID and generate a Client Secret.
- **GitLab** → https://gitlab.com/-/user_settings/applications → *Add new application*
  - Redirect URI: `http://localhost:5173/auth/gitlab/callback`
  - Scopes: `read_user`, `read_api`, `read_repository`, `api`.
- **Google** → https://console.cloud.google.com/apis/credentials → *Create Credentials → OAuth client ID* (Web application)
  - Authorized redirect URI: `http://localhost:5173/auth/google/callback`

`SECRET_KEY` can be any random string; generate one with:
```bash
python -c "import secrets; print(secrets.token_urlsafe(50))"
```

### 2. `backend/services/configuration/.env`

```env
SECRET_KEY=<any long random string>
DEBUG=True
DATABASE_NAME=configuration_db
DATABASE_USER=postgres
DATABASE_PASSWORD=postgres
DATABASE_HOST=configuration-db
DATABASE_PORT=5432
ALLOWED_HOSTS=localhost,127.0.0.1,configuration-service
CORS_ALLOWED_ORIGINS=http://localhost:5173
ENCRYPTION_KEY=<Fernet key>
```

`ENCRYPTION_KEY` is a Fernet key used to encrypt provider tokens. Generate one with:
```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

### 3. `backend/services/collection/.env`

This service also provides the credentials used to boot MinIO, so **both the MinIO container and the collection service read this file**. Keep the `MINIO_*` values consistent.

```env
SECRET_KEY=<any long random string>
DEBUG=True
DATABASE_HOST=collection-db
DATABASE_NAME=collection_db
DATABASE_USER=postgres
DATABASE_PASSWORD=postgres
DATABASE_PORT=5432
ALLOWED_HOSTS=localhost,127.0.0.1,collection-service
CORS_ALLOWED_ORIGINS=http://localhost:5173
ENCRYPTION_KEY=<same Fernet key as configuration service>
CONFIGURATION_SERVICE_URL=http://configuration-service:8001/api

# --- MinIO (object storage for collected artifacts) ---
MINIO_ROOT_USER=<pick a username>
MINIO_ROOT_PASSWORD=<pick a strong password, ≥8 chars>
MINIO_BUCKET_NAME=revmine-collections
MINIO_ENDPOINT=minio:9000
MINIO_ACCESS_KEY=<same as MINIO_ROOT_USER>
MINIO_SECRET_KEY=<same as MINIO_ROOT_PASSWORD>
MINIO_SECURE=False
```

After startup, the MinIO console is at http://localhost:9001 (login with the values above).

### 4. `backend/services/analyze/.env`

```env
SECRET_KEY=<any long random string>
DEBUG=True
DATABASE_HOST=analyze-db
DATABASE_NAME=analyze_db
DATABASE_USER=postgres
DATABASE_PASSWORD=postgres
DATABASE_PORT=5432
ALLOWED_HOSTS=localhost,127.0.0.1,analyze-service
CORS_ALLOWED_ORIGINS=http://localhost:5173
ENCRYPTION_KEY=<same Fernet key as configuration service>
```

### 5. `backend/services/llm/.env`

The LLM service can route to either a local Ollama model (default) or an OpenRouter-hosted model.

```env
OLLAMA_DEFAULT_MODEL=deepseek-r1
OLLAMA_HOST=http://ollama-service:11434/

# Optional — only needed if you want to use OpenRouter-hosted models
OPENROUTER_API_KEY=
OPENROUTER_SITE_URL=http://localhost/
```

**Where to get the keys:**

- **Ollama** — runs as a container (`ollama-service`), no key needed. Pull the model once the stack is up:
  ```bash
  docker exec -it ollama-service ollama pull deepseek-r1
  ```
- **OpenRouter** (optional) → https://openrouter.ai/keys → *Create Key*.

### 6. Notification service

The Go notification service reads its configuration from environment variables set directly in [docker-compose.yaml](docker-compose.yaml) — no `.env` needed.

---

## Usage

### Start the stack

```bash
docker compose up --build          # first run / after code changes
docker compose up                  # subsequent runs
docker compose up -d               # detached
docker compose logs -f <service>   # tail a single service
docker compose down                # stop
docker compose down -v             # stop and wipe volumes (DBs, MinIO, Ollama models)
```

### Access the services

- Frontend: http://localhost:5173
- API Gateway: http://localhost:8000/api
- MinIO Console: http://localhost:9001
- Grafana: http://localhost:3001 (admin / admin)

### Pull the LLM model (once)

After the first `docker compose up`:

```bash
docker exec -it ollama-service ollama pull deepseek-r1
```

### Frontend development (outside Docker)

```bash
cd frontend
npm install
npm run dev
```

### Running tests

```bash
# Frontend unit tests
cd frontend && npm test

# Frontend E2E (Cypress)
cd frontend && npm run cypress:open

# A Django service
cd backend/services/analyze && python manage.py test
```

---

## Troubleshooting

- **A service keeps restarting** — check `docker compose logs <service>`. Most often a missing or malformed `.env` variable.
- **`ENCRYPTION_KEY` errors** — the configuration, collection, and analyze services must share the same Fernet key.
- **OAuth redirect mismatch** — the `*_REDIRECT_URI` in the gateway `.env` must exactly match the one registered with the provider.
- **MinIO refuses to start** — `MINIO_ROOT_PASSWORD` must be at least 8 characters.
- **Port already in use** — adjust the host-side port in `docker-compose.yaml`.
