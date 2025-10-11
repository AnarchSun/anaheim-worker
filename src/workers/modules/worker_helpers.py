# src/workers/modules/hyper_optimal_worker_helpers.py
import queue
from pathlib import Path

from .anaheim_worker_safe import log, shutdown_event


# -----------------------
# Real worker functions
# -----------------------

def delegate_to_copilot(task: dict, llm_queue: queue.Queue = None):
    """
    Envoie une tâche à la queue LLM pour traitement par Copilot.
    Si llm_queue est None, utilise la queue globale.
    """
    if llm_queue is None:
        from .anaheim_worker_safe import llm_queue
        llm_queue = llm_queue
    log(f"🤖 Delegating task to Copilot: {task.get('type', 'unknown')}")
    llm_queue.put(task)

def generate_copilot_fail_report(failures: list, report_path: Path = None):
    """
    Génère un rapport simple des échecs Copilot.
    """
    if report_path is None:
        report_path = Path("/tmp/copilot_fail_report.txt")
    log(f"📝 Generating Copilot fail report: {len(failures)} entries")
    with report_path.open("w", encoding="utf-8") as f:
        for entry in failures:
            f.write(f"{entry}\n")
    return report_path

def handle_shutdown():
    """
    Active le signal d'arrêt pour tous les threads du worker.
    """
    log("⚡ Shutdown initiated")
    shutdown_event.set()

def init_db(db_path: Path = None):
    """
    Stub simple pour l'initialisation de la DB.
    Peut être remplacé par une vraie initialisation sqlite/postgres.
    """
    if db_path is None:
        db_path = Path("/tmp/anarcrypt_worker.db")
    log(f"💾 Initializing database at {db_path}")
    db_path.touch(exist_ok=True)
    return db_path
