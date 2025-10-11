# PATH: super_worker_hot_reload.py

import json
import os
import queue
import threading
import time
from pathlib import Path
from typing import Optional, List, Dict, Union
from git import Repo, InvalidGitRepositoryError, GitCommandError
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

from ts_worker import auto_ts_fix_cycle, handle_ts_error

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
FLOOD_BRANCH = "<flood>"

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
# Safe auto TS fix cycle
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
        if repo_obj and (now_ts - last_commit_time >= 300):  # commit max toutes les 5 min
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
# Hot reload handler
# -----------------------
class TSErrorHandler(FileSystemEventHandler):
    def __init__(self, repo_obj: Repo):
        self.repo = repo_obj

    def on_modified(self, event):
        if event.src_path.endswith(".ts"):
            log(f"📂 Detected TS modification: {event.src_path}")
            submit_task(event.src_path)

# -----------------------
# Task injection
# -----------------------
def submit_task(task: Union[str, dict]):
    llm_queue.put(task)
    log(f"📥 Task submitted: {str(task)[:100]}")

# -----------------------
# Main orchestrator with hot reload
# -----------------------
def main_hot_reload(num_threads: int = 4):
    repo_obj = repo_open()
    if not repo_obj:
        log("❌ Repo not available, exiting orchestrator.")
        return

    buffers = {"Orion": [], "Orion-Exploration": []}
    last_commit_times = {"Orion": 0.0, "Orion-Exploration": 0.0}

    threads = [threading.Thread(target=worker_thread_cycle, args=(llm_queue,), name=f"worker-{i+1}", daemon=True)
               for i in range(num_threads)]
    for t in threads:
        t.start()
        log(f"🧵 Started {t.name}")

    # Watchdog
    observer = Observer()
    observer.schedule(TSErrorHandler(repo_obj), str(PROJECT_PATH), recursive=True)
    observer.start()
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
            time.sleep(10)  # boucle rapide pour commit et flush
    except KeyboardInterrupt:
        shutdown_event.set()
    finally:
        shutdown_event.set()
        observer.stop()
        observer.join()
        for t in threads:
            t.join(timeout=2)
        log("✅ Hot reload orchestrator stopped cleanly.")

if __name__ == "__main__":
    main_hot_reload(num_threads=4)
