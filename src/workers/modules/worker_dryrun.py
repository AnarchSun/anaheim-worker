#!/usr/bin/env python3
# worker_dryrun.py

import re
from pathlib import Path

from workers.modules import PROJECT_PATH
# -----------------------
# Remplacement des imports de worker_full
# -----------------------
from workers.modules.anaheim_worker_safe import (
    log,
    apply_ts_actions,
)

# Stub pour governance_dir
governance_dir = PROJECT_PATH / "governance"

# Stubs pour fonctions manquantes
def run_tsc(paths: list) -> Path:
    log(f"💡 run_tsc stub called on paths: {[str(p) for p in paths]}")
    return PROJECT_PATH / "ts_errors.json"

def run_resolver(ts_errors_file: Path) -> list:
    log(f"💡 run_resolver stub called on {ts_errors_file}")
    return []  # retourne actions vides

def collect_errors():
    log("💡 collect_errors stub called")
    return [], []  # (errors, metadata)

def analyze_and_fix(errors: list):
    log(f"💡 analyze_and_fix stub called for {len(errors)} errors")

def devtools_check():
    log("💡 devtools_check stub called")

def apply_strategy_and_commit(errors):
    log(f"💡 apply_strategy_and_commit stub called with {len(errors)} errors")

# -----------------------
# Patch helper
# -----------------------
def apply_patch(patch: dict) -> bool:
    file_path = Path(patch["file"])
    if not file_path.exists():
        log(f"❌ File not found for patch: {file_path}")
        return False

    code = file_path.read_text(encoding="utf-8")
    t = patch.get("type")

    if t == "insert_import":
        sym = patch["symbol"]
        if re.search(rf"import\s+.*\b{sym}\b", code):
            return False
        code = f"import {{ {sym} }} from './{file_path.stem}';\n" + code

    elif t == "create_function":
        sym = patch["symbol"]
        if re.search(rf"(function|export function)\s+{sym}\s*\(", code):
            return False
        code += f"\nexport function {sym}(...args: any[]) {{ throw new Error('Not implemented'); }}\n"

    elif t == "add_param":
        fn, p, pt = patch["function"], patch["param"], patch.get("paramType", "any")
        m = re.search(rf"(function\s+{fn}\s*\([^)]*)\)", code)
        if not m: return False
        code = code[:m.start()] + m.group(1) + f", {p}: {pt})" + code[m.end():]

    elif t == "change_type":
        sym, new_t = patch["symbol"], patch.get("newType", "any")
        code, n = re.subn(rf"(\b{sym}\s*:\s*)[A-Za-z0-9_\[\]|]+" , rf"\1{new_t}", code)
        if n == 0: return False

    file_path.write_text(code, encoding="utf-8")
    log(f"✅ Patch applied: {t} -> {file_path}")
    return True

# -----------------------
# Main DEBUG loop
# -----------------------
def debug_main(dry_run: bool = True):
    log("🛠️ Anaheim Worker DEBUG iteration started")

    # 1️⃣ TSC
    paths_to_check = [PROJECT_PATH]
    if governance_dir.exists():
        paths_to_check.append(governance_dir)
    ts_errors_file = run_tsc(paths=paths_to_check)
    log(f"✅ TSC completed. Errors file: {ts_errors_file}")

    # 2️⃣ Resolver TS
    ts_actions = run_resolver(ts_errors_file)
    log(f"✅ Resolver actions: {ts_actions}")
    apply_ts_actions(ts_actions)
    log("✅ Actions applied")

    # 3️⃣ Collect errors & LLM fix
    errs, _ = collect_errors()
    log(f"✅ Collected errors: {len(errs)}")
    analyze_and_fix(errs)
    log("✅ LLM analysis applied")

    # 4️⃣ Playwright / DevTools
    if dry_run:
        log("💡 Dry-run: skipping Playwright")
    else:
        devtools_check()
    log("✅ Playwright / DevTools check done")

    # 5️⃣ Commit & push strategy
    if dry_run:
        log("💡 Dry-run: commit & push skipped")
    else:
        apply_strategy_and_commit(errs)
        log("✅ Commit & push attempted")

    log("🛑 DEBUG iteration finished")

if __name__ == "__main__":
    debug_main(dry_run=True)
