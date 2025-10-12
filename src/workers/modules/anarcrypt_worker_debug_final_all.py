# PATH: src/workers/modules/anarcrypt_worker_debug_final_all.py
#!/usr/bin/env python3
import sys, os, time

# -----------------------
# Tracker global pour tests
# -----------------------
class CallTracker:
    def __init__(self):
        self.calls = []

tracker = CallTracker()

# -----------------------
# Helpers & logging
# -----------------------
def log(msg: str, color: str = "\033[0m"):
    """Print colored log for terminal."""
    print(f"{color}{msg}\033[0m")

RED    = "\033[31m"
GREEN  = "\033[32m"
YELLOW = "\033[33m"
BLUE   = "\033[34m"
MAGENTA = "\033[35m"
CYAN   = "\033[36m"

# -----------------------
# Stubs LLM & Playwright
# -----------------------
def ask_llm_stub() -> str:
    tracker.calls.append(("ask_llm_stub",))
    log("💡 LLM simulated: returning empty string")
    return ""

def devtools_check_stub():
    tracker.calls.append(("devtools_check_stub",))
    log("💡 Playwright simulated: skipped")

# -----------------------
# Module centralisé stubs
# -----------------------
def repo_open():
    tracker.calls.append(("repo_open",))
    log("📦 repo_open() called", CYAN)
    return {"name": "mock-repo"}

def apply_ts_actions(actions):
    tracker.calls.append(("apply_ts_actions", actions))
    log(f"⚡ apply_ts_actions({actions})", MAGENTA)

def handle_ts_error(err):
    tracker.calls.append(("handle_ts_error", err))
    log(f"[worker-safe] TS error handled: {err}", GREEN)

def auto_ts_fix_cycle_safe(repo, last_commit_time=0.0):
    tracker.calls.append(("auto_ts_fix_cycle_safe", repo))
    applied_actions = ["DebugPatch1"]
    log(f"🌿 auto_ts_fix_cycle_safe called on repo {repo}", MAGENTA)
    return applied_actions, time.time()

# -----------------------
# Debug / Dry-run main
# -----------------------
def debug_main(dry_run: bool = True):
    log("🛠️ Anaheim Worker DEBUG iteration started", BLUE)

    # Repo open
    repo = repo_open()
    if not repo:
        log("❌ Repo not available, aborting debug run.", RED)
        return

    buffers = {"Orion": [], "Orion-Exploration": []}
    last_commit_times = {"Orion": 0.0, "Orion-Exploration": 0.0}

    # 1️⃣ TypeScript simulation
    ts_error_stub = {"file": "<unknown>", "type": "create_function", "symbol": "DebugStub"}
    apply_ts_actions([ts_error_stub])
    log("✅ Stub TS action applied", GREEN)

    # 2️⃣ Collect errors & LLM analysis
    ts_errors = [ts_error_stub]
    for err in ts_errors:
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
        if applied_actions:
            log(f"🛠 {branch} applied {len(applied_actions)} actions.", GREEN)

    # 5️⃣ Stub LLM call for future options
    ask_llm_stub()

    log("🛑 DEBUG iteration finished", BLUE)

# -----------------------
# Test intégré pour pytest
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
    assert any(c[0] == "ask_llm_stub" for c in tracker.calls)

# -----------------------
# Mode live
# -----------------------
def debug_main_live(dry_run=True):
    debug_main(dry_run=dry_run)

# -----------------------
# Entry point
# -----------------------
if __name__ == "__main__":
    debug_main(dry_run=True)
