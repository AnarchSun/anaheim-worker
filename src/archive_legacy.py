#!/usr/bin/env python3
# archive_legacy.py
import os
from pathlib import Path
import shutil

BASE = Path(__file__).resolve().parent
WORKERS = BASE / "workers"
LEGACY = WORKERS / "legacy"
ARCHIVE = WORKERS / "archive_legacy"

if not LEGACY.exists():
    print("❌ Legacy folder not found.")
    exit(1)

ARCHIVE.mkdir(exist_ok=True)

for item in LEGACY.iterdir():
    dest = ARCHIVE / item.name
    print(f"📦 Moving {item} → {dest}")
    shutil.move(str(item), str(dest))

# Supprimer legacy vide
LEGACY.rmdir()
print("✅ Legacy archived to archive_legacy/. Repo cleaned.")
