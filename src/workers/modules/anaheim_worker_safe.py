# src/workers/modules/anaheim_worker_safe.py
import os
import queue
import threading
import time
import pickle
from pathlib import Path
from typing import Optional, Union

from workers.utils.apply_ts_actions import apply_ts_actions

# -----------------------
# Globals
# -----------------------
PROJECT_PATH = Path(os.getenv(
    "REPO_PATH",
    "/home/anarchsun/RustroverProjects/anarcrypt.sol/anaheim-worker"
)).resolve()

DIAGNOSTICS_DIR = PROJECT_PATH / "diagnostics"
DIAGNOSTICS_DIR.mkdir(exist_ok=True)

COPILOT_DELEGATIONS_LOG = DIAGNOSTICS_DIR / "copilot_delegations.log"
FLOOD_BRANCH = "<flood>"

llm_queue: queue.Queue[Union[str, dict]] = queue.Queue()
shutdown_event = threading.Event()
DRY_RUN = os.getenv("WORKER_DRY_RUN", "true").lower() == "true"

LLM_QUEUE_PATH = PROJECT_PATH / "llm_queue.pkl"

# -----------------------
# Logging
# -----------------------
def log(msg: str):
    ts = time.strftime("%Y-%m-%d %H:%M:%S")
    line = f"[worker-safe][{ts}] {msg}"
    print(line)
    try:
        with open(PROJECT_PATH / "worker_safe.log", "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except OSError:
        pass

# -----------------------
# Worker Functions
# -----------------------
def delegate_to_copilot(task: dict, queue_ref: Optional[queue.Queue] = None):
    if queue_ref is None:
        queue_ref = llm_queue
    log(f"🤖 Delegating task to Copilot: {task.get('type', 'unknown')}")
    queue_ref.put(task)

def generate_copilot_fail_report(failures: list, report_path: Optional[Path] = None):
    if report_path is None:
        report_path = Path("/tmp/copilot_fail_report.txt")
    log(f"📝 Generating Copilot fail report: {len(failures)} entries")
    with report_path.open("w", encoding="utf-8") as f:
        for entry in failures:
            f.write(f"{entry}\n")
    return report_path

def handle_shutdown():
    log("⚡ Shutdown initiated")
    shutdown_event.set()

def init_db(db_path: Optional[Path] = None):
    if db_path is None:
        db_path = Path("/tmp/anarcrypt_worker.db")
    log(f"💾 Initializing database at {db_path}")
    db_path.touch(exist_ok=True)
    return db_path

def ask_llm(prompt: str) -> str:
    log(f"🤖 ask_llm called with prompt: {prompt[:100]}...")
    return "[]"

def handle_ts_error(ts_error: dict):
    apply_ts_actions([ts_error])
    log(f"🛠 TS error handled: {ts_error.get('message', ts_error)}")

def auto_ts_fix_cycle_safe(last_commit_time: float):
    log("💡 auto_ts_fix_cycle_safe called")
    return [], last_commit_time

def main_worker_safe_hyper(num_threads: int = 4):
    log(f"💡 main_worker_safe_hyper starting with {num_threads} threads")

# -----------------------
# Repo Helpers, Hot Reload, Queue Persistence
# -----------------------
def start_hot_reload():
    """Démarre un watcher basique simulant le rechargement à chaud."""
    log("♻️ Hot Reload System initialized (background watcher thread active).")

    def watcher():
        while not shutdown_event.is_set():
            time.sleep(5)
            log("🔁 [hot-reload] Heartbeat pulse…")

    t = threading.Thread(target=watcher, daemon=True)
    t.start()
    return t

def save_queue_state():
    with LLM_QUEUE_PATH.open("wb") as f:
        pickle.dump(list(llm_queue.queue), f)

def load_queue_state():
    if LLM_QUEUE_PATH.exists():
        tasks = pickle.load(LLM_QUEUE_PATH.open("rb"))
        for t in tasks:
            llm_queue.put(t)

def worker_thread_cycle(thread_id: int, task_queue: queue.Queue):
    log(f"🧵 Worker thread #{thread_id} started.")
    while not shutdown_event.is_set():
        try:
            task = task_queue.get(timeout=2)
        except queue.Empty:
            continue

        log(f"⚙️ Worker #{thread_id} processing task: {task}")
        try:
            result = ask_llm(str(task))
            log(f"✅ Worker #{thread_id} task complete -> {result}")
        except Exception as e:
            handle_ts_error({"message": str(e), "task": task})
        finally:
            task_queue.task_done()
    log(f"🛑 Worker thread #{thread_id} exiting.")

def repo_open(repo_path: Optional[Path] = None):
    if repo_path is None:
        repo_path = PROJECT_PATH
    log(f"📂 Repo opened at {repo_path}")
    return {"path": repo_path, "status": "ok"}

def copilot_retrier(task: dict, retries: int = 3, delay: int = 2):
    for attempt in range(1, retries + 1):
        try:
            log(f"🌀 Copilot retrier attempt {attempt}/{retries}")
            ask_llm(str(task))
            log(f"✅ Copilot retrier succeeded on attempt {attempt}")
            return True
        except Exception as e:
            log(f"⚠️ Attempt {attempt} failed: {e}")
            time.sleep(delay)
    log("❌ Copilot retrier exhausted all retries.")
    return False

def hyper_worker_main(num_threads: int = 4, dry_run: bool = True):
    log(f"🚀 Hyper Safe Worker started | threads={num_threads} | dry_run={dry_run}")
    start_hot_reload()
    init_db()

    task_queue = queue.Queue()
    threads = []
    for i in range(num_threads):
        t = threading.Thread(target=worker_thread_cycle, args=(i + 1, task_queue), daemon=True)
        threads.append(t)
        t.start()

    for n in range(5):
        task_queue.put({"type": "init", "payload": f"task_{n}"})

    try:
        while not shutdown_event.is_set():
            time.sleep(2)
            log("💤 Main hyper worker heartbeat…")
    except KeyboardInterrupt:
        handle_shutdown()

    for t in threads:
        t.join(timeout=2)

    log("✅ Hyper Safe Worker terminated cleanly.")
