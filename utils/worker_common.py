# src/utils/worker_common.py

import threading
import time
from git import Repo, GitCommandError
from pathlib import Path
from typing import Optional, List

shutdown_event = threading.Event()

def log(msg: str):
    """Simple timestamped log for all worker modules."""
    print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {msg}")

def repo_open(path: Optional[Path] = None) -> Optional[Repo]:
    """Try to open a git repo at the given path or CWD."""
    try:
        repo_path = path or Path.cwd()
        return Repo(repo_path)
    except Exception as e:
        log(f"❌ repo_open failed: {repr(e)}")
        return None

def create_branch_if_missing(repo: Repo, branch_name: str):
    if branch_name not in [b.name for b in repo.branches]:
        repo.git.branch(branch_name)
        log(f"🌱 Created missing branch {branch_name}")

def commit_all(repo: Repo, message: str):
    repo.git.add(A=True)
    repo.git.commit(m=message)
    log(f"💾 Commit done: {message}")
