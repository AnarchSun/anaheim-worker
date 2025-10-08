#!/usr/bin/env bash
# ==========================================================
# Anaheim Worker — Auto-start script
# PATH: scripts/start_worker.sh
# ==========================================================

set -e

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

VENV="$PROJECT_ROOT/.venv"
LOG_DIR="$PROJECT_ROOT/logs"
LOG_FILE="$LOG_DIR/worker.log"

# ==========================================================
# 1️⃣ Ensure venv exists
# ==========================================================
if [ ! -d "$VENV" ]; then
  echo "🧪 Creating virtual environment..."
  python3 -m venv "$VENV"
fi

# ==========================================================
# 2️⃣ Activate environment
# ==========================================================
source "$VENV/bin/activate"

# ==========================================================
# 3️⃣ Ensure logs folder
# ==========================================================
mkdir -p "$LOG_DIR"

# ==========================================================
# 4️⃣ Start the worker
# ==========================================================
echo "🚀 Starting Anaheim Worker..."
nohup python src/worker_full.py > "$LOG_FILE" 2>&1 &

# ==========================================================
# 5️⃣ Confirm process and tail log
# ==========================================================
sleep 2
PID=$(pgrep -f "worker_full.py" | head -n 1)
if [ -n "$PID" ]; then
  echo "✅ Worker started (PID: $PID)"
  echo "📜 Log: $LOG_FILE"
  echo "🧠 Tail logs with: tail -f $LOG_FILE"
else
  echo "❌ Failed to start worker"
  exit 1
fi
