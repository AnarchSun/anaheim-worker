#!/usr/bin/env python3
# src/workers/modules/anaheim_worker_safe.py

import os
import pickle
import queue
import sqlite3
import threading
import time
from pathlib import Path
from typing import Union, List, Optional, Tuple, cast

from git import Repo

# -----------------------
# Globals
# -----------------------
PROJECT_PATH = Path(os.getenv("REPO_PATH", "/home/anarchsun/RustroverProjects/anarcrypt.sol/anaheim-worker")).resolve()
DB_PATH = PROJECT_PATH / "anarcrypt_worker.db"
LLM_QUEUE_PATH = PROJECT_PATH / "llm_queue_state.pkl"

llm_queue: queue.Queue[Union[str, dict]] = queue.Queue()
shutdown_event = threading.Event()

# -----------------------
# Logging
# -----------------------
def log(msg: str):
    ts = time.strftime("%Y-%m-%d %H:%M:%S")
    line = f"[hyper-worker][{ts}] {msg}"
    print(line)
    try:
        with (PROJECT_PATH / "hyper_worker.log").open("a", encoding="utf-8") as f:
            f.write(line + "\n")
    except OSError:
        pass

# -----------------------
# Queue persistence
# -----------------------
def save_queue_state():
    tasks = list(llm_queue.queue)
    try:
        # Use Path.open for Path objects, no type hints, and avoid _typeshed errors!
        with LLM_QUEUE_PATH.open("wb") as f:
            pickle.dump(tasks, f)
        log(f"💾 Saved {len(tasks)} tasks to queue state.")
    except Exception as e:
        log(f"💥 save_queue_state error: {repr(e)}")


def load_queue_state():
    if LLM_QUEUE_PATH.exists():
        try:
            with LLM_QUEUE_PATH.open("rb") as f:
                tasks = pickle.load(f)
            for t in tasks:
                llm_queue.put(t)
            log(f"💾 Loaded {len(tasks)} tasks from saved queue.")
        except Exception as e:
            log(f"💥 load_queue_state error: {repr(e)}")

# -----------------------
# Worker thread
# -----------------------
def worker_thread_cycle(task_source_queue: queue.Queue):
    log(f"🧵 Worker thread started.")
    while not shutdown_event.is_set():
        try:
            task = task_source_queue.get(timeout=2)
            if isinstance(task, dict):
                # placeholder pour apply_ts_actions
                log(f"⚙️ Processing task: {task}")
            task_source_queue.task_done()
        except queue.Empty:
            continue
        except Exception as e:
            log(f"💥 Worker error: {repr(e)}")
    log(f"🛑 Worker thread exiting.")

# -----------------------
# Hot reload simulation
# -----------------------
def start_hot_reload():
    log("♻️ Hot Reload System initialized (background watcher thread active).")
    def watcher():
        while not shutdown_event.is_set():
            time.sleep(5)
            log("🔁 [hot-reload] Heartbeat pulse…")
    t = threading.Thread(target=watcher, daemon=True)
    t.start()
    return t

# -----------------------
# DB init
# -----------------------
def init_db():
    try:
        DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("""
                  CREATE TABLE IF NOT EXISTS applied_actions (
                                                                 id INTEGER PRIMARY KEY AUTOINCREMENT,
                                                                 file TEXT,
                                                                 action_type TEXT,
                                                                 symbol TEXT,
                                                                 timestamp REAL
                  )
                  """)
        c.execute("""
                  CREATE TABLE IF NOT EXISTS llm_logs (
                                                          id INTEGER PRIMARY KEY AUTOINCREMENT,
                                                          prompt TEXT,
                                                          response TEXT,
                                                          timestamp REAL
                  )
                  """)
        conn.commit()
        conn.close()
        log(f"💾 Database initialized at {DB_PATH}")
    except Exception as e:
        log(f"💥 init_db error: {repr(e)}")

# -----------------------
# Shutdown
# -----------------------
def handle_shutdown():
    log("⚡ Shutdown initiated")
    shutdown_event.set()
    while not llm_queue.empty():
        llm_queue.get_nowait()
        llm_queue.task_done()

# -----------------------
# Placeholder / Safe stubs
# -----------------------
def handle_ts_error():
    return None

def ask_llm():
    return None

# -----------------------
# Auto TS fix safe
# -----------------------
def auto_ts_fix_cycle_safe(
        repo_obj: Optional[Repo] = None,
        last_commit_time: float = 0,
        min_commit_interval: int = 300,
        target_branch: str = "Orion",
        action_buffer: Optional[List[dict]] = None
) -> Tuple[List[dict], float]:
    """
    Version "safe" de auto_ts_fix_cycle, compatible avec hyper_worker.
    """
    applied_actions: List[dict] = []
    if action_buffer is None:
        action_buffer = []

    # Placeholder: rien à appliquer ici
    if not applied_actions:
        return applied_actions, last_commit_time

    action_buffer.extend(applied_actions)
    now_ts = time.time()
    if repo_obj and (now_ts - last_commit_time >= min_commit_interval) and action_buffer:
        try:
            if target_branch not in repo_obj.branches:
                repo_obj.git.branch(target_branch)
            repo_obj.git.checkout(target_branch)
            # commit_all(repo_obj, f"Auto TS update - {len(action_buffer)} actions", action_buffer=action_buffer)
            action_buffer.clear()
        except Exception as e:
            log(f"⚠️ Commit failed: {repr(e)}")
    return applied_actions, last_commit_time

# -----------------------
# Main hyper safe worker
# -----------------------
def main_worker_safe_hyper(num_threads: int = 4):
    log("🚀 Hyper Safe Worker started")
    init_db()
    load_queue_state()
    start_hot_reload()

    threads = [threading.Thread(target=worker_thread_cycle, args=(llm_queue,), daemon=True)
               for _ in range(num_threads)]
    for t in threads:
        t.start()

    # Boucle principale
    try:
        while not shutdown_event.is_set():
            time.sleep(2)
            log("💤 Hyper worker heartbeat…")
    except KeyboardInterrupt:
        log("⚡ Ctrl+C received, shutting down...")
    finally:
        save_queue_state()
        handle_shutdown()
        for t in threads:
            t.join(timeout=2)
        log("✅ Hyper Safe Worker terminated cleanly.")

__all__ = [
    "PROJECT_PATH", "DB_PATH", "LLM_QUEUE_PATH", "shutdown_event", "llm_queue", "log",
    "start_hot_reload", "init_db", "worker_thread_cycle", "handle_shutdown",
    "handle_ts_error", "ask_llm", "save_queue_state", "load_queue_state",
    "auto_ts_fix_cycle_safe", "main_worker_safe_hyper"
]
