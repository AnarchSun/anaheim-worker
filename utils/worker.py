# ts_worker.py
from typing import List, Optional
from git import Repo

def auto_ts_fix_cycle(
        repo_obj: Optional[Repo] = None,
        last_commit_time: float = 0.0,
        min_commit_interval: int = 300,
        target_branch: str = "Orion"
) -> tuple[List[dict], float]:
    """
    Stub: returns empty patch list and keeps last commit timestamp.
    """
    return [], last_commit_time

def handle_ts_error(error_block: dict):
    """
    Stub: logs a TypeScript error block.
    """
    file_name = error_block.get("fileName", "<unknown>")
    msg = error_block.get("messageText", "???")
    print(f"TS Error: {file_name} -> {msg}")
