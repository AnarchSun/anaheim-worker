# anaheim_worker.py

import json
import os
import queue
import threading
import time
from pathlib import Path
from typing import Optional, List, Dict
from git import Repo, InvalidGitRepositoryError, NoSuchPathError

# -----------------------
# Globals
# -----------------------
DB_PATH = Path("memory.sqlite")
COPILOT_FAIL_LOG = Path("patches/copilot_fail_log.json")
shutdown_event = threading.Event()
llm_queue = queue.Queue()
error_fail_count: Dict[str, int] = {}
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
# Dummy LLM and TS handler
# -----------------------
def ask_llm(prompt: str) -> str:
    log(f"🤖 ask_llm called with prompt: {prompt[:100]}...")
    return "[]"

def handle_ts_error(error_block: dict):
    log(f"🛠 handle_ts_error called for {error_block.get('fileName', '<unknown>')}")

def apply_patch(patch: dict):
    log(f"Applied patch: {patch}")

def apply_ts_actions(actions: List[dict]):
    for patch in actions:
        apply_patch(patch)

# -----------------------
# Repo helpers
# -----------------------
def repo_open() -> Optional[Repo]:
    try:
        log(f"🔍 Opening repo at {PROJECT_PATH}")
        return Repo(PROJECT_PATH)
    except (InvalidGitRepositoryError, NoSuchPathError) as e:
        log(f"❌ Invalid repo: {repr(e)}")
        return None

def create_branch_if_missing(repo: Repo, branch_name: str):
    if branch_name not in repo.branches:
        repo.git.branch(branch_name)
        log(f"🌿 Created branch {branch_name}")

def commit_all(repo: Repo, message: str):
    repo.git.add(all=True)
    repo.index.commit(message)
    log(f"✅ Committed: {message}")

def flush_to_flood(repo: Repo, branch_name: str):
    create_branch_if_missing(repo, FLOOD_BRANCH)
    repo.git.checkout(FLOOD_BRANCH)
    repo.git.merge(branch_name)
    # Limit flood branch to 250 commits
    commits = list(repo.iter_commits(FLOOD_BRANCH))
    if len(commits) > 250:
        oldest_hash = commits[249].hexsha
        repo.git.reset("--hard", oldest_hash)
        log(f"♻️ FLOOD branch trimmed to 250 commits")
    repo.git.push("--set-upstream", "origin", FLOOD_BRANCH)
    log(f"🌊 Flushed {branch_name} to FLOOD branch")

# anaheim_worker.py (updated safe main_worker)

# ... toutes les imports et fonctions précédentes restent inchangées ...

# -----------------------
# Auto TypeScript fix cycle with buffer
# -----------------------
def auto_ts_fix_cycle_safe(
        repo_obj: Optional[Repo] = None,
        last_commit_time: float = 0.0,
        min_commit_interval: int = 300,
        target_branch: str = "Orion",
        action_buffer: Optional[List[dict]] = None
) -> tuple[List[dict], float]:
    applied_actions, last_commit_time = auto_ts_fix_cycle(
        repo_obj=repo_obj,
        last_commit_time=last_commit_time,
        min_commit_interval=min_commit_interval,
        target_branch=target_branch
    )

    if action_buffer is not None and applied_actions:
        action_buffer.extend(applied_actions)
        # Commit only if cooldown elapsed
        now_ts = time.time()
        if repo_obj and (now_ts - last_commit_time) >= min_commit_interval:
            try:
                create_branch_if_missing(repo_obj, target_branch)
                repo_obj.git.checkout(target_branch)
                commit_all(repo_obj, f"Auto TS update - {len(action_buffer)} actions")
                flush_to_flood(repo_obj, target_branch)
                last_commit_time = now_ts
                action_buffer.clear()  # clear buffer after commit
            except Exception as e:
                log(f"⚠️ Commit failed for {target_branch}: {repr(e)}")

    return applied_actions, last_commit_time

# -----------------------
# Safe main worker
# -----------------------
def main_worker_safe(num_threads: int = 3):
    repo_obj = repo_open()
    buffers = {"Orion": [], "Orion-Exploration": []}

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

    last_commit_times = {"Orion": 0.0, "Orion-Exploration": 0.0}
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
                patches_json = ask_llm(task)
                try:
                    patches = json.loads(patches_json)
                except (json.JSONDecodeError, TypeError):
                    patches = []
                for patch in patches:
                    apply_patch(patch)
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
# Main worker loop
# -----------------------
def main_worker(num_threads: int = 3):
    repo_obj = repo_open()
    if not repo_obj:
        log("❌ Repo not available, exiting main_worker.")
        return

    orion_buffer: List[dict] = []
    exploration_buffer: List[dict] = []

    threads = [threading.Thread(target=worker_thread_cycle, args=(llm_queue,), name=f"worker-{i+1}", daemon=True)
               for i in range(num_threads)]
    for t in threads:
        t.start()
        log(f"🧵 Started {t.name}")

    retrier = threading.Thread(target=copilot_retrier, name="copilot-retrier", daemon=True)
    retrier.start()
    log("🛰️ Copilot retrier daemon started.")

    last_commit_time_orion: float = 0.0
    last_commit_time_expl: float = 0.0

    try:
        while not shutdown_event.is_set():
            applied_orion, last_commit_time_orion = auto_ts_fix_cycle_dev(
                repo_obj=repo_obj,
                last_commit_time=last_commit_time_orion,
                target_branch="Orion",
                action_buffer=orion_buffer
            )
            if applied_orion:
                log(f"🛠 Orion cycle applied {len(applied_orion)} actions.")

            applied_expl, last_commit_time_expl = auto_ts_fix_cycle_dev(
                repo_obj=repo_obj,
                last_commit_time=last_commit_time_expl,
                target_branch="Orion-Exploration",
                action_buffer=exploration_buffer
            )
            if applied_expl:
                log(f"🛠 Orion-Exploration cycle applied {len(applied_expl)} actions.")

            time.sleep(60)

    except KeyboardInterrupt:
        shutdown_event.set()
    finally:
        shutdown_event.set()
        for t in threads:
            t.join(timeout=2)
        retrier.join(timeout=2)
        log("✅ main_worker stopped cleanly.")

if __name__ == "__main__":
    main_worker(num_threads=3)
