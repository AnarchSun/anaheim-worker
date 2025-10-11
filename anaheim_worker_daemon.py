# anaheim_worker_daemon.py
import threading
import time
from typing import List, Dict

from worker_full import (
    repo_open,
    auto_ts_fix_cycle,
    shutdown_event,
    log,
    flush_to_flood,
    worker_thread_cycle,
    copilot_retrier,
    safe_commit
)
from queue import Queue

# Global queue pour LLM/TS patches
llm_queue: Queue = Queue()

def main_daemon(num_orion_threads: int = 3, num_explore_threads: int = 2):
    """
    Main daemon orchestration:
    - Launch Orion branch workers
    - Launch Orion-Exploration workers
    - Manage flush to <flood>
    """
    repo_obj = repo_open()
    if not repo_obj:
        log("❌ Repo unavailable. Exiting main_daemon.")
        return

    # --- Orion workers ---
    orion_threads = [
        threading.Thread(target=worker_thread_cycle, args=(llm_queue,), name=f"orion-worker-{i+1}", daemon=True)
        for i in range(num_orion_threads)
    ]
    for t in orion_threads:
        t.start()
        log(f"🧵 Started {t.name} for Orion branch")

    orion_retrier = threading.Thread(target=copilot_retrier, name="orion-copilot-retrier", daemon=True)
    orion_retrier.start()
    log("🛰️ Orion Copilot retrier daemon started.")

    # --- Orion-Exploration worker ---
    exploration_thread = threading.Thread(
        target=exploration_worker_loop,
        name="orion-exploration-worker",
        daemon=True
    )
    exploration_thread.start()
    log("🚀 Orion-Exploration worker started.")

    # --- Main loop: periodically flush to <flood> if necessary ---
    try:
        while not shutdown_event.is_set():
            # Flush orphan patches or errors periodically
            flush_to_flood()
            time.sleep(120)  # every 2 minutes
    except KeyboardInterrupt:
        shutdown_event.set()
    finally:
        shutdown_event.set()
        for t in orion_threads:
            t.join(timeout=2)
        orion_retrier.join(timeout=2)
        exploration_thread.join(timeout=2)
        log("✅ main_daemon stopped cleanly.")


# --- Exploration worker loop ---
def exploration_worker_loop():
    """
    Worker for Orion-Exploration branch.
    Handles batch commits + flush to <flood> for innovation.
    """
    repo_obj = repo_open()
    if not repo_obj:
        log("❌ Repo unavailable for exploration_worker_loop.")
        return

    # Worker threads for LLM queue
    threads = [
        threading.Thread(target=worker_thread_cycle, args=(llm_queue,), name=f"explore-worker-{i+1}", daemon=True)
        for i in range(2)
    ]
    for t in threads:
        t.start()
        log(f"🧵 Started {t.name} for exploration branch")

    retrier = threading.Thread(target=copilot_retrier, name="exploration-copilot-retrier", daemon=True)
    retrier.start()
    log("🛰️ Exploration Copilot retrier daemon started.")

    last_commit_time: float = 0.0
    min_commit_interval: int = 300  # 5 min cooldown

    try:
        while not shutdown_event.is_set():
            applied_actions, last_commit_time = auto_ts_fix_cycle(
                repo_obj=repo_obj,
                last_commit_time=last_commit_time,
                min_commit_interval=min_commit_interval
            )

            if applied_actions:
                log(f"🛠 Exploration auto_ts_fix_cycle applied {len(applied_actions)} actions.")
                safe_commit(repo_obj, branch_name="Orion-Exploration", actions=applied_actions)
                flush_to_flood(applied_actions)

            time.sleep(90)
    finally:
        shutdown_event.set()
        for t in threads:
            t.join(timeout=2)
        retrier.join(timeout=2)
        log("✅ exploration_worker_loop stopped cleanly.")


if __name__ == "__main__":
    main_daemon()
