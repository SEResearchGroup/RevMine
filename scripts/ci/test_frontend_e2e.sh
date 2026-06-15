#!/usr/bin/env bash

set -eo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"
FRONTEND_DIR="$PROJECT_DIR/frontend"
NODE_VERSION="${NODE_VERSION:-20.19.0}"
NODE_CACHE_DIR="${NODE_CACHE_DIR:-$PROJECT_DIR/.cache/tools}"

ensure_node() {
    if command -v npm >/dev/null 2>&1; then
        return
    fi

    local os arch archive install_dir url
    os="$(uname -s | tr '[:upper:]' '[:lower:]')"
    arch="$(uname -m)"

    case "$arch" in
        x86_64|amd64) arch="x64" ;;
        aarch64|arm64) arch="arm64" ;;
        *) echo "[frontend-e2e] Unsupported architecture: $arch" >&2; exit 1 ;;
    esac

    archive="node-v${NODE_VERSION}-${os}-${arch}.tar.xz"
    install_dir="$NODE_CACHE_DIR/node-v${NODE_VERSION}-${os}-${arch}"
    url="https://nodejs.org/dist/v${NODE_VERSION}/$archive"

    if [[ ! -x "$install_dir/bin/npm" ]]; then
        mkdir -p "$NODE_CACHE_DIR"
        echo "[frontend-e2e] Downloading Node.js $NODE_VERSION locally..."
        curl -fsSL "$url" -o "$NODE_CACHE_DIR/$archive"
        rm -rf "$install_dir"
        tar -C "$NODE_CACHE_DIR" -xJf "$NODE_CACHE_DIR/$archive"
    fi

    export PATH="$install_dir/bin:$PATH"
}

run_cypress() {
    (
        cd "$FRONTEND_DIR"
        unset ELECTRON_RUN_AS_NODE
        unset ELECTRON_NO_ATTACH_CONSOLE

        npm ci
        npx cypress verify

        if [[ "${CYPRESS_VERIFY_ONLY:-0}" == "1" ]]; then
            echo "[frontend-e2e] Cypress binary verified"
            exit 0
        fi

        if command -v xvfb-run >/dev/null 2>&1; then
            xvfb-run -a npx cypress run "$@"
        else
            npx cypress run "$@"
        fi
    )
}

ensure_node
run_cypress "$@"
