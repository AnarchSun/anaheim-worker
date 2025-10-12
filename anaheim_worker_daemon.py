#!/bin/bash
# ~/bin/anarcrypt-worker-daemon
# Anarcrypt Hyper Worker Daemon PRO with Auto-Update Watchdog

export PYTHONPATH="$HOME/RustroverProjects/anarcrypt.sol/anaheim-worker/src"

WORKER_MODULE="workers.modules.anarcrypt_worker_hyper"
LOG_DIR="$HOME/RustroverProjects/anarcrypt.sol/anaheim-worker/worker_logs"
PID_DIR="$HOME/RustroverProjects/anarcrypt.sol/anaheim-worker/worker_pids"
SRC_DIR="$HOME/RustroverProjects/anarcrypt.sol/anaheim-worker/src"
mkdir -p "$LOG_DIR" "$PID_DIR"

NUM_THREADS=4
NUM_WORKERS=1
WORKER_OPTS=()
WATCH_INTERVAL=2

# -----------------------
# Parse CLI options
# -----------------------
while [[ $# -gt 0 ]]; do
case "$1" in
--threads)
NUM_THREADS="$2"
shift 2
;;
--workers)
NUM_WORKERS="$2"
shift 2
;;
--no-dry-run)
WORKER_OPTS+=("--run")  # translates to Python argument
shift \
;;
*)
break
;;
esac
done

# -----------------------
# Worker functions
# -----------------------
start_worker() {
    local idx="$1"
local pid_file="$PID_DIR/worker_${idx}.pid"
local log_file="$LOG_DIR/worker_${idx}.log"

if [ -f "$pid_file" ] && kill -0 $(cat "$pid_file") 2>/dev/null; then
echo "⚠️ Worker #$idx already running (PID $(cat "$pid_file"))"
return
fi

echo "🚀 Starting Worker #$idx..."
nohup bash -c "
while true; do
python3 -u -m $WORKER_MODULE --threads $NUM_THREADS ${WORKER_OPTS[@]} >> '$log_file' 2>&1
echo '⚠️ Worker #$idx crashed at \$(date), restarting...' >> '$log_file'
sleep 2
done
" &
echo $! > "$pid_file"
echo "✅ Worker #$idx watchdog started with PID $(cat "$pid_file")"
}

stop_worker() {
local idx
for idx in $(seq 1 $NUM_WORKERS); do
local pid_file="$PID_DIR/worker_${idx}.pid"
if [ -f "$pid_file" ] && kill -0 $(cat "$pid_file") 2>/dev/null; then
echo "🛑 Stopping Worker #$idx (watchdog PID $(cat "$pid_file"))..."
kill $(cat "$pid_file")
rm -f "$pid_file"
echo "✅ Worker #$idx stopped."
else
echo "⚠️ Worker #$idx not running"
fi
done
}

status_worker() {
local idx
for idx in $(seq 1 $NUM_WORKERS); do
local pid_file="$PID_DIR/worker_${idx}.pid"
if [ -f "$pid_file" ] && kill -0 $(cat "$pid_file") 2>/dev/null; then
echo "✅ Worker #$idx running (watchdog PID $(cat "$pid_file"))"
else
echo "❌ Worker #$idx not running"
fi
done
}

update_workers() {
echo "♻️ Updating all workers..."
stop_worker
sleep 1
for i in $(seq 1 $NUM_WORKERS); do
start_worker "$i"
done
echo "✅ Update complete, workers restarted."
}

# -----------------------
# Auto-update via file watcher
# -----------------------
watch_src_and_update() {
echo "👁 Watching $SRC_DIR for changes…"
local last_hash
last_hash=$(find "$SRC_DIR" -type f -name '*.py' -exec md5sum {} \; | md5sum | awk '{print $1}')

while true; do
sleep "$WATCH_INTERVAL"
local current_hash
current_hash=$(find "$SRC_DIR" -type f -name '*.py' -exec md5sum {} \; | md5sum | awk '{print $1}')
if [ "$current_hash" != "$last_hash" ]; then
echo "♻️ Detected Python source change, updating workers..."
update_workers
last_hash="$current_hash"
fi
done
}

# -----------------------
# CLI
# -----------------------
case "$1" in
     start)
shift
for i in $(seq 1 $NUM_WORKERS); do
start_worker "$i"
done
echo "💡 Starting auto-update watcher..."
watch_src_and_update &
;;
stop)
stop_worker
;;
restart)
stop_worker
sleep 1
shift
for i in $(seq 1 $NUM_WORKERS); do
start_worker "$i"
done
echo "💡 Restarted auto-update watcher..."
watch_src_and_update &
;;
status)
status_worker
;;
update)
update_workers
;;
*)
echo "Usage: $0 {start|stop|restart|status|update} [--threads N] [--workers M] [--no-dry-run]"
exit 1
;;
esac
