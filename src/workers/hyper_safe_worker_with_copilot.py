# PATH: hyper_safe_worker_with_copilot.py

import os
import queue
import threading
from pathlib import Path
from typing import Optional, List, Union

from git import InvalidGitRepositoryError, GitCommandError
from git import Repo

from ts_worker import handle_ts_error  # assure que ts_worker.py est correct

# -----------------------
# Globals
# -----------------------
DB_PATH = Path("memory.sqlite")
shutdown_event = threading.Event()
llm_queue: queue.Queue[Union[str, dict]] = queue.Queue()
REPO_PATH_FALLBACK = "/home/anarchsun/RustroverProjects/anarcrypt.sol/anaheim-worker/anaheim-putsch-self-governance-solana-dapp"
PROJECT_PATH = Path(os.getenv("REPO_PATH", REPO_PATH_FALLBACK)).resolve()
DIAGNOSTICS_DIR = Path("diagnostics")
DIAGNOSTICS_DIR.mkdir(exist_ok=True)
COPILOT_DELEGATIONS_LOG = DIAGNOSTICS_DIR / "copilot_delegations.log"
FLOOD_BRANCH = "<flood>"

MAX_COMMITS_PER_BRANCH = 1
COMMIT_INTERVAL = 300  # 5 min
BUFFER_LIMIT = 100

