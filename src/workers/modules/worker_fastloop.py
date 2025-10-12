# FILE: src/workers/modules/worker_fastloop.py
#!/usr/bin/env python3

import os
import pickle
import queue
import sqlite3
import threading
import time
from pathlib import Path
from typing import List, Union, Optional
from git import Repo, GitCommandError

# -----------------------
# Globals
# -----------------------
PROJECT_PATH = Path(os.getenv("REPO_PATH", "/home/anarchsun/RustroverProjects/anarcrypt.sol/anaheim-worker")).resolve()
DB_PATH = PROJECT_PATH / "anarcrypt_worker.db"
LLM_QUEUE_PATH = PROJECT_PATH / "llm_queue_state.pkl"
DIAGNOSTICS_DIR = PROJECT_PATH / "diagnostics"
DIAGNOSTICS_DIR.mkdir(exist_ok=True)
COPILOT_DELEGATIONS_LOG = DIAGNOSTICS_DIR / "copilot_delegations.log"
FLOOD_BRANCH = "<flood>"

llm_queue: queue.Queue[Union[str, dict]] = queue.Queue()
shutdown_event = threading.Event()
pause_event = threading.Event()  # <-- added pause event
DRY_RUN = os.getenv("WORKER_DRY_RUN", "true").lower() == "true"
WORKER_DELAY = float(os.getenv("WORKER_DELAY", "0.5"))  # seconds per task, default 0.5

LOGS_DIR = PROJECT_PATH / "logs"
LOGS_DIR.mkdir(exist_ok=True)
HYPER_WORKER_LOG = LOGS_DIR / "hyper_worker.log"


# -----------------------
# Logging
# -----------------------
def log(msg: str):
    ts = time.strftime("%Y-%m-%d %H:%M:%S")
    line = f"[worker_fastloop][{ts}] {msg}"
    print(line)
    try:
        with HYPER_WORKER_LOG.open("a", encoding="utf-8") as f:
            f.write(line + "\n")
    except OSError:
        pass


# -----------------------
# Repo helpers
# -----------------------
def repo_open() -> Optional[Repo]:
    try:
        return Repo(PROJECT_PATH)
    except Exception as e:
        log(f"❌ Failed to open repo: {repr(e)}")
        return None

def create_branch_if_missing(repo: Repo, branch_name: str):
    if branch_name not in repo.branches:
        repo.git.branch(branch_name)
        log(f"🌿 Created branch {branch_name}")

def commit_all(repo: Repo, message: str, action_buffer: Optional[List[dict]] = None, target_branch: str = ""):
    if DRY_RUN:
        log(f"💡 Dry-run enabled, skipping commit for {len(action_buffer) if action_buffer else 0} actions on branch {target_branch}")
        return
    try:
        repo.git.add(all=True)
        repo.index.commit(message)
        log(f"✅ Committed: {message}")
    except GitCommandError as e:
        log(f"⚠️ Commit failed: {repr(e)}")

def flush_to_flood(repo: Repo, branch_name: str):
    try:
        if FLOOD_BRANCH not in repo.branches:
            repo.git.branch(FLOOD_BRANCH)
        repo.git.checkout(FLOOD_BRANCH)
        try:
            repo.git.merge(branch_name, "--no-ff", "--strategy-option=theirs")
        except GitCommandError:
            repo.git.merge("--abort")
            log(f"⚠️ Merge conflict during flush_to_flood on {branch_name}")
            return
        commits = list(repo.iter_commits(FLOOD_BRANCH))
        if len(commits) > 250:
            repo.git.reset("--hard", commits[249].hexsha)
            log("♻️ FLOOD branch trimmed to 250 commits")
        if not DRY_RUN:
            repo.git.push("--set-upstream", "origin", FLOOD_BRANCH)
        log(f"🌊 FLOOD branch updated with {branch_name}")
    except Exception as e:
        log(f"💥 flush_to_flood failed: {repr(e)}")

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
# Queue persistence
# -----------------------
def save_queue_state():
    tasks = list(llm_queue.queue)
    try:
        # Use Path.open for Path objects, NO type hint after "as f", and DO NOT use built-in open for Path!
        # This returns a file object with 'write' and 'writable' methods supporting bytes.
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
# Hot reload (background)
# -----------------------
def start_hot_reload():
    log("♻️ Hot Reload System initialized")
    def watcher():
        while not shutdown_event.is_set():
            time.sleep(5)
            log("🔁 [hot-reload] Heartbeat pulse…")
    t = threading.Thread(target=watcher, daemon=True)
    t.start()
    return t

# -----------------------
# Worker threads
# -----------------------

