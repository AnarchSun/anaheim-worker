"""
Patch file utility to replace deprecated datetime.now(timezone.utc)
with timezone-aware datetime.now(timezone.utc).
"""

import re
import traceback
from pathlib import Path

__version__ = "1.0.0"

def msg():
    """Returns a short identifier for logs."""
    return "fix_utc_deprecated"


def patch_file(file_path: Path) -> bool:
    """
    Scan a Python file and replace all occurrences of datetime.now(timezone.utc)
    with datetime.now(timezone.utc), respecting formatting.
    """
    try:
        if not file_path.exists() or not file_path.suffix == ".py":
            return False

        text = file_path.read_text(encoding="utf-8")
        new_text, count = re.subn(
            r"datetime\.utcnow\s*\(\s*\)",
            "datetime.now(timezone.utc)",
            text,
        )

        if count > 0:
            file_path.write_text(new_text, encoding="utf-8")
            print(f"🩹 Patched {count} utcnow() in {file_path}")
            return True

        return False

    except Exception as e:
        print(f"⚠️ Error patching {file_path}: {repr(e)}\n{traceback.format_exc()}")
        return False


def fix_utc_deprecated():
    """CLI-like entry to patch all Python files in the repo root."""
    repo_root = Path(__file__).resolve().parents[1]
    patched_files = 0
    for py_file in repo_root.rglob("*.py"):
        if patch_file(py_file):
            patched_files += 1
    print(f"✅ Finished patching {patched_files} files.")
    return patched_files


if __name__ == "__main__":
    fix_utc_deprecated()