# -----------------------
# Logging
# -----------------------
def log(msg: str):
    line = f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {msg}"
    print(line)
    try:
        with open("worker.log", "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except OSError:
        pass

# -----------------------
# Repo helpers
# -----------------------
def repo_open() -> Optional[Repo]:
    try:
        log(f"🔍 Opening repo at {PROJECT_PATH}")
        return Repo(PROJECT_PATH)
    except InvalidGitRepositoryError as e:
        log(f"❌ Invalid repo: {repr(e)}")
        return None

def create_branch_if_missing(repo: Repo, branch_name: str):
    if branch_name not in repo.branches:
        repo.git.branch(branch_name)
        log(f"🌿 Created branch {branch_name}")

def commit_all(repo: Repo, message: str):
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
            oldest_hash = commits[249].hexsha
            repo.git.reset("--hard", oldest_hash)
            log(f"♻️ FLOOD branch trimmed to 250 commits")
        repo.git.push("--set-upstream", "origin", FLOOD_BRANCH)
        log(f"🌊 FLOOD branch updated with {branch_name}")
    except Exception as e:
        log(f"💥 flush_to_flood failed: {repr(e)}")

# -----------------------
# Worker threads
# -----------------------
def worker_thread_cycle(task_source_queue: queue.Queue):
    while not shutdown_event.is_set():
        try:
            task = task_source_queue.get(timeout=2)
            if isinstance(task, dict):
                handle_ts_error(task)
            elif isinstance(task, str):
                try:
                    patches, _ = auto_ts_fix_cycle(task)
                    for patch in patches:
                        log(f"🛠 Applied patch from task: {patch}")
                except Exception as e:
                    log(f"💥 Worker failed on task: {repr(e)}")
            task_source_queue.task_done()
        except queue.Empty:
            continue

# -----------------------
# Safe auto TS fix cycle with buffer & rate limit
# -----------------------
def auto_ts_fix_cycle_safe(repo_obj: Optional[Repo],
                           last_commit_time: float,
                           target_branch: str,
                           action_buffer: Optional[List[dict]]) -> tuple[List[dict], float]:
    applied_actions, last_commit_time = auto_ts_fix_cycle(repo_obj=repo_obj,
                                                          target_branch=target_branch,
                                                          last_commit_time=last_commit_time)
    if action_buffer is not None and applied_actions:
        action_buffer.extend(applied_actions)
        now_ts = time.time()
        if repo_obj and (now_ts - last_commit_time >= COMMIT_INTERVAL or len(action_buffer) >= BUFFER_LIMIT):
            try:
                create_branch_if_missing(repo_obj, target_branch)
                repo_obj.git.checkout(target_branch)
                commit_all(repo_obj, f"Auto TS update - {len(action_buffer)} actions")
                flush_to_flood(repo_obj, target_branch)
                last_commit_time = now_ts
                action_buffer.clear()
            except Exception as e:
                log(f"⚠️ Commit failed for {target_branch}: {repr(e)}")
    return applied_actions, last_commit_time

# -----------------------
# Hot reload TS handler
# -----------------------
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import threading
import time
from git import Repo
from anaheim_worker import repo_open, log, auto_ts_fix_cycle

class TSErrorHandler(FileSystemEventHandler):
    def __init__(self, repo: Optional[Repo]):
        self.repo = repo

    def on_modified(self, event):
        if event.src_path.endswith(".ts"):
            log(f"📂 Detected TS modification: {event.src_path}")
            if self.repo:
                applied_actions, _ = auto_ts_fix_cycle(repo_obj=self.repo)
                if applied_actions:
                    log(f"🛠 Hot reload applied {len(applied_actions)} actions.")

# -----------------------
# Start hot reload observer
# -----------------------
def start_hot_reload(repo: Optional[Repo], watch_path: str = "."):
    if repo is None:
        log("❌ Repo not available, hot reload not started.")
        return

    event_handler = TSErrorHandler(repo)
    observer = Observer()
    observer.schedule(event_handler, path=watch_path, recursive=True)
    observer_thread = threading.Thread(target=observer.start, name="hot-reload-observer", daemon=True)
    observer_thread.start()
    log(f"🛰️ Hot reload started on path: {watch_path}")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()
    log("✅ Hot reload stopped cleanly.")

# -----------------------
# Example usage
# -----------------------
if __name__ == "__main__":
    repo_obj: Optional[Repo] = repo_open()
    start_hot_reload(repo_obj, watch_path="src")



# -----------------------
# Task injection
# -----------------------
def submit_task(task: Union[str, dict]):
    llm_queue.put(task)
    log(f"📥 Task submitted: {str(task)[:100]}")

# -----------------------
# Copilot retrier daemon
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
                ts_error = {"fileName": "<unknown>", "messageText": block[:80], "code": "???"}
                handle_ts_error(ts_error)
            time.sleep(interval)
        except Exception as e:
            log(f"💥 copilot_retrier error: {repr(e)}")
            time.sleep(interval)

# -----------------------
# Main orchestrator
# -----------------------
def main_worker_hyper_safe(num_threads: int = 4):
    repo_obj = repo_open()
    if not repo_obj:
        log("❌ Repo not available, exiting.")
        return

    buffers = {"Orion": [], "Orion-Exploration": []}
    last_commit_times = {"Orion": 0.0, "Orion-Exploration": 0.0}

    # Worker threads
    threads = [threading.Thread(target=worker_thread_cycle, args=(llm_queue,), name=f"worker-{i+1}", daemon=True)
               for i in range(num_threads)]
    for t in threads:
        t.start()
        log(f"🧵 Started {t.name}")

    # Copilot retrier
    retrier_thread = threading.Thread(target=copilot_retrier, name="copilot-retrier", daemon=True)
    retrier_thread.start()
    log("🛰️ Copilot retrier started.")

    log("👀 Hot reload observer started.")

    try:
        while not shutdown_event.is_set():
            for branch in ["Orion", "Orion-Exploration"]:
                applied_actions, last_commit_times[branch] = auto_ts_fix_cycle_safe(
                    repo_obj=repo_obj,
                    last_commit_time=last_commit_times[branch],
                    target_branch=branch,
                    action_buffer=buffers[branch]
                )
                if applied_actions:
                    log(f"🛠 {branch} applied {len(applied_actions)} actions.")
            time.sleep(10)
    except KeyboardInterrupt:
        shutdown_event.set()
    finally:
        shutdown_event.set()
        for t in threads:
            t.join(timeout=2)
        retrier_thread.join(timeout=2)
        log("✅ Hyper safe worker with copilot retrier stopped cleanly.")

if __name__ == "__main__":
    main_worker_hyper_safe(num_threads=4)
