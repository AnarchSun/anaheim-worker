#!/usr/bin/env python3
import argparse
import subprocess
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

def read_todo_instructions(folder_path: Path):
    """Lit le TODO.md d’un dossier et retourne les lignes"""
    todo_file = folder_path / "TODO.md"
    if todo_file.exists():
        with todo_file.open("r", encoding="utf-8") as f:
            return f.read().splitlines()
    return []

def build_and_run_dapp(dapp_path_local: Path, use_pnpm: bool = False):
    """Build et run le dapp, retourne le process et le port utilisé"""
    build_cmd = ["pnpm", "build"] if use_pnpm else ["yarn", "build"]
    subprocess.run(build_cmd, cwd=dapp_path_local, check=True)
    dev_cmd = ["pnpm", "dev"] if use_pnpm else ["yarn", "dev"]
    dev_process = subprocess.Popen(dev_cmd, cwd=dapp_path_local)
    port = 3000  # Par défaut Next.js dev
    return dev_process, port

def hyper_worker_main(dapp_path_local: Path, num_threads_local: int = 4, dry_run_local: bool = True):
    """Hyper Safe Worker complet avec threads, queue, hot reload et sauvegarde"""
    log(f"🚀 Hyper Safe Worker started | threads={num_threads_local} | dry_run={dry_run_local}")

    # Hot reload + DB
    start_hot_reload()
    init_db()

    # Restaurer queue
    load_queue_state()

    # Charger les TODO.md pour créer des tâches
    todo_tasks = read_todo_instructions(dapp_path_local)
    for task in todo_tasks:
        llm_queue.put({"type": "todo", "payload": task})
        log(f"🔹 TODO queued: {task}")

    # Lancer threads
    threads = []
    for i in range(num_threads_local):
        t = threading.Thread(target=worker_thread_cycle, args=(i+1, llm_queue, dry_run_local), daemon=True)
        threads.append(t)
        t.start()

    # Tâches initiales si queue vide
    if llm_queue.empty():
        for n in range(5):
            llm_queue.put({"type": "init", "payload": f"task_{n}"})

    try:
        while not shutdown_event.is_set():
            time.sleep(2)
            log("💤 Main hyper worker heartbeat…")
    except KeyboardInterrupt:
        log("⚡ Ctrl+C received, shutting down...")
        handle_shutdown()
    finally:
        save_queue_state()
        for t in threads:
            t.join(timeout=2)
        log("✅ Hyper Safe Worker terminated cleanly.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Anarcrypt Hyper Worker Ultimate")
    parser.add_argument("--run", action="store_true", help="Run in active mode")
    parser.add_argument("--dry-run", action="store_true", help="Run in dry mode")
    parser.add_argument("--threads", type=int, default=4, help="Number of worker threads")
    parser.add_argument("--dapp", type=str, required=True, help="Path to the dapp folder")
    parser.add_argument("--use-pnpm", action="store_true", help="Use pnpm instead of yarn for build/dev")
    args = parser.parse_args()

    dapp_path_arg = Path(args.dapp).resolve()
    dry_run_flag_arg = not args.run or args.dry_run

    if dry_run_flag_arg:
        log("💡 Running Hyper Worker in dry-run mode…")
    else:
        log("🚀 Running Hyper Worker ACTIVE…")

    hyper_worker_main(
        dapp_path_local=dapp_path_arg,
        num_threads_local=args.threads,
        dry_run_local=dry_run_flag_arg
    )
