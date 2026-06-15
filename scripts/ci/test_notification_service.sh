#!/usr/bin/env bash

set -eo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"
SERVICE_DIR="$PROJECT_DIR/backend/services/notification"
GO_VERSION="${GO_VERSION:-1.22.12}"
GO_CACHE_DIR="${GO_CACHE_DIR:-$PROJECT_DIR/.cache/tools}"

run_go_tests() {
    (
        cd "$SERVICE_DIR"
        go test -coverprofile=coverage.out ./...
    )
}

docker_is_available() {
    command -v docker >/dev/null 2>&1 && docker info >/dev/null 2>&1
}

run_go_tests_in_docker() {
    docker run --rm \
        -v "$SERVICE_DIR:/app" \
        -w /app \
        -e GOCACHE=/tmp/go-cache \
        -e GOPATH=/tmp/go \
        "golang:${GO_VERSION%.*}-alpine" \
        sh -c "go test -coverprofile=coverage.out ./..."
}

install_local_go() {
    local os arch archive install_dir url
    os="$(uname -s | tr '[:upper:]' '[:lower:]')"
    arch="$(uname -m)"

    case "$arch" in
        x86_64|amd64) arch="amd64" ;;
        aarch64|arm64) arch="arm64" ;;
        *) echo "[notification-test] Unsupported architecture: $arch" >&2; exit 1 ;;
    esac

    archive="go${GO_VERSION}.${os}-${arch}.tar.gz"
    install_dir="$GO_CACHE_DIR/go${GO_VERSION}.${os}-${arch}"
    url="https://go.dev/dl/$archive"

    if [[ ! -x "$install_dir/go/bin/go" ]]; then
        mkdir -p "$GO_CACHE_DIR" "$install_dir"
        echo "[notification-test] Downloading Go $GO_VERSION locally..."
        curl -fsSL "$url" -o "$GO_CACHE_DIR/$archive"
        rm -rf "$install_dir/go"
        tar -C "$install_dir" -xzf "$GO_CACHE_DIR/$archive"
    fi

    export PATH="$install_dir/go/bin:$PATH"
}

if command -v go >/dev/null 2>&1; then
    echo "[notification-test] Using host Go: $(go version)"
    run_go_tests
elif docker_is_available; then
    echo "[notification-test] Host Go not found; using golang Docker image"
    run_go_tests_in_docker
else
    echo "[notification-test] Host Go and usable Docker are unavailable; using local Go toolchain"
    install_local_go
    run_go_tests
fi
