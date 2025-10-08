# anarcrypt.sol/anaheim-worker/src/worker.py
import hashlib
import json
import os
import subprocess
import time

import yaml

# -----------------------
# Local modules
# -----------------------
from db import init_db, add_or_increment, get_fix, export_json
from git_utils import repo_open, create_branch_if_missing, commit_all
from github_search import search_code
from llm_interface import ask_llm
from parser_utils import parse_tsc, parse_eslint_json, parse_cargo
from playwright_runner import run_checks
from ts_worker import run_tsc, run_resolver, apply_actions  # TypeScript resolver

# -----------------------
# Config
# -----------------------
CFG_PATH = "config/worker_config.yml"
cfg = yaml.safe_load(open(CFG_PATH))

REPO = os.getenv("REPO_PATH", cfg.get("repo_path","/work/project"))
BRANCH = os.getenv("WORKER_BRANCH", cfg.get("worker_branch","Orion"))
REPEAT_THRESHOLD = cfg.get("repeat_threshold",2)
ROOTS_THRESHOLD = cfg.get("roots_error_threshold",6)

# -----------------------
# Init DB
# -----------------------
init_db()

# -----------------------
# Helpers
# -----------------------
def run_cmd(cmd, cwd=REPO, timeout=600):
    try:
        p = subprocess.run(cmd, cwd=cwd, shell=True, capture_output=True, text=True, timeout=timeout)
        return p.returncode, p.stdout + "\n" + p.stderr
    except Exception as e:
        return -1, str(e)

def fingerprint_error(err):
    return hashlib.sha256(json.dumps(err, sort_keys=True).encode('utf-8')).hexdigest()

# -----------------------
# Analyze and fix
# -----------------------
def analyze_and_fix(errors):
    for e in errors:
        key = fingerprint_error(e)
        prev = get_fix()
        if prev:
            add_or_increment()
            print("Found cached fix, skipping LLM")
            continue

        # Ask LLM for patch
        prompt = f"Error:\n{json.dumps(e, indent=2)}\nFile content (if available): Provide a minimal patch or full file replacement and short explanation. If deprecated, suggest replacements and possible GitHub examples."
        resp = ask_llm(prompt, timeout=90)
        add_or_increment()

        if "deprecated" in resp.lower() or "replacement" in resp.lower():
            term = e.get("msg","")
            try:
                hits = search_code(term)
                with open(f"/work/data/patches/patch_{key}.txt","w",encoding="utf-8") as f:
                    f.write(resp+"\n\n# GH candidates:\n")
                    for h in hits[:10]:
                        f.write(f"{h['repo']} {h['path']} {h['url']}\n")
            except Exception as ex:
                print("Github search failed", ex)
        else:
            with open(f"/work/data/patches/patch_{key}.txt","w",encoding="utf-8") as f:
                f.write(resp)

# -----------------------
# Collect errors
# -----------------------
def collect_errors():
    # 1️⃣ TypeScript resolver
    ts_errors_file = run_tsc()
    ts_actions = run_resolver(ts_errors_file)
    if ts_actions:
        apply_actions(ts_actions)

    # 2️⃣ pnpm / eslint / cargo
    rc, out = run_cmd("pnpm build || pnpm run build || true")
    tsc = parse_tsc(out)
    rc2, lint_out = run_cmd("pnpm lint -f json || true")
    eslint = parse_eslint_json(lint_out)
    rc3, cargo_out = run_cmd("cargo build || true")
    cargo = parse_cargo(cargo_out)

    errs = tsc + eslint + cargo
    return errs, out + "\n" + lint_out + "\n" + cargo_out

# -----------------------
# Commit / push strategy
# -----------------------
def apply_strategy_and_commit(repo, errs):
    export_json()
    create_branch_if_missing(repo, BRANCH)
    repo.git.checkout(BRANCH)

    target_branch = BRANCH
    if len(errs) <= ROOTS_THRESHOLD:
        target_branch = "Roots"

    ts = time.strftime("%Y-%m-%d %H:%M:%S")
    summary = f"Auto update {ts} - errors:{len(errs)}"
    commit_all(repo, summary)
    try:
        repo.git.push('--set-upstream','origin', target_branch)
    except Exception as e:
        print("Push failed:", e)

# -----------------------
# Devtools checks
# -----------------------
def devtools_check():
    pages = cfg.get("playwright", {}).get("pages", [])
    selectors = cfg.get("playwright", {}).get("click_selectors", [])
    try:
        run_checks(pages, selectors, out_path="/work/data/dev_errors.json")
    except Exception as e:
        print("Playwright failed:", e)

# -----------------------
# Main loop
# -----------------------
def main_loop():
    repo = repo_open()
    while True:
        errs, raw = collect_errors()
        print(f"Found {len(errs)} errors")

        to_handle = []
        for e in errs:
            _key = fingerprint_error(e)
            to_handle.append(e)

        if to_handle:
            analyze_and_fix(to_handle)

        devtools_check()
        apply_strategy_and_commit(repo, errs)
        export_json()
        time.sleep(300)

if __name__=="__main__":
    main_loop()
