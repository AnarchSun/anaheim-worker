# /home/anarchsun/RustroverProjects/anarcrypt.sol/anaheim-worker/worker_core.py

import json
import os
import threading
import time
from pathlib import Path
from typing import Optional, List

from git import Repo, InvalidGitRepositoryError, NoSuchPathError

# -----------------------
# Globals
# -----------------------
shutdown_event = threading.Event()
PROJECT_PATH = Path(os.getenv("REPO_PATH", "/home/anarchsun/RustroverProjects/anarcrypt.sol/anaheim-worker")).resolve()
DIAGNOSTICS_DIR = Path("diagnostics")
DIAGNOSTICS_DIR.mkdir(exist_ok=True)
PATCHES_DIR = Path("patches")
PATCHES_DIR.mkdir(exist_ok=True)

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
# Repo utils
# -----------------------
def repo_open() -> Optional[Repo]:
    try:
        log(f"🔍 Opening repo at {PROJECT_PATH}")
        return Repo(PROJECT_PATH)
    except (InvalidGitRepositoryError, NoSuchPathError) as e:
        log(f"❌ Invalid repo: {repr(e)}")
        return None

def create_branch_if_missing(repo: Repo, branch: str):
    if branch not in repo.branches:
        repo.git.branch(branch)
        log(f"🌿 Created missing branch {branch}")

def commit_all(repo: Repo, msg: str):
    repo.git.add(A=True)
    if repo.index.diff("HEAD"):
        repo.index.commit(msg)
        log(f"💾 Git commit: {msg}")
    else:
        log("ℹ️ Git commit skipped, nothing to commit")

# -----------------------
# TS patch / LLM logic
# -----------------------
def ask_llm(prompt: str) -> str:
    """Stub LLM: returns fake patch"""
    log(f"🤖 ask_llm called with prompt: {prompt[:100]}...")
    return json.dumps([{"file": "example.ts", "change": "// LLM fix"}])

def handle_ts_error(error_block: dict):
    """Handle a TS error block"""
    log(f"🛠 handle_ts_error: {error_block.get('fileName', '<unknown>')} - {error_block.get('messageText', '')}")

def apply_patch(patch: dict):
    # Here you would really patch the file
    log(f"Applied patch to {patch.get('file', '<unknown>')}")

def apply_ts_actions(actions: List[dict]):
    for patch in actions:
        apply_patch(patch)

def flush_to_flood(patches: List[dict], branch_name: str):
    flood_dir = PATCHES_DIR / "flood"
    flood_dir.mkdir(exist_ok=True)
    flood_file = flood_dir / f"{branch_name}_{int(time.time())}.json"
    flood_file.write_text(json.dumps(patches, indent=2), encoding="utf-8")
    log(f"💦 Flushed {len(patches)} patches to <flood> ({flood_file})")

# -----------------------
# Auto TypeScript fix cycle
# -----------------------
def auto_ts_fix_cycle(
        repo_obj: Optional[Repo] = None,
        last_commit_time: float = 0.0,
        target_branch: str = "Orion",
        dev_style: bool = True
) -> tuple[List[dict], float]:

    applied_actions: List[dict] = []
    error_queue_file = PATCHES_DIR / "ts_errors.json"

    # Load TS errors
    try:
        errors = json.loads(error_queue_file.read_text(encoding="utf-8")) if error_queue_file.exists() else []
    except json.JSONDecodeError as e:
        log(f"⚠️ auto_ts_fix_cycle: reading TS errors failed: {repr(e)}")
        errors = []

    if not errors:
        log("ℹ️ auto_ts_fix_cycle: No TypeScript errors to fix")
        return applied_actions, last_commit_time

    for error in errors:
        handle_ts_error(error)

    prompt = f"Fix these TypeScript errors:\n{json.dumps(errors, indent=2)}"
    ts_actions: List[dict] = []
    try:
        ts_actions_raw = ask_llm(prompt)
        ts_actions = json.loads(ts_actions_raw)
    except Exception:
        ts_actions = []
        log("⚠️ auto_ts_fix_cycle: LLM returned invalid JSON")

    if ts_actions:
        apply_ts_actions(ts_actions)
        applied_actions.extend(ts_actions)

    # Git commit logic
    total_actions = len(ts_actions)
    now_ts = time.time()
    if repo_obj and total_actions > 0 and (now_ts - last_commit_time) >= 300:
        try:
            create_branch_if_missing(repo_obj, target_branch)
            repo_obj.git.checkout(target_branch)
            commit_all(repo_obj, f"Auto update - {total_actions} TS patches")
            last_commit_time = now_ts
        except Exception as e_repo:
            log(f"⚠️ auto_ts_fix_cycle: Git commit failed: {repr(e_repo)}")
    elif total_actions > 0:
        log(f"ℹ️ auto_ts_fix_cycle: Commit skipped (cooldown active)")

    # Archive patches
    try:
        archive_file = PATCHES_DIR / f"applied_{target_branch}_{int(time.time())}.json"
        archive_file.write_text(json.dumps(ts_actions, indent=2), encoding="utf-8")
        log(f"✅ Archived {len(ts_actions)} TS patches: {archive_file}")
    except Exception as e:
        log(f"⚠️ auto_ts_fix_cycle: Failed to archive patches: {repr(e)}")

    # Clear error queue
    try:
        error_queue_file.write_text("[]", encoding="utf-8")
    except Exception as e:
        log(f"⚠️ auto_ts_fix_cycle: Failed to clear TS error queue: {repr(e)}")

    return applied_actions, last_commit_time
