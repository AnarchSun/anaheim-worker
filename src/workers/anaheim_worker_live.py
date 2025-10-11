# PATH: anaheim_worker_live.py

import json
import os
import queue
import threading
import time
from pathlib import Path
from typing import List, Optional, Dict
from git import Repo, InvalidGitRepositoryError, NoSuchPathError

from ts_worker import auto_ts_fix_cycle, handle_ts_error  # <-- live TS resolver
from git_utils import repo_open, create_branch_if_missing, commit_all, flush_to_flood

# -----------------------
# Globals
# -----------------------
DB_PATH = Path("memory.sqlite")
shutdown_event = threading.Event()
llm_queue = queue.Queue()

REPO_PATH_FALLBACK = "/home/anarchsun/RustroverProjects/anarcrypt.sol/anaheim-worker/anaheim-putsch-self-governance-solana-dapp"
PROJECT_PATH = Path(os.getenv("REPO_PATH", REPO_PATH_FALLBACK)).resolve()
DIAGNOSTICS_DIR = Path("diagnostics")
DIAGNOSTICS_DIR.mkdir(exist_ok=True)
COPILOT_DELEGATIONS_LOG = DIAGNOSTICS_DIR / "copilot_delegations.log"
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
# Worker threads
# -----------------------
def worker_thread_cycle(task_source_queue: queue.Queue):
    while not shutdown_event.is_set():
        try:
            task = task_source_queue.get(timeout=2)
            if isinstance(task, dict):
                handle_ts_error(task)
            task_source_queue.task_done()
        except queue.Empty:
            continue

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
            entries = [b.strip() for b in content.split("-" * 60) if b.strip()]
            for block in entries:
                ts_error = {"fileName": "<unknown>", "messageText": block[:80], "code": "???"}
                handle_ts_error(ts_error)
            time.sleep(interval)
        except Exception as e:
            log(f"💥 copilot_retrier error: {repr(e)}")
            time.sleep(interval)

# -----------------------
# Auto TS fix cycle with buffer & cooldown
# -----------------------
def auto_ts_fix_cycle_safe(
        repo_obj: Optional[Repo] = None,
        last_commit_time: float = 0.0,
        min_commit_interval: int = 300,
        target_branch: str = "Orion",
        action_buffer: Optional[List[dict]] = None
) -> tuple[List[dict], float]:

    if repo_obj is None:
        return [], last_commit_time

    if action_buffer is None:
        action_buffer = []

    applied_actions, _ = auto_ts_fix_cycle(
        repo_obj=repo_obj,
        last_commit_time=last_commit_time,
        min_commit_interval=min_commit_interval,
        target_branch=target_branch
    )

    if applied_actions:
        action_buffer.extend(applied_actions)
        now_ts = time.time()
        if (now_ts - last_commit_time) >= min_commit_interval:
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
# Main worker safe
# -----------------------
def main_worker_safe(num_threads: int = 3):
    repo_obj = repo_open()
    if not repo_obj:
        log("❌ Repo not available, exiting.")
        return

    buffers = {"Orion": [], "Orion-Exploration": []}
    last_commit_times = {"Orion": 0.0, "Orion-Exploration": 0.0}

    threads = [
        threading.Thread(target=worker_thread_cycle, args=(llm_queue,), name=f"worker-{i+1}", daemon=True)
        for i in range(num_threads)
    ]
    for t in threads:
        t.start()
        log(f"🧵 Started {t.name}")

    retrier = threading.Thread(target=copilot_retrier, name="copilot-retrier", daemon=True)
    retrier.start()
    log("🛰️ Copilot retrier daemon started.")

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
            time.sleep(60)

    except KeyboardInterrupt:
        shutdown_event.set()
    finally:
        shutdown_event.set()
        for t in threads:
            t.join(timeout=2)
        retrier.join(timeout=2)
        log("✅ main_worker_safe stopped cleanly.")

if __name__ == "__main__":
    main_worker_safe()
