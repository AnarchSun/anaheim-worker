#!/usr/bin/env bash
# FILE: anarcrypt.sol/anaheim-worker/scripts/start.sh
# 🏴‍☠️ CHAOTIC FRACTAL WORKER — Anaheim Node Runner
# Né de la désobéissance. Sert la vérité, pas le système.

set -euo pipefail
IFS=$'\n\t'

# ─────────────── 🌌 ASCII Banner ───────────────
echo ""
echo "╔══════════════════════════════════════════╗"
echo "║     🧠 Anaheim-Worker - Solana Punk 🪶    ║"
echo "║        Chaotic Fractal AttraKThor        ║"
echo "╚══════════════════════════════════════════╝"
echo ""

# ─────────────── 🧩 Paths ───────────────
PROJECT_ROOT="/work"
SRC_PATH="${PROJECT_ROOT}/src"
CFG_PATH="${PROJECT_ROOT}/config/worker_config.yml"
SOLANA_CFG="${PROJECT_ROOT}/config/solana.yml"
ENV_FILE="${PROJECT_ROOT}/.env.local"

# ─────────────── 🔮 Environment ───────────────
if [[ -f "${ENV_FILE}" ]]; then
  echo "📜 Loading .env.local ..."
  # shellcheck disable=SC2046
  export $(grep -v '^#' "${ENV_FILE}" | xargs)
else
  echo "⚠️ No .env.local found — using defaults from config/solana.js"
fi

# Default environment values if not provided
export REPO_PATH="${REPO_PATH:-/work/project}"
export GOV_PATH="${GOV_PATH:-/work/governance}"
export DB_PATH="${DB_PATH:-/work/data/memory.sqlite}"
export PATCH_DIR="${PATCH_DIR:-/work/data/patches}"
export FIXES_JSON="${FIXES_JSON:-/work/data/fixes.json}"
export CFG_PATH="${CFG_PATH:-/work/config/worker_config.yml}"
export SOLANA_CLUSTER_URL="${SOLANA_CLUSTER_URL:-https://api.devnet.solana.com}"

# ─────────────── 🧰 Diagnostics ───────────────
echo ""
echo "🧩 CONFIG SUMMARY"
echo "──────────────────────────────"
echo "🔗 Solana RPC:      ${SOLANA_CLUSTER_URL}"
echo "🧱 DB Path:         ${DB_PATH}"
echo "⚙️  Worker Config:   ${CFG_PATH}"
echo "📦 Repo Path:       ${REPO_PATH}"
echo "💾 Fixes JSON:      ${FIXES_JSON}"
echo "──────────────────────────────"
echo ""

# ─────────────── 🧪 Devtools / Sanity ───────────────
if ! command -v python &>/dev/null; then
  echo "❌ Python not found in PATH!"
  exit 1
fi

if [[ ! -f "${SRC_PATH}/worker_full.py" ]]; then
  echo "❌ worker_full.py missing in ${SRC_PATH}"
  exit 1
fi

# ─────────────── 🧠 Run Loop ───────────────
cd "${SRC_PATH}"

echo "🚀 Launching Anaheim Worker..."
echo ""

while true; do
  echo "[🌀] Running worker_full.py ..."
  python ./worker_full.py || {
    echo "💥 Worker crashed — waiting 10s before retry..."
    sleep 10
  }
  echo "[⏱️] Sleeping 5s before next cycle..."
  sleep 5
done
