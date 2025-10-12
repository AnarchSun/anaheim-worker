#!/usr/bin/env python3
import sqlite3
import pickle
from pathlib import Path
import subprocess

# Paths
PROJECT_PATH = Path("/home/anarchsun/RustroverProjects/anarcrypt.sol/anaheim-worker").resolve()
DB_PATH = PROJECT_PATH / "anarcrypt_worker.db"
LLM_QUEUE_PATH = PROJECT_PATH / "llm_queue_state.pkl"

print("\n🔹 Anaheim Worker Audit Summary 🔹\n")

# 1️⃣ Applied actions from DB
if DB_PATH.exists():
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        print("🗂️ Last 20 applied actions:")
        for row in c.execute("SELECT id, file, action_type, symbol, timestamp FROM applied_actions ORDER BY timestamp DESC LIMIT 20"):
            print(f"  [{row[0]}] {row[1]} | {row[2]} | {row[3]} | ts={row[4]}")
        conn.close()
    except Exception as e:
        print(f"💥 Error reading DB: {e}")
else:
    print("⚠️ Database not found.")

# 2️⃣ Pending tasks from queue
if LLM_QUEUE_PATH.exists():
    try:
        with LLM_QUEUE_PATH.open("rb") as f:
            tasks = pickle.load(f)
        print(f"\n⏳ Pending tasks ({len(tasks)}):")
        for t in tasks:
            print(f"  {t}")
    except Exception as e:
        print(f"💥 Error reading queue state: {e}")
else:
    print("\n⚠️ Queue state file not found.")

# 3️⃣ Uncommitted file changes
try:
    print("\n📝 Uncommitted file changes (git diff --name-status):")
    result = subprocess.run(["git", "diff", "--name-status"], cwd=PROJECT_PATH, capture_output=True, text=True)
    print(result.stdout.strip() or "  None")
except Exception as e:
    print(f"💥 Error running git diff: {e}")

print("\n🔹 End of Audit 🔹\n")
