# Environment Setup

RevMine reads its configuration from a **single `.env` file at the repository root**. It is gitignored — copy `.env.example` once and fill in your values.

```bash
cp .env.example .env
$EDITOR .env
```

The defaults boot a working dev stack out of the box. The only values you must change before first run:

| Variable | Why | How |
|---|---|---|
| `SECRET_KEY` | Django secret used by every service | `python -c "import secrets; print(secrets.token_urlsafe(50))"` |
| `ENCRYPTION_KEY` | Fernet key shared by configuration / collection / analyze for token encryption | `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"` |
| `GITHUB_*` / `GITLAB_*` / `GOOGLE_*` | OAuth client IDs (only the providers you want to enable) | See [provider setup](#oauth-provider-setup) below |

Everything else (Postgres, MinIO, Ollama, OpenRouter site URL) ships with sane defaults that just work for local dev.

## OAuth provider setup

### GitHub

1. https://github.com/settings/developers → **New OAuth App**
2. Set:
   - Homepage URL: `http://localhost:5173`
   - Authorization callback URL: `http://localhost:5173/auth/github/callback`
3. Copy the **Client ID** and generate a **Client Secret** → paste into `GITHUB_CLIENT_ID` / `GITHUB_CLIENT_SECRET`.

### GitLab

1. https://gitlab.com/-/user_settings/applications → **Add new application**
2. Set:
   - Redirect URI: `http://localhost:5173/auth/gitlab/callback`
   - Scopes: `read_user`, `read_api`, `read_repository`, `api`
3. Copy the Application ID / Secret → paste into `GITLAB_CLIENT_ID` / `GITLAB_CLIENT_SECRET`.

### Google

1. https://console.cloud.google.com/apis/credentials → **Create Credentials → OAuth client ID** (Web application)
2. Authorized redirect URI: `http://localhost:5173/auth/google/callback`
3. Copy the Client ID / Secret → paste into `GOOGLE_CLIENT_ID` / `GOOGLE_CLIENT_SECRET`.

## Optional: OpenRouter (LLM)

Default LLM routing uses the local Ollama container — no key required.

To use OpenRouter-hosted models instead, get a key at https://openrouter.ai/keys and set `OPENROUTER_API_KEY`.

After the stack is up, pull the default Ollama model (one-time):

```bash
docker exec -it ollama-service ollama pull deepseek-r1
```

## Common pitfalls

- **`ENCRYPTION_KEY` mismatch** across services will cause token decryption to fail. The single root `.env` setup avoids this — every service reads the same value.
- **OAuth redirect URI** must match the URI registered with the provider exactly (scheme, host, port, path).
- **`MINIO_ROOT_PASSWORD`** must be at least 8 characters or MinIO refuses to start.
- **Changing `POSTGRES_PASSWORD` after the first boot** won't update existing Postgres volumes — either start with the password you want, or `docker compose down -v` to reset (deletes data).
