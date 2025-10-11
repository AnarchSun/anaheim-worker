# src/workers/modules/anaheim_worker_safe.py
import os
import queue
import threading
import time
from pathlib import Path
from typing import Optional, Union

from workers.utils.apply_ts_actions import apply_ts_actions


# -----------------------
# Globals
# -----------------------
PROJECT_PATH = Path(os.getenv("REPO_PATH", "/home/anarchsun/RustroverProjects/anarcrypt.sol/anaheim-worker")).resolve()
DIAGNOSTICS_DIR = PROJECT_PATH / "diagnostics"
DIAGNOSTICS_DIR.mkdir(exist_ok=True)
COPILOT_DELEGATIONS_LOG = DIAGNOSTICS_DIR / "copilot_delegations.log"
FLOOD_BRANCH = "<flood>"

llm_queue: queue.Queue[Union[str, dict]] = queue.Queue()
shutdown_event = threading.Event()
DRY_RUN = os.getenv("WORKER_DRY_RUN", "true").lower() == "true"

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
# Real worker functions
# -----------------------
def delegate_to_copilot(task: dict, queue_ref: Optional[queue.Queue] = None):
    """Pousse une tâche dans la queue LLM pour traitement par Copilot"""
    if queue_ref is None:
        queue_ref = llm_queue
    log(f"🤖 Delegating task to Copilot: {task.get('type', 'unknown')}")
    queue_ref.put(task)

def generate_copilot_fail_report(failures: list, report_path: Optional[Path] = None):
    """Génère un rapport simple des échecs Copilot"""
    if report_path is None:
        report_path = Path("/tmp/copilot_fail_report.txt")
    log(f"📝 Generating Copilot fail report: {len(failures)} entries")
    with report_path.open("w", encoding="utf-8") as f:
        for entry in failures:
            f.write(f"{entry}\n")
    return report_path

def handle_shutdown():
    """Active le signal d'arrêt pour tous les threads du worker"""
    log("⚡ Shutdown initiated")
    shutdown_event.set()

def init_db(db_path: Optional[Path] = None):
    """Stub simple pour l'initialisation de la DB"""
    if db_path is None:
        db_path = Path("/tmp/anarcrypt_worker.db")
    log(f"💾 Initializing database at {db_path}")
    db_path.touch(exist_ok=True)
    return db_path

def ask_llm(prompt: str) -> str:
    log(f"🤖 ask_llm called with prompt: {prompt[:100]}...")
    return "[]"

def handle_ts_error(ts_error: dict):
    """Transforme et applique un TS error via apply_ts_actions"""
    apply_ts_actions([ts_error])
    log(f"🛠 TS error handled: {ts_error.get('message', ts_error)}")

def auto_ts_fix_cycle_safe(last_commit_time: float):
    """Version safe du cycle auto TS fix"""
    # placeholder simple
    log("💡 auto_ts_fix_cycle_safe called")
    return [], last_commit_time

def main_worker_safe_hyper(num_threads: int = 4):
    """Main worker safe hyper"""
    log(f"💡 main_worker_safe_hyper starting with {num_threads} threads")

# -----------------------
# Repo helpers, TS patching, worker threads, hot reload
# -----------------------
# ... ici tu conserves tout le reste de anaheim_worker_safe.py
# y compris apply_patch, apply_ts_actions, auto_ts_fix_cycle_safe, worker_thread_cycle, etc.
