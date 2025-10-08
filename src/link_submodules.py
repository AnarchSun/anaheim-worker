import subprocess
import logging
from pathlib import Path
import sys

# --- Configuration du logger ---
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)

REPOS = {
    "governance": "../governance",
    "candy-machine": "../candy-machine",
    "putsch": "../anaheim-putsch-self-governance-solana-dapp",
}

def run(cmd, repo_path, check=False, capture=False):
    """Exécute une commande git dans un repo donné"""
    full_cmd = ["git", "-C", str(repo_path)] + cmd
    if capture:
        return subprocess.run(full_cmd, capture_output=True, text=True)
    else:
        subprocess.run(full_cmd, check=check)

def update_and_link(branch="Orion", force_all=False):
    for name, path in REPOS.items():
        repo_path = Path(__file__).resolve().parent / path
        logging.info(f"🔗 Linking submodule: {name} -> {repo_path}")

        if not repo_path.exists():
            logging.warning(f"⚠️ Repo path missing: {repo_path}")
            continue

        # Fetch origin
        run(["fetch", "origin"], repo_path)

        # Vérifie si la branche existe
        local = run(["branch", "--list", branch], repo_path, capture=True)
        remote = run(["ls-remote", "--heads", "origin", branch], repo_path, capture=True)
        branch_exists = local.stdout.strip() or remote.stdout.strip()

        # Si la branche n'existe pas
        if not branch_exists:
            logging.warning(f"🌱 Creating new branch '{branch}' in {name}")
            run(["checkout", "-b", branch], repo_path)
            run(["push", "--set-upstream", "origin", branch], repo_path)
        else:
            if force_all:
                logging.warning(f"⚠️ FORCE MODE: resetting {name} to origin/{branch}")
                run(["checkout", branch], repo_path)
                run(["fetch", "origin"], repo_path)
                run(["reset", "--hard", f"origin/{branch}"], repo_path)
            else:
                # Stash si changements locaux
                status = run(["status", "--porcelain"], repo_path, capture=True)
                if status.stdout.strip():
                    logging.info(f"💾 Stashing local changes in {name}")
                    run(["stash", "-u"], repo_path)

                # Checkout et pull
                run(["checkout", branch], repo_path)
                run(["pull", "--rebase"], repo_path)

        logging.info(f"✅ {name} synced on branch '{branch}'.\n")

    logging.info("🎯 All submodules linked and up to date.")

if __name__ == "__main__":
    # Mode force
    force_all = "--force-all" in sys.argv
    update_and_link(force_all=force_all)
