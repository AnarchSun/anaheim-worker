# PATH: src/workers/tests/test_anarcrypt_worker_debug.py
import pytest
from workers.modules.anarcrypt_worker_debug import debug_main, tracker

# ---------- Fixtures ----------
@pytest.fixture(autouse=True)
def reset_tracker():
    tracker.calls.clear()
    yield
    tracker.calls.clear()

# ---------- Tests ----------
def test_debug_main_runs_clean(capsys):
    """Vérifie que le debug_main s'exécute sans erreurs et logs fin de debug."""
    debug_main(dry_run=True)
    captured = capsys.readouterr()
    output = captured.out

    assert "🛠️ Anaheim Worker DEBUG iteration started" in output
    assert "🛑 DEBUG iteration finished" in output

def test_debug_main_full_sequence():
    """Vérifie que toutes les étapes du debug_main sont appelées."""
    debug_main(dry_run=True)

    # 1️⃣ repo_open appelé
    assert "repo_open" in tracker.calls

    # 2️⃣ apply_ts_actions appelé
    assert any(c[0] == "apply_ts_actions" for c in tracker.calls)

    # 3️⃣ handle_ts_error appelé
    assert any(c[0] == "handle_ts_error" for c in tracker.calls)

    # 4️⃣ auto_ts_fix_cycle_safe appelé pour chaque branche
    assert any(c[0] == "auto_ts_fix_cycle_safe" for c in tracker.calls)

    # 5️⃣ DEBUG iteration finished log
    assert any(c[0] == "log" and "DEBUG iteration finished" in c[1] for c in tracker.calls)
