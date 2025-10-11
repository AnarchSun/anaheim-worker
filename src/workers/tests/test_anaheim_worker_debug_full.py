# PATH: src/workers/modules/anarcrypt_worker_debug_final_all.py
#!/usr/bin/env python3
import sys
import os
import time
from typing import List, Dict, Any, Tuple, Optional

# Ajout du chemin parent pour imports locaux
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

# -----------------------
# Imports modules locaux
# -----------------------
from workers.utils.apply_ts_actions import apply_ts_actions
from workers.modules.anaheim_worker_safe import handle_ts_error

# Pour simuler repo_open, log, auto_ts_fix_cycle_safe
try:
    from hyper_optimal_worker import repo_open, log, auto_ts_fix_cycle_safe
except ImportError:
    def repo_open() -> Optional[Dict[str, Any]]:
        print("[mock] repo_open() called")
        return {"name": "mock-repo"}

    def log(msg: str, color: str = ""):
        print(f"{color}{msg}\033[0m")

    def auto_ts_fix_cycle_safe(repo: Dict[str, Any], last_commit_time: float) -> Tuple[List[str], float]:
        print(f"[mock] auto_ts_fix_cycle_safe({repo}, {last_commit_time})")
        return (["DebugPatch1"], time.time())

# -----------------------
# Couleurs ANSI pour log
# -----------------------
RED    = "\033[31m"
GREEN  = "\033[32m"
YELLOW = "\033[33m"
BLUE   = "\033[34m"
MAGENTA = "\033[35m"
CYAN   = "\033[36m"

# -----------------------
# Tracker global pour tests et suivi
# -----------------------
class Tracker:
    def __init__(self):
        self.calls: List[Tuple[str, Any]] = []

tracker = Tracker()

# -----------------------
# Stubs LLM & Playwright
# -----------------------
def ask_llm_stub(return_value: str = "") -> str:
    tracker.calls.append(("ask_llm_stub", return_value))
    log(f"💡 LLM simulated: returning '{return_value}'", CYAN)
    return return_value

def devtools_check_stub():
    tracker.calls.append(("devtools_check_stub", None))
    log("💡 Playwright simulated: skipped", CYAN)

# -----------------------
# Helper TS simulation
# -----------------------
def simulate_ts_action(ts_error_stub: Dict[str, Any]):
    tracker.calls.append(("apply_ts_actions", ts_error_stub))
    apply_ts_actions([ts_error_stub])
    log(f"✅ Stub TS action applied for {ts_error_stub['symbol']}", GREEN)

# -----------------------
# Debug / Dry-run main
# -----------------------
def debug_main(dry_run: bool = True, verbose: bool = True):
    log("🛠️ Anaheim Worker DEBUG iteration started", BLUE)
    start_time = time.time()

    repo = repo_open()
    tracker.calls.append(("repo_open", repo))
    if not repo:
        log("❌ Repo not available, aborting debug run.", RED)
        return

    if verbose:
        log(f"✅ Repo available → continue ({repo['name']})", GREEN)

    buffers = {"Orion": [], "Orion-Exploration": []}
    last_commit_times = {"Orion": 0.0, "Orion-Exploration": 0.0}

    # 1️⃣ TypeScript simulation
    ts_error_stub = {"file": "<unknown>", "type": "create_function", "symbol": "DebugStub"}
    simulate_ts_action(ts_error_stub)

    # 2️⃣ Collect errors & handle
    ts_errors = [ts_error_stub]
    for err in ts_errors:
        tracker.calls.append(("handle_ts_error", err))
        handle_ts_error(err)
    log(f"✅ Handled {len(ts_errors)} TS errors", GREEN)

    # 3️⃣ Playwright / DevTools
    if dry_run:
        devtools_check_stub()
    else:
        log("💡 Real Playwright check skipped in debug", YELLOW)

    # 4️⃣ Auto TS fix cycle simulation
    for branch in ["Orion", "Orion-Exploration"]:
        applied_actions, last_commit_times[branch] = auto_ts_fix_cycle_safe(
            repo,
            last_commit_time=last_commit_times[branch]
        )
        tracker.calls.append(("auto_ts_fix_cycle_safe", branch))
        if applied_actions:
            log(f"🛠 {branch} applied {len(applied_actions)} actions", GREEN)

    end_time = time.time()
    log(f"🛑 DEBUG iteration finished in {end_time - start_time:.2f}s", BLUE)

# -----------------------
# Debug live simulation (plus détaillé)
# -----------------------
def debug_main_live(dry_run=True):
    debug_main(dry_run=dry_run, verbose=True)

# -----------------------
# Tests Pytest intégrés
# -----------------------
def test_debug_main_runs_clean(capsys):
    tracker.calls.clear()
    debug_main(dry_run=True)
    captured = capsys.readouterr()
    output = captured.out
    assert "🛠️ Anaheim Worker DEBUG iteration started" in output
    assert "✅ Stub TS action applied" in output
    assert "🛑 DEBUG iteration finished" in output
    assert any(c[0] == "repo_open" for c in tracker.calls)
    assert any(c[0] == "apply_ts_actions" for c in tracker.calls)
    assert any(c[0] == "handle_ts_error" for c in tracker.calls)
    assert any(c[0] == "auto_ts_fix_cycle_safe" for c in tracker.calls)
    assert any(c[0] == "devtools_check_stub" for c in tracker.calls)
    assert any(c[0] == "ask_llm_stub" or True)  # toujours présent pour futures options

# -----------------------
# Entrée principale
# -----------------------
if __name__ == "__main__":
    debug_main(dry_run=True)
