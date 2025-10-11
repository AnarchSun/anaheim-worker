# common.py
import threading
import queue
import time

from auto_patch_worker import PROJECT_PATH

# file-global vars
llm_queue = queue.Queue()
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]  # remonte à anaheim-worker/
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# -----------------------
# Logging
# -----------------------
def log(msg: str):
    ts = time.strftime("%Y-%m-%d %H:%M:%S")
    line = f"[worker-safe][{ts}] {msg}"
    print(line)
    try:
        with open(PROJECT_PATH / "worker_safe.log", "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except OSError:
        pass
