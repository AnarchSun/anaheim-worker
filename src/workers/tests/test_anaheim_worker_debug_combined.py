# PATH: src/workers/tests/test_anaheim_worker_debug_combined.py
import io
import sys
import pytest

# Import du debug_main dry-run
from workers.modules.anarcrypt_worker_debug import debug_main

# -----------------------
# Test simple : vérifie que debug_main démarre et se termine
# -----------------------
def test_debug_main_runs_clean(capsys):
    """Dry-run Anaheim Worker Debug — assure que debug_main s’exécute proprement."""
    debug_main(dry_run=True)
    captured = capsys.readouterr()
    output = captured.out

    assert "🛠️ Anaheim Worker DEBUG iteration started" in output
    assert "🛑 DEBUG iteration finished" in output

# -----------------------
# Test complet : vérifie le flux complet dry-run
# -----------------------
def test_debug_main_full_sequence(capsys):
    """
    Vérifie le flux complet de debug_main en dry-run,
    chaque étape clé doit apparaître dans les logs.
    """
    debug_main(dry_run=True)
    captured = capsys.readouterr()
    output = captured.out

    # Étapes clés du flux
    assert "🛠️ Anaheim Worker DEBUG iteration started" in output
    assert "✅ Stub TS action applied" in output
    assert "🔧 handle_ts_error" in output or "✅ Handled 1 TS errors" in output
    assert "💡 Playwright simulated: skipped" in output
    assert "🌿 auto_ts_fix_cycle_safe" in output
    assert "🛑 DEBUG iteration finished" in output
