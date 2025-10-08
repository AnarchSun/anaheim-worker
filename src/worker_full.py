import hashlib
import json
import os
import subprocess
import time
import traceback
from pathlib import Path
from submodules_manager import update_submodules

import yaml
from git import Repo, InvalidGitRepositoryError, NoSuchPathError

from db import init_db, export_json, add_or_increment, get_fix
from git_utils import create_branch_if_missing, commit_all
from github_search import search_code
from playwright_runner import run_checks

# -----------------------
# Config paths - robust
# -----------------------
REPO_PATH_FALLBACK = "/home/anarchsun/RustroverProjects/anarcrypt.sol/anaheim-worker/anaheim-putsch-self-governance-solana-dapp"
CFG_PATH = os.path.join(os.environ.get("REPO_PATH", REPO_PATH_FALLBACK), "../config/worker_config.yml")

try:
    with open(CFG_PATH, "r") as _fh:
        cfg = yaml.safe_load(_fh)
except FileNotFoundError:
    raise FileNotFoundError(f"❌ Fichier de config introuvable : {CFG_PATH}")
except yaml.YAMLError as _yaml_err:
    raise RuntimeError(f"⚠️ Erreur YAML dans {CFG_PATH} : {_yaml_err}")

# Paths principaux
REPO = Path(os.getenv("REPO_PATH", cfg.get("repo_path", REPO_PATH_FALLBACK))).resolve()
PROJECT_PATH = REPO
DB_PATH = Path(os.getenv("DB_PATH", cfg.get("db_path", "/home/anarchsun/RustroverProjects/anarcrypt.sol/anaheim-worker/data/memory.sqlite"))).resolve()
BRANCH = os.getenv("WORKER_BRANCH", cfg.get("worker_branch", "Orion"))
ROOTS_THRESHOLD = cfg.get("roots_error_threshold", 6)
ORION_THRESHOLD_ERRORS = cfg.get("orion_threshold_errors", 999)
REPEAT_THRESHOLD = cfg.get("repeat_threshold", 2)
GOV_PATH = Path(os.getenv("GOV_PATH", cfg.get("gov_path", PROJECT_PATH.parent / "governance"))).resolve()

# Fallback si GOV_PATH inexistant
if not GOV_PATH.exists() and (PROJECT_PATH.parent / "governance").exists():
    GOV_PATH = (PROJECT_PATH.parent / "governance").resolve()
governance_dir = GOV_PATH

# Logs init
LOG_DIR = PROJECT_PATH.parent / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)
LOG_FILE = LOG_DIR / "anaheim_worker.log"

def log(msg):
    ts = time.strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line)
    with open(LOG_FILE, "a") as f:
        f.write(line + "\n")

log("🚀 Starting Anaheim Worker...")
log(f"📂 REPO_PATH={REPO} ({'exists' if REPO.exists() else 'missing'})")
log(f"📂 GOV_PATH={GOV_PATH} ({'exists' if governance_dir.exists() else 'missing'})")
log(f"📂 DB_PATH={DB_PATH}")
log(f"🌿 BRANCH={BRANCH}")
log(f"⚙️ ROOTS_THRESHOLD={ROOTS_THRESHOLD}")
log(f"🧠 ORION_THRESHOLD_ERRORS={ORION_THRESHOLD_ERRORS}")
log(f"🔁 REPEAT_THRESHOLD={REPEAT_THRESHOLD}")

init_db()

# -----------------------
# Repo open helper
# -----------------------
def repo_open():
    try:
        log(f"🔍 Opening repo at {PROJECT_PATH}")
        return Repo(PROJECT_PATH)
    except (InvalidGitRepositoryError, NoSuchPathError) as e:
        log(f"❌ Repo Git invalide: {e}")
        return None

# -----------------------
# Command runner
# -----------------------
def run_cmd(cmd, cwd=PROJECT_PATH, timeout=600):
    try:
        p = subprocess.run(cmd, cwd=cwd, shell=True, capture_output=True, text=True, timeout=timeout)
        return p.returncode, p.stdout + "\n" + p.stderr
    except Exception as ex:
        log(f"💥 Command failed: {cmd}\n{ex}")
        return -1, str(ex)

# -----------------------
# Error fingerprint
# -----------------------
def fingerprint_error(err):
    return hashlib.sha256(json.dumps(err, sort_keys=True).encode('utf-8')).hexdigest()

# -----------------------
# TypeScript / resolver
# -----------------------
def run_tsc(paths=None, timeout=120):
    paths = paths or [PROJECT_PATH]
    paths = [p for p in paths if p.exists()]
    combined_log = PROJECT_PATH / "ts-errors.log"
    with open(combined_log, "w") as f:
        for path in paths:
            subprocess.run(
                ["npx", "tsc", "--noEmit"],
                cwd=path,
                stdout=f,
                stderr=subprocess.STDOUT,
                check=False,
                timeout=timeout
            )
    return combined_log


def run_resolver(errors_file: Path):
    result = subprocess.run(["node", "src/utils/resolver/index.js", str(errors_file)],
                            cwd=PROJECT_PATH, capture_output=True, text=True, check=False)
    if result.stdout.strip():
        return json.loads(result.stdout)
    return []

def insert_import(_target_file, _symbol):
    """Stub: implémentation future"""
    pass  # placeholder


