#!/usr/bin/env python3
"""
Test suite for Anaheim Worker Debug runner.
Ensures the debug pipeline runs end-to-end without exceptions or circular imports.
"""

import io
import sys
import types
import pytest

# ----------------------------------------------------------------------------------
# 🔧 Mock missing dependencies (like hyper_optimal_worker) before importing the worker
# ----------------------------------------------------------------------------------
fake_mod = types.ModuleType("hyper_optimal_worker")

def fake_repo_open():
    print("[mock] repo_open() called")
    return {"repo": "mock"}

def fake_log(msg):
    print(f"[mock-log] {msg}")

def fake_auto_ts_fix_cycle_safe(repo, last_commit_time):
    print(f"[mock] auto_ts_fix_cycle_safe({repo}, {last_commit_time})")
    # Simulate return (actions, new_last_commit_time)
    return [{"mock_action": True}], last_commit_time + 1

fake_mod.repo_open = fake_repo_open
fake_mod.apply_ts_actions = lambda actions: print(f"[mock] apply_ts_actions({actions})")
fake_mod.log = fake_log
fake_mod.auto_ts_fix_cycle_safe = fake_auto_ts_fix_cycle_safe

sys.modules["hyper_optimal_worker"] = fake_mod  # ✅ register mock module

# Now safe to import the debug worker
from workers.modules.anarcrypt_worker_debug import debug_main


def test_debug_main_runs_clean(monkeypatch, capsys):
    """Dry-run Anaheim Worker Debug — ensures clean execution (exit code 0)."""

    # Capture log output
    log_output = io.StringIO()
    monkeypatch.setattr(sys, "stdout", log_output)

    # Run safely
    try:
        debug_main(dry_run=True)
    except Exception as e:
        pytest.fail(f"Debug main raised unexpected error: {e!r}")

    output = log_output.getvalue()
    assert "🛠️ Anaheim Worker DEBUG iteration started" in output
    assert "🛑 DEBUG iteration finished" in output
    assert "✅ Stub TS action applied" in output

    print("\n--- Debug Output ---")
    print(output)
    print("--------------------")
