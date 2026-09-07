#!/usr/bin/env bash
# Install Ollama and start the server.
#
# The upstream instruction is `curl -fsSL https://ollama.com/install.sh | sh`.
# This downloads the script first so it can be inspected, and offers a
# --no-systemd path for containers where the service install does not apply.
set -euo pipefail

NO_SYSTEMD=0
SHOW=0
INSTALL_DIR="/usr/local"
for arg in "$@"; do
    case "$arg" in
        --no-systemd) NO_SYSTEMD=1 ;;
        --show) SHOW=1 ;;
        --install-dir=*) INSTALL_DIR="${arg#*=}" ;;
        -h|--help)
            echo "usage: setup_ollama.sh [--no-systemd] [--show] [--install-dir=PATH]"
            echo "  --no-systemd   install the binary and run 'ollama serve' directly"
            echo "  --show         print the official installer and exit without running it"
            exit 0 ;;
        *) echo "unknown option: $arg" >&2; exit 2 ;;
    esac
done

case "$(uname -s)" in
    Linux) ;;
    Darwin) echo "On macOS install the app from https://ollama.com/download — it ships the"
            echo "server and CLI together. This script covers Linux."; exit 1 ;;
    *) echo "Unsupported platform $(uname -s). See https://ollama.com/download"; exit 1 ;;
esac

if command -v ollama >/dev/null 2>&1; then
    echo "ollama already installed: $(ollama --version 2>&1 | head -1)"
else
    TMP="$(mktemp -d)"
    trap 'rm -rf "$TMP"' EXIT
    echo "Fetching https://ollama.com/install.sh ..."
    curl -fsSL -o "$TMP/install.sh" https://ollama.com/install.sh

    if [ "$SHOW" = "1" ]; then
        cat "$TMP/install.sh"; exit 0
    fi

    if [ "$NO_SYSTEMD" = "1" ]; then
        # The official script installs a systemd unit and a dedicated user, neither
        # of which applies in a container. Fetch the release archive directly.
        ARCH="$(uname -m)"
        case "$ARCH" in
            x86_64) ARCH=amd64 ;;
            aarch64|arm64) ARCH=arm64 ;;
            *) echo "unsupported arch $ARCH" >&2; exit 1 ;;
        esac
        BASE="https://ollama.com/download/ollama-linux-${ARCH}"
        echo "Downloading ${BASE} (~1.4GB) ..."
        # Releases are published as .tar.zst; .tgz is not always present.
        if curl -fsSL --head "${BASE}.tar.zst" >/dev/null 2>&1; then
            command -v zstd >/dev/null 2>&1 || {
                echo "zstd is required to extract this release. Install it (apt install zstd)." >&2
                exit 1; }
            curl -fL --progress-bar "${BASE}.tar.zst" | zstd -d -c | tar -x -C "$INSTALL_DIR"
        else
            curl -fL --progress-bar "${BASE}.tgz" | tar -xz -C "$INSTALL_DIR"
        fi
        export PATH="$INSTALL_DIR/bin:$PATH"
    else
        echo "Running the official installer (installs a systemd service; needs root)..."
        sh "$TMP/install.sh"
    fi
fi

OLLAMA_BIN="$(command -v ollama || echo "$INSTALL_DIR/bin/ollama")"
HOST="${OLLAMA_HOST:-127.0.0.1:11434}"

if curl -fsS "http://${HOST}/api/version" >/dev/null 2>&1; then
    echo "Server already running at ${HOST}."
else
    echo "Starting 'ollama serve' in the background (log: /tmp/ollama-serve.log)..."
    OLLAMA_HOST="$HOST" nohup "$OLLAMA_BIN" serve >/tmp/ollama-serve.log 2>&1 &
    for _ in $(seq 1 30); do
        curl -fsS "http://${HOST}/api/version" >/dev/null 2>&1 && break
        sleep 1
    done
fi

if curl -fsS "http://${HOST}/api/version" >/dev/null 2>&1; then
    echo "Ollama is up: $(curl -fsS "http://${HOST}/api/version")"
    echo
    echo "Next:"
    echo "  ollama pull qwen3:0.6b            # small, quick smoke test"
    echo "  python .claude/skills/ollama/scripts/ollama_doctor.py --model qwen3:0.6b"
else
    echo "Server did not come up. Check /tmp/ollama-serve.log." >&2
    exit 1
fi
