# Welcome to RevMine

**RevMine** is an open-source tool for *mining and analyzing modern code review data*. It connects to your Git hosting provider (GitHub or GitLab), collects merge/pull request activity, and surfaces process metrics — lead time, rework, review size, reviewer workload, and more — through an interactive dashboard with an LLM-assisted exploration interface.

In addition to its core code-review focus, RevMine now ships **light analytics for Kanban boards (GitHub Projects v2, GitLab Issue Boards) and CI/CD pipelines (GitHub Actions, GitLab CI)** — covering flow metrics (lead/cycle time, throughput, WIP, CFD) and pipeline reliability metrics (success rate, build duration, MTTR, deploy frequency, flaky jobs). These DevOps tracks are intentionally minimal in this release and will be deepened in upcoming versions.

RevMine is designed for researchers and practitioners who want reproducible, end-to-end code review analytics without stitching together ad-hoc scripts.

### Key features

- **Multi-provider collection** — pull review history from GitHub and GitLab via OAuth.
- **Process analytics** — lead time, rework size, review iteration counts, and distribution histograms with adaptive binning and time-based filters.
- **DevOps tracks (light, evolving)** — Kanban flow metrics and CI/CD pipeline metrics with async background collection, progress bar, and a metrics-CSV export. Slated for deeper coverage in future releases.
- **LLM-assisted insights** — ask natural-language questions over collected data (via local Ollama or OpenRouter-hosted models).
- **Microservice architecture** — each concern (collection, configuration, analysis, notification, LLM) runs as an independent service, orchestrated with Docker Compose.
- **Observability built in** — Grafana + Loki + Promtail for logs out of the box.

### Paper

If you use RevMine in your research, please cite our paper:

> *RevMine: A Tool for Mining and Analyzing Modern Code Review Data* — **[link to paper](#)** *(https://ieeexplore.ieee.org/abstract/document/11344241)*

```bibtex
@inproceedings{kansab2025revmine,
  title={RevMine: An LLM-assisted tool for code review mining and analysis across Git platforms},
  author={Kansab, Samah and Bordeleau, Francis and Tizghadam, Ali},
  booktitle={2025 IEEE International Conference on Collaborative Advances in Software and COmputiNg (CASCON)},
  pages={577--578},
  year={2025},
  organization={IEEE}
}
```

---

## Quick Start

The entire stack — frontend, backend microservices, databases, Kafka, MinIO, Redis, Ollama, and observability — runs through Docker Compose with a single command:

```bash
docker compose up --build -d
```

Once the containers are healthy, open the app at:

**http://localhost:5173/**

> ⚠️ **Before the first run**, you need to create the `.env` files for each backend service. They are gitignored and must be filled in locally with your own secrets (OAuth credentials, encryption keys, MinIO credentials, etc.). See **[docs/environment-setup.md](docs/environment-setup.md)** for the variables and where to obtain each value.

After the stack is up, pull the default LLM model (one-time):

```bash
docker exec -it ollama-service ollama pull deepseek-r1
```

To stop the stack:

```bash
docker compose down
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

Before starting, create the `.env` files described in **[docs/environment-setup.md](docs/environment-setup.md)**. They are gitignored and must be created locally.

Then start everything:

```bash
docker compose up --build
```

The frontend will be available at `http://localhost:5173`.

---

## Environment Setup

Each backend service reads its secrets from a local `.env` file that must be created before the first run. Step-by-step instructions — variables, how to generate keys, and where to obtain each OAuth credential — are split per service to keep things easy to scan:

- [Overview & shared keys](docs/environment-setup.md)
- [API Gateway (GitHub / GitLab / Google OAuth)](docs/env/api-gateway.md)
- [Configuration service](docs/env/configuration.md)
- [Collection service (includes MinIO)](docs/env/collection.md)
- [Analyze service](docs/env/analyze.md)
- [LLM service (Ollama / OpenRouter)](docs/env/llm.md)

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