def create_function(_target_file, _symbol):
    """Stub: implémentation future"""
    pass  # placeholder


def patch_function_signature(_target_file, _function_name, _param, _type="any"):
    """Stub: implémentation future"""
    pass  # placeholder


def patch_type_annotation(_target_file, _symbol, _new_type):
    """Stub: implémentation future"""
    pass  # placeholder

def apply_ts_actions(actions):
    for act in actions:
        action = act.get("action")
        file_rel = act.get("file", "")
        if file_rel.startswith("governance/") and governance_dir.exists():
            _target_file = governance_dir / Path(file_rel).relative_to("governance")
        else:
            _target_file = PROJECT_PATH / file_rel

        try:
            if action == "add_import":
                insert_import(_target_file, act.get("symbol", "_"))
            elif action == "create_function":
                create_function(_target_file, act.get("symbol", "_"))
            elif action == "create_parameter":
                patch_function_signature(
                    _target_file,
                    act.get("function", "unknownFn"),
                    act.get("param", "arg"),
                    act.get("type", "any")
                )
            elif action == "change_type":
                patch_type_annotation(
                    _target_file,
                    act.get("symbol", "arg"),
                    act.get("newType", "any")
                )
            elif action == "suggest_package":
                subprocess.run(["pnpm", "add", act.get("package", "_")], cwd=PROJECT_PATH)
            else:
                log(f"ℹ️ Ignoré: {act}")
        except Exception as ex_local:
            log(f"⚠️ Erreur action TS: {act}\n{ex_local}")

# -----------------------
# LLM analysis
# -----------------------
def ask_llm(_prompt: str, _timeout: int = 90) -> str:
    """Stub temporaire: retourne string vide pour éviter NoneType"""
    return ""



def analyze_and_fix(errors):
    for single_error in errors:
        try:
            # fingerprint pour patch unique
            key = fingerprint_error(single_error)
            prev_fix = get_fix()
            if prev_fix:
                add_or_increment()
                continue

            prompt = f"Error:\n{json.dumps(single_error, indent=2)}\nProvide a patch or replacement with short explanation."
            llm_response = ask_llm(prompt)
            add_or_increment()

            patch_file = Path(os.path.join(os.path.dirname(DB_PATH), f"patches/patch_{key}.txt"))
            patch_file.parent.mkdir(parents=True, exist_ok=True)
            patch_file.write_text(llm_response)

            # Si patch mentionne deprecated ou replacement, faire recherche github
            error_msg = single_error.get("msg", "")
            if "deprecated" in llm_response.lower() or "replacement" in llm_response.lower():
                try:
                    hits = search_code(error_msg)
                    with patch_file.open("a", encoding="utf-8") as _fh_write:
                        for hit in hits[:10]:
                            _fh_write.write(f"{hit['repo']} {hit['path']} {hit['url']}\n")
                except Exception as _ex_search:
                    log(f"⚠️ Github search failed: {_ex_search}")

        except Exception as _ex_process:
            log(f"💥 Error processing single_error in analyze_and_fix: {_ex_process}\n{traceback.format_exc()}")


# -----------------------
# Strategy & commit
# -----------------------
def apply_strategy_and_commit(repo, errs):
    if repo is None:
        log("⚠️ Repo non disponible, commit skipped")
        return
    export_json()
    create_branch_if_missing(repo, BRANCH)
    repo.git.checkout(BRANCH)
    target_branch = "roots" if len(errs) <= ROOTS_THRESHOLD else BRANCH
    commit_all(repo, f"Auto update {time.strftime('%Y-%m-%d %H:%M:%S')} - errors:{len(errs)}")
    try:
        repo.git.push('--set-upstream', 'origin', target_branch)
    except Exception as ex:
        log(f"push failed: {ex}")

# -----------------------
# Playwright
# -----------------------
def devtools_check():
    pages = cfg.get("playwright", {}).get("pages", [])
    selectors = cfg.get("playwright", {}).get("click_selectors", [])
    try:
        run_checks(pages, selectors, out_path=os.path.join(os.path.dirname(DB_PATH), "dev_errors.json"))
    except Exception as ex:
        log(f"playwright failed: {ex}")

# -----------------------
# Collect errors
# -----------------------
def collect_errors() -> tuple[list, str]:
    """Stub temporaire pour éviter 'None' et unpack errors."""
    return [], ""

# -----------------------
# Main loop
# -----------------------
update_submodules(branch=BRANCH)

def main_loop():
    repo = repo_open()
    log("🛠️ Anaheim Worker main_loop started")
while True:
    try:
        paths_to_check = [PROJECT_PATH]
        if governance_dir.exists():
            paths_to_check.append(governance_dir)
        ts_errors_file = run_tsc(paths=paths_to_check)
        ts_actions = run_resolver(ts_errors_file)
        apply_ts_actions(ts_actions)
        errs, _ = collect_errors()
        analyze_and_fix(errs)
        # passe un timeout plus court si possible
        devtools_check()
        apply_strategy_and_commit(Repo, errs)
        export_json()
    except Exception as ex:
        log(f"💥 Worker loop crashed: {ex}\n{traceback.format_exc()}")

    # Sleep inside the loop
    log("⏱️ Sleeping 10 seconds before next run...")
    time.sleep(10)


if __name__ == "__main__":
    main_loop()


def ensure_branch_exists():
    return None