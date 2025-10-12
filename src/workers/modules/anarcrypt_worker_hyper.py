#!/usr/bin/env python3
import argparse
import queue
import threading
import time
import pickle
from pathlib import Path
from workers.modules.anaheim_worker_safe import (
    PROJECT_PATH, shutdown_event, llm_queue, log,
    start_hot_reload, init_db, worker_thread_cycle, handle_shutdown
)

LLM_QUEUE_PATH = PROJECT_PATH / "llm_queue_state.pkl"

def save_queue_state():
    """Sauvegarde la queue LLM dans un fichier"""
    tasks = list(llm_queue.queue)
    with LLM_QUEUE_PATH.open("wb") as f:
        pickle.dump(tasks, f)
    log(f"💾 Saved {len(tasks)} tasks to queue state.")

def load_queue_state():
    """Restaurer les tâches en attente depuis le fichier"""
    if LLM_QUEUE_PATH.exists():
        tasks = pickle.load(LLM_QUEUE_PATH.open("rb"))
        for t in tasks:
            llm_queue.put(t)
        log(f"💾 Loaded {len(tasks)} tasks from saved queue.")

def hyper_worker_main(num_threads: int = 4, dry_run: bool = True):
    """Hyper Safe Worker complet avec threads, queue, hot reload et sauvegarde"""
    log(f"🚀 Hyper Safe Worker started | threads={num_threads} | dry_run={dry_run}")

    # Hot reload + DB
    start_hot_reload()
    init_db()

    # Restaurer la queue si elle existe
    load_queue_state()

    # Lancer les threads
    task_queue = llm_queue  # On utilise la queue globale
    threads = []
    for i in range(num_threads):
        t = threading.Thread(target=worker_thread_cycle, args=(i+1, task_queue), daemon=True)
        threads.append(t)
        t.start()

    # Tâches initiales si queue vide
    if task_queue.empty():
        for n in range(5):
            task_queue.put({"type": "init", "payload": f"task_{n}"})

    try:
        while not shutdown_event.is_set():
            time.sleep(2)
            log("💤 Main hyper worker heartbeat…")
    except KeyboardInterrupt:
        log("⚡ Ctrl+C received, shutting down...")
        handle_shutdown()
    finally:
        # Sauvegarder la queue avant de fermer
        save_queue_state()

        # Attendre la fin des threads
        for t in threads:
            t.join(timeout=2)
        log("✅ Hyper Safe Worker terminated cleanly.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Anarcrypt Hyper Worker Ultimate")
    parser.add_argument("--run", action="store_true", help="Run in active mode")
    parser.add_argument("--dry-run", action="store_true", help="Run in dry mode")
    parser.add_argument("--threads", type=int, default=4, help="Number of worker threads")
    args = parser.parse_args()

    dry_run = not args.run or args.dry_run
    if dry_run:
        log("💡 Running Hyper Worker in dry-run mode…")
    else:
        log("🚀 Running Hyper Worker ACTIVE…")

    hyper_worker_main(num_threads=args.threads, dry_run=dry_run)
