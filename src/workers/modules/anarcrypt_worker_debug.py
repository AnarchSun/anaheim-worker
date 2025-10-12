# PATH: src/workers/modules/anarcrypt_worker_debug.py
#!/usr/bin/env python3
import os
import sys

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))


# -----------------------
# Tracker / Mocks
# -----------------------
class MockCallTracker:
    """Capture tous les appels importants pour test full sequence"""
    def __init__(self):
        self.calls = []

tracker = MockCallTracker()

def repo_open():
    tracker.calls.append("repo_open")
    return {"name": "mock-repo"}

def log(msg, color=""):
    tracker.calls.append(("log", msg))
    print(f"{color}{msg}\033[0m")

def apply_ts_actions_stub(actions):
    tracker.calls.append(("apply_ts_actions", actions))
    print(f"[mock] apply_ts_actions({actions})")

def handle_ts_error_stub(err):
    tracker.calls.append(("handle_ts_error", err))
    print(f"[mock] handle_ts_error({err})")

def auto_ts_fix_cycle_safe_stub(repo, last_commit_time):
    tracker.calls.append(("auto_ts_fix_cycle_safe", repo, last_commit_time))
    return ["DebugPatch1"], last_commit_time + 1.0

def ask_llm_stub():
    tracker.calls.append("ask_llm_stub")
    return ""

def devtools_check_stub():
    tracker.calls.append("devtools_check_stub")
    print("[mock] devtools_check_stub() called")

# -----------------------
# Debug main
# -----------------------
def debug_main(dry_run=True):
    log("🛠️ Anaheim Worker DEBUG iteration started")

    repo = repo_open()
    if not repo:
        log("❌ Repo not available, aborting debug run.")
        return

    last_commit_times = {"Orion": 0.0, "Orion-Exploration": 0.0}

    ts_error_stub = {"file": "<unknown>", "type": "create_function", "symbol": "DebugStub"}
    apply_ts_actions_stub([ts_error_stub])
    log("✅ Stub TS action applied")

    for err in [ts_error_stub]:
        handle_ts_error_stub(err)
    log(f"✅ Handled 1 TS error")

    if dry_run:
        devtools_check_stub()
    else:
        log("💡 Real Playwright check skipped")

    for branch in ["Orion", "Orion-Exploration"]:
        applied_actions, last_commit_times[branch] = auto_ts_fix_cycle_safe_stub(
            repo,
            last_commit_time=last_commit_times[branch]
        )
        if applied_actions:
            log(f"🛠 {branch} applied {len(applied_actions)} actions.")

    log("🛑 DEBUG iteration finished")

# -----------------------
# Tests intégrés
# -----------------------
if __name__ == "__main__":
    debug_main(dry_run=True)
    print("\n=== Assertions test full sequence ===")
    assert "repo_open" in tracker.calls
    assert any(c[0]=="apply_ts_actions" for c in tracker.calls)
    assert any(c[0]=="handle_ts_error" for c in tracker.calls)
    assert any(c[0]=="auto_ts_fix_cycle_safe" for c in tracker.calls)
    assert any(c[0]=="log" and "DEBUG iteration finished" in c[1] for c in tracker.calls)
    print("✅ Full sequence checks passed")
