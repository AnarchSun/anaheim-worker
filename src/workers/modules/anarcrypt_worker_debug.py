# PATH: src/workers/modules/anarcrypt_worker_debug.py
#!/usr/bin/env python3
import sys, os
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from workers.utils.apply_ts_actions import apply_ts_actions

# Imports depuis modules centralisés
from hyper_optimal_worker import (
    repo_open,
    apply_ts_actions,
    log,
    auto_ts_fix_cycle_safe,
)
from workers.modules.anaheim_worker_safe import handle_ts_error
# -----------------------
# Stubs LLM & Playwright
# -----------------------
def ask_llm_stub() -> str:
    log("💡 LLM simulated: returning empty string")
    return ""

def devtools_check_stub():
    log("💡 Playwright simulated: skipped")

def test_debug_main_runs_clean(capsys):
    debug_main(dry_run=True)
    captured = capsys.readouterr()
    assert "🛑 DEBUG iteration finished" in captured.out

# -----------------------
# Debug / Dry-run main
# -----------------------
def debug_main(dry_run: bool = True):
    log("🛠️ Anaheim Worker DEBUG iteration started")
    repo = repo_open()
    if not repo:
        log("❌ Repo not available, aborting debug run.")
        return

    buffers = {"Orion": [], "Orion-Exploration": []}
    last_commit_times = {"Orion": 0.0, "Orion-Exploration": 0.0}

    # 1️⃣ TypeScript simulation
    ts_error_stub = {"file": "<unknown>", "type": "create_function", "symbol": "DebugStub"}
    apply_ts_actions([ts_error_stub])
    log("✅ Stub TS action applied")

    # 2️⃣ Collect errors & LLM analysis
    ts_errors = [ts_error_stub]
    for err in ts_errors:
        handle_ts_error(err)
    log(f"✅ Handled {len(ts_errors)} TS errors")

    # 3️⃣ Playwright / DevTools
    if dry_run:
        devtools_check_stub()
    else:
        log("💡 Real Playwright check skipped in debug")

    # 4️⃣ Auto TS fix cycle simulation
    for branch in ["Orion", "Orion-Exploration"]:
        applied_actions, last_commit_times[branch] = auto_ts_fix_cycle_safe(
            repo,
            last_commit_time=last_commit_times[branch]
        )
        if applied_actions:
            log(f"🛠 {branch} applied {len(applied_actions)} actions.")

    # Ligne finale pour le test
    print("🛑 DEBUG iteration finished")

# -----------------------
# Entry point
# -----------------------
if __name__ == "__main__":
    debug_main(dry_run=True)
