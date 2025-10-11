# PATH: hyper_worker_central.py
import os
import sys
import threading
from typing import Optional

from .anaheim_worker_safe import main_worker_safe
from .worker_dryrun import dryrun_main
from .worker_fastloop import fastloop_main
from ..common import log

# -----------------------
# Worker mode selector
# -----------------------
MODES = {
    "safe": main_worker_safe,
    "dryrun": dryrun_main,
    "fastloop": fastloop_main
}

def launch_worker(worker_func, name: Optional[str] = None):
    t = threading.Thread(target=worker_func, name=name or worker_func.__name__)
    t.start()
    log(f"🧵 Started {t.name}")
    return t

def launch_all(selected_modes=None):
    """
    selected_modes: list of mode strings, or None to launch all
    """
    threads = []

    if selected_modes is None:
        selected_modes = list(MODES.keys())

    for mode in selected_modes:
        func = MODES.get(mode)
        if func:
            threads.append(launch_worker(func, name=f"{mode}_worker"))
        else:
            log(f"⚠️ Unknown worker mode: {mode}")

    # Join all threads
    for t in threads:
        t.join()

if __name__ == "__main__":
    # Mode can be passed as CLI args or env var WORKER_MODE
    modes = os.getenv("WORKER_MODE")
    if len(sys.argv) > 1:
        modes = sys.argv[1:]
    elif modes:
        modes = modes.split(",")

    if modes:
        log(f"🚀 Launching selected modes: {modes}")
        launch_all(selected_modes=modes)
    else:
        log("🚀 Launching all workers")
        launch_all()
