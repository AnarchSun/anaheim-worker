#!/usr/bin/env python3
import re
import shutil
from pathlib import Path

BASE = Path(__file__).resolve().parent
MODULES_DIR = BASE / "modules"
LEGACY_DIR = BASE / "legacy"
LEGACY_DIR.mkdir(exist_ok=True)

PRIMARY_WORKERS = {
    "safe": MODULES_DIR / "anaheim_worker_safe.py",
    "fastloop": MODULES_DIR / "worker_fastloop.py",
    "dryrun": MODULES_DIR / "worker_dryrun.py",
}

def backup_old_workers():
    for f in MODULES_DIR.glob("*.py"):
        if f.name not in [p.name for p in PRIMARY_WORKERS.values()] and f.name != "__init__.py":
            dest = LEGACY_DIR / f.name
            print(f"📦 Archiving {f.name} → {dest}")
            shutil.copy(f, dest)
            f.unlink()

def merge_unique_functions(src_file, dest_file):
    src_text = src_file.read_text(encoding="utf-8")
    dest_text = dest_file.read_text(encoding="utf-8")

    src_funcs = re.findall(r"^def\s+(\w+)", src_text, re.MULTILINE)
    dest_funcs = re.findall(r"^def\s+(\w+)", dest_text, re.MULTILINE)

    new_funcs = [f for f in src_funcs if f not in dest_funcs]
    if not new_funcs:
        return

    print(f"🔧 Merging {len(new_funcs)} new functions from {src_file.name} → {dest_file.name}")
    with open(dest_file, "a", encoding="utf-8") as f:
        f.write("\n\n# ---- merged from " + src_file.name + " ----\n")
        for match in re.finditer(r"^def\s+\w+[\s\S]*?(?=\n^def\s|\Z)", src_text, re.MULTILINE):
            func_block = match.group(0)
            func_name = re.match(r"^def\s+(\w+)", func_block).group(1)
            if func_name in new_funcs:
                f.write(func_block + "\n\n")

def merge_all():
    print("🚀 Starting worker merge...")
    backup_old_workers()

    legacy_files = list(LEGACY_DIR.glob("*.py"))
    for lf in legacy_files:
        if "safe" in lf.name or "super" in lf.name or "orchestrator" in lf.name:
            merge_unique_functions(lf, PRIMARY_WORKERS["safe"])
        elif "fast" in lf.name or "hot_reload" in lf.name:
            merge_unique_functions(lf, PRIMARY_WORKERS["fastloop"])
        elif "dry" in lf.name or "debug" in lf.name or "patcher" in lf.name:
            merge_unique_functions(lf, PRIMARY_WORKERS["dryrun"])

    print("✅ Merge complete. Legacy workers archived in /legacy")

if __name__ == "__main__":
    merge_all()
