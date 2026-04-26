# Environment Setup

RevMine's backend services read their secrets from per-service `.env` files. These files are gitignored — you must create them locally before starting the stack for the first time.

Each service that requires secrets ships with a `.env.example` next to its code. The recommended flow is to copy each example to `.env` in the same folder, then fill in the values.

```bash
cp backend/api-gateway/.env.example            backend/api-gateway/.env
cp backend/services/configuration/.env.example backend/services/configuration/.env
cp backend/services/collection/.env.example    backend/services/collection/.env
cp backend/services/analyze/.env.example       backend/services/analyze/.env
# LLM service has no .env.example — create it manually
touch backend/services/llm/.env
```

## Per-service guides

Follow each guide below to fill in the required values and learn where to obtain each secret:

| Service | File | Guide |
|---|---|---|
| API Gateway | `backend/api-gateway/.env` | [env/api-gateway.md](env/api-gateway.md) |
| Configuration | `backend/services/configuration/.env` | [env/configuration.md](env/configuration.md) |
| Collection | `backend/services/collection/.env` | [env/collection.md](env/collection.md) |
| Analyze | `backend/services/analyze/.env` | [env/analyze.md](env/analyze.md) |
| LLM | `backend/services/llm/.env` | [env/llm.md](env/llm.md) |
| Notification | — | No `.env` needed; configured directly in [docker-compose.yaml](../docker-compose.yaml) |

## Shared secrets you will generate once

Some values are reused across several services. Generate them once and paste them in everywhere they're referenced.

### Django `SECRET_KEY`

Any long random string. Each service can use its own, but it must be set.

```bash
python -c "import secrets; print(secrets.token_urlsafe(50))"
```

### `ENCRYPTION_KEY` (Fernet key)

Used to encrypt provider tokens. The **configuration**, **collection**, and **analyze** services must all share the *same* key.

```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

## Common pitfalls

- **`ENCRYPTION_KEY` mismatch** across configuration / collection / analyze will cause token decryption to fail.
- **OAuth redirect URI** must match the URI registered with the provider exactly (scheme, host, port, path).
- **`MINIO_ROOT_PASSWORD`** must be at least 8 characters or MinIO refuses to start.
