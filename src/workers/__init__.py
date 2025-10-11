# anarcrypt.sol/anaheim-worker/src/__init__.py
"""
Auto-import all key worker functions
"""
import sys
from pathlib import Path
src_path = Path(__file__).parent.resolve()
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

try:
    from worker_full import (
        log, log_thread, apply_patch, apply_ts_actions,
        auto_ts_fix_cycle, ask_llm, delegate_to_copilot,
        handle_ts_error, generate_copilot_fail_report,
        worker_loop, handle_shutdown, repo_open, init_db
    )
except ImportError as e:
    raise ImportError(f"Failed to import from worker_full.py. Make sure {src_path} exists.") from e

__all__ = [
    "log", "log_thread", "apply_patch", "apply_ts_actions",
    "auto_ts_fix_cycle", "ask_llm", "delegate_to_copilot",
    "handle_ts_error", "generate_copilot_fail_report",
    "worker_loop", "handle_shutdown", "repo_open", "init_db"
]
