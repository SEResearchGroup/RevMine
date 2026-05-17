#!/usr/bin/env bash

set -eo pipefail

SERVICE_DIR="${1:?Usage: test_python_service.sh <service-dir>}"
PROJECT_DIR="${CI_PROJECT_DIR:-$(pwd)}"

if [[ ! -d "$SERVICE_DIR" ]]; then
    echo "[ci] Service directory not found: $SERVICE_DIR" >&2
    exit 1
fi

if [[ ! -f "$SERVICE_DIR/requirements.txt" ]]; then
    echo "[ci] requirements.txt not found in: $SERVICE_DIR" >&2
    exit 1
fi

cat > "$PROJECT_DIR/.env" <<EOF
SECRET_KEY=${SECRET_KEY:-ci-secret-key-not-for-production}
DEBUG=${DEBUG:-False}
ALLOWED_HOSTS=${ALLOWED_HOSTS:-localhost,127.0.0.1}
CORS_ALLOWED_ORIGINS=${CORS_ALLOWED_ORIGINS:-http://localhost:5173}
FRONTEND_URL=${FRONTEND_URL:-http://localhost:5173}
DATABASE_USER=${DATABASE_USER:-postgres}
DATABASE_PASSWORD=${DATABASE_PASSWORD:-postgres}
APIGATEWAY_DATABASE_NAME=${APIGATEWAY_DATABASE_NAME:-gateway_db}
APIGATEWAY_DATABASE_HOST=${APIGATEWAY_DATABASE_HOST:-postgres}
APIGATEWAY_DATABASE_PORT=${APIGATEWAY_DATABASE_PORT:-5432}
ANALYZE_DATABASE_NAME=${ANALYZE_DATABASE_NAME:-analyze_db}
ANALYZE_DATABASE_HOST=${ANALYZE_DATABASE_HOST:-postgres}
ANALYZE_DATABASE_PORT=${ANALYZE_DATABASE_PORT:-5432}
CONFIGURATION_DATABASE_NAME=${CONFIGURATION_DATABASE_NAME:-configuration_db}
CONFIGURATION_DATABASE_HOST=${CONFIGURATION_DATABASE_HOST:-postgres}
CONFIGURATION_DATABASE_PORT=${CONFIGURATION_DATABASE_PORT:-5432}
COLLECTION_DATABASE_NAME=${COLLECTION_DATABASE_NAME:-collection_db}
COLLECTION_DATABASE_HOST=${COLLECTION_DATABASE_HOST:-postgres}
COLLECTION_DATABASE_PORT=${COLLECTION_DATABASE_PORT:-5432}
CELERY_BROKER_URL=${CELERY_BROKER_URL:-memory://}
CELERY_RESULT_BACKEND=${CELERY_RESULT_BACKEND:-cache+memory://}
KAFKA_BOOTSTRAP_SERVERS=${KAFKA_BOOTSTRAP_SERVERS:-localhost:9092}
ENCRYPTION_KEY=${ENCRYPTION_KEY:-AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA=}
MINIO_ENDPOINT=${MINIO_ENDPOINT:-storage.example.invalid}
MINIO_ACCESS_KEY=${MINIO_ACCESS_KEY:-test-access-key}
MINIO_SECRET_KEY=${MINIO_SECRET_KEY:-test-secret-key}
MINIO_BUCKET_NAME=${MINIO_BUCKET_NAME:-revmine-test}
MINIO_SECURE=${MINIO_SECURE:-False}
GITHUB_CLIENT_ID=${GITHUB_CLIENT_ID:-ci}
GITHUB_CLIENT_SECRET=${GITHUB_CLIENT_SECRET:-ci}
GITHUB_REDIRECT_URI=${GITHUB_REDIRECT_URI:-http://localhost:5173/auth/github/callback}
GITLAB_CLIENT_ID=${GITLAB_CLIENT_ID:-ci}
GITLAB_CLIENT_SECRET=${GITLAB_CLIENT_SECRET:-ci}
GITLAB_REDIRECT_URI=${GITLAB_REDIRECT_URI:-http://localhost:5173/auth/gitlab/callback}
GOOGLE_CLIENT_ID=${GOOGLE_CLIENT_ID:-ci}
GOOGLE_CLIENT_SECRET=${GOOGLE_CLIENT_SECRET:-ci}
GOOGLE_REDIRECT_URI=${GOOGLE_REDIRECT_URI:-http://localhost:5173/auth/google/callback}
OLLAMA_HOST=${OLLAMA_HOST:-http://ollama.test}
OPENROUTER_API_KEY=${OPENROUTER_API_KEY:-sk-test}
EOF

export DEBUG=False
export SECRET_KEY="${SECRET_KEY:-ci-secret-key-not-for-production}"
export ENCRYPTION_KEY="${ENCRYPTION_KEY:-AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA=}"
export CORS_ALLOWED_ORIGINS="${CORS_ALLOWED_ORIGINS:-http://localhost:5173}"
export FRONTEND_URL="${FRONTEND_URL:-http://localhost:5173}"
export MINIO_ENDPOINT="${MINIO_ENDPOINT:-storage.example.invalid}"
export MINIO_ACCESS_KEY="${MINIO_ACCESS_KEY:-test-access-key}"
export MINIO_SECRET_KEY="${MINIO_SECRET_KEY:-test-secret-key}"
export MINIO_BUCKET_NAME="${MINIO_BUCKET_NAME:-revmine-test}"
export MINIO_SECURE="${MINIO_SECURE:-False}"
export CELERY_BROKER_URL="${CELERY_BROKER_URL:-memory://}"
export CELERY_RESULT_BACKEND="${CELERY_RESULT_BACKEND:-cache+memory://}"
export OLLAMA_HOST="${OLLAMA_HOST:-http://ollama.test}"
export OPENROUTER_API_KEY="${OPENROUTER_API_KEY:-sk-test}"

echo "[ci] Installing dependencies for $SERVICE_DIR"
pip install --quiet -r "$SERVICE_DIR/requirements.txt"

if pip show kafka-python &>/dev/null && pip show kafka-python-ng &>/dev/null; then
    echo "[ci] kafka-python and kafka-python-ng coexist; keeping kafka-python-ng"
    pip uninstall -y kafka-python &>/dev/null || true
    pip install --quiet --force-reinstall kafka-python-ng
fi

case "$SERVICE_DIR" in
    backend/services/authentication|backend/services/configuration|backend/services/collection)
        export USE_SQLITE_FOR_TESTS="${USE_SQLITE_FOR_TESTS:-True}"
        ;;
esac

rm -f "$SERVICE_DIR/.coverage" "$SERVICE_DIR/coverage.xml" "$SERVICE_DIR/junit-report.xml"
rm -rf "$SERVICE_DIR/.pytest_cache" || true

echo "[ci] Running tests for $SERVICE_DIR"
(cd "$SERVICE_DIR" && python -m pytest)