def worker_thread_cycle(task_source_queue: queue.Queue, thread_id: int = 0):
    log(f"🧵 Worker thread #{thread_id} started.")
    while not shutdown_event.is_set():
        try:
            task = task_source_queue.get(timeout=2)
        except queue.Empty:
            continue

        try:
            file_path = PROJECT_PATH / task.get("file", "")
            desc = task.get("description", "<no description>")
            action_type = task.get("action_type", "generic")
            patch = task.get("patch", None)

            log(f"⚙️ Worker #{thread_id} processing task: file={file_path}, type={action_type}, description={desc}")

            # Apply patch if provided
            if patch and file_path.exists():
                with file_path.open("w", encoding="utf-8") as f:
                    f.write(patch)
                log(f"✅ Worker #{thread_id} applied patch to {file_path}")

            time.sleep(0.5)  # slow down

            # Save task log
            log_file = LOGS_DIR / f"{time.strftime('%Y%m%d')}_tasks.log"
            with log_file.open("a", encoding="utf-8") as f:
                f.write(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {task}\n")

            log(f"✅ Worker #{thread_id} completed task: {desc}")

        except Exception as e:
            log(f"💥 Worker #{thread_id} error: {repr(e)}")
        finally:
            task_source_queue.task_done()

    log(f"🛑 Worker thread #{thread_id} exiting.")


# -----------------------
# Copilot retrier
# -----------------------
def copilot_retrier(interval: int = 120):
    while not shutdown_event.is_set():
        try:
            if not COPILOT_DELEGATIONS_LOG.exists():
                time.sleep(interval)
                continue
            content = COPILOT_DELEGATIONS_LOG.read_text(encoding="utf-8").strip()
            if not content:
                time.sleep(interval)
                continue
            entries = [b.strip() for b in content.split("-"*60) if b.strip()]
            for block in entries:
                log(f"⚠️ Copilot retrier detected block: {block[:80]}")
            time.sleep(interval)
        except Exception as e:
            log(f"💥 copilot_retrier error: {repr(e)}")
            time.sleep(interval)

# -----------------------
# Auto TS fix safe
# -----------------------
def auto_ts_fix_cycle_safe(repo_obj: Optional[Repo],
                           last_commit_time: float,
                           min_commit_interval: int = 300,
                           target_branch: str = "Orion",
                           action_buffer: Optional[List[dict]] = None) -> tuple[List[dict], float]:
    applied_actions: List[dict] = []
    if action_buffer is None:
        action_buffer = []

    if not applied_actions:
        return applied_actions, last_commit_time

    action_buffer.extend(applied_actions)
    now_ts = time.time()
    if repo_obj and (now_ts - last_commit_time >= min_commit_interval) and action_buffer:
        try:
            create_branch_if_missing(repo_obj, target_branch)
            repo_obj.git.checkout(target_branch)
            commit_all(repo_obj, f"Auto TS update - {len(action_buffer)} actions",
                       action_buffer=action_buffer, target_branch=target_branch)
            flush_to_flood(repo_obj, target_branch)
            last_commit_time = now_ts
            action_buffer.clear()
        except Exception as e:
            log(f"⚠️ Commit failed: {repr(e)}")
    return applied_actions, last_commit_time

# -----------------------
# TODO loader
# -----------------------
def read_todo_instructions(dapp_path: Path) -> List[str]:
    todos = []
    for file in dapp_path.rglob("TODO.md"):
        try:
            with file.open("r", encoding="utf-8") as f:
                todos.extend(f.read().splitlines())
        except Exception as e:
            log(f"💥 Failed to read {file}: {repr(e)}")
    return todos

# -----------------------
# Fastloop main
# -----------------------
def fastloop_main(dapp_path: Optional[Path] = None, num_threads: int = 4, iteration_sleep: float = 2.0):
    log("🛠️ Anaheim Worker hyper-fastloop started")
    repo = repo_open()
    if not repo:
        log("❌ Repo unavailable, fastloop exiting")
        return

    init_db()
    start_hot_reload()
    load_queue_state()

    # Load TODO.md tasks
    if dapp_path:
        todos = read_todo_instructions(dapp_path)
        for t in todos:
            llm_queue.put({"type": "todo", "payload": t})
            log(f"🔹 TODO queued: {t}")

    # Start worker threads
    threads = [
        threading.Thread(target=worker_thread_cycle, args=(llm_queue, i), daemon=True)
        for i in range(num_threads)
    ]
    for t in threads:
        t.start()

    # Copilot retrier thread
    retrier_thread = threading.Thread(target=copilot_retrier, daemon=True)
    retrier_thread.start()

    iteration = 0
    try:
        while not shutdown_event.is_set():
            iteration += 1
            log(f"🔁 Iteration {iteration}")

            # Pause workers, snapshot queue, then resume
            if not llm_queue.empty():
                pause_event.set()
                save_queue_state()
                log(f"💾 Snapshot mid-run: {list(llm_queue.queue)}")
                pause_event.clear()

            time.sleep(iteration_sleep)  # slow down loop
    except KeyboardInterrupt:
        log("⚡ Ctrl+C received, shutting down...")
        shutdown_event.set()
    finally:
        save_queue_state()
        log("✅ Hyper-fastloop terminated cleanly.")


