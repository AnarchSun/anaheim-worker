# anarcrypt.sol/anaheim-worker/src/test_worker_start.py
import sys
from pathlib import Path

from workers.legacy.worker_full import CFG_PATH, REPO, GOV_PATH, DB_PATH, BRANCH, ensure_branch_exists, init_db

print("🛠️ Test Worker Start")

# 1️⃣ Vérifier la config
if not Path(CFG_PATH).exists():
    print(f"❌ Config non trouvée: {CFG_PATH}")
    sys.exit(1)
else:
    print(f"✅ Config trouvée: {CFG_PATH}")

# 2️⃣ Chemins principaux
print(f"📂 REPO_PATH={REPO} {'(existe)' if Path(REPO).exists() else '(manquant)'}")
print(f"📂 GOV_PATH={GOV_PATH} {'(existe)' if Path(GOV_PATH).exists() else '(manquant)'}")
print(f"📂 DB_PATH={DB_PATH}")

# 3️⃣ Init DB
try:
    init_db()
    print("✅ DB initialisée")
except Exception as e:
    print("❌ Erreur DB:", e)
    sys.exit(1)

# 4️⃣ Vérifier / créer branche Git
try:
    ensure_branch_exists()
    print(f"✅ Branche Git prête: {BRANCH}")
except Exception as e:
    print("❌ Erreur Git:", e)
    sys.exit(1)

print("🎯 Worker prêt pour main_loop()")
