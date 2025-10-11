#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Patch automatique : remplace tous les datetime.utcnow() dépréciés
par datetime.now(timezone.utc), compatible Python 3.12+
"""

import os
import re
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]  # remonte au dossier principal
TARGET_EXTENSIONS = (".py",)
RE_PATTERN = re.compile(r"\bdatetime\.utcnow\s*\(\s*\)")

def patch_file(path: Path):
    text = path.read_text(encoding="utf-8")
    if "datetime.utcnow" not in text:
        return False

    # assure que timezone est importé
    if "from datetime import timezone" not in text:
        if "from datetime import datetime" in text:
            text = text.replace("from datetime import datetime", "from datetime import datetime, timezone")
        else:
            text = "from datetime import timezone\n" + text

    patched = RE_PATTERN.sub("datetime.now(timezone.utc)", text)
    if patched != text:
        path.write_text(patched, encoding="utf-8")
        print(f"✅ Patched {path}")
        return True
    return False

def main():
    count = 0
    for root, _, files in os.walk(PROJECT_ROOT):
        for file in files:
            if file.endswith(TARGET_EXTENSIONS):
                fpath = Path(root) / file
                if patch_file(fpath):
                    count += 1
    print(f"\n✨ Total fichiers corrigés : {count}")

if __name__ == "__main__":
    main()
