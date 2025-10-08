# anarcrypt.sol/anaheim-worker/src/submodules_manager.py
import subprocess
from pathlib import Path
from datetime import datetime

REPOS = {
    "governance": "../governance",
    "candy-machine": "../candy-machine",
    "putsch": "../anaheim-putsch-self-governance-solana-dapp",
}

def log(msg: str):
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [SUBMODULE] {msg}")

def update_submodules(branch: str = "Orion"):
    log(f"🔗 Syncing submodules for branch: {branch}")
    for name, path in REPOS.items():
        repo_path = Path(__file__).resolve().parent / path
        if not repo_path.exists():
            log(f"⚠️ Repo {name} not found at {repo_path}")
            continue
        try:
            subprocess.run(["git", "-C", str(repo_path), "fetch", "origin"], check=False)
            subprocess.run(["git", "-C", str(repo_path), "checkout", branch], check=False)
            subprocess.run(["git", "-C", str(repo_path), "pull"], check=False)
            log(f"✅ {name} synced successfully.")
        except Exception as e:
            log(f"💥 Error syncing {name}: {e}")
    log("✨ Submodule sync complete.")
