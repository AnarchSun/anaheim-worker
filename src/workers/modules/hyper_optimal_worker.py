# PATH: src/workers/modules/hyper_worker_optimal.py

import os
import queue
import sqlite3
import threading
import time
from pathlib import Path
from typing import List, Optional, Union

from git import Repo, GitCommandError

# -----------------------
# Globals
# -----------------------
PROJECT_PATH = Path(os.getenv("REPO_PATH", "/home/anarchsun/RustroverProjects/anarcrypt.sol/anaheim-worker")).resolve()
DIAGNOSTICS_DIR = PROJECT_PATH / "diagnostics"
DIAGNOSTICS_DIR.mkdir(exist_ok=True)
COPILOT_DELEGATIONS_LOG = DIAGNOSTICS_DIR / "copilot_delegations.log"
FLOOD_BRANCH = "<flood>"

DB_PATH = PROJECT_PATH / "anarcrypt_worker.db"

llm_queue: queue.Queue[Union[str, dict]] = queue.Queue()
shutdown_event = threading.Event()
DRY_RUN = os.getenv("WORKER_DRY_RUN", "true").lower() == "true"

# -----------------------
# Logging
# -----------------------
def log(msg: str):
    ts = time.strftime("%Y-%m-%d %H:%M:%S")
    line = f"[hyper-worker][{ts}] {msg}"
    print(line)
    try:
        with open(PROJECT_PATH / "hyper_worker.log", "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except OSError:
        pass

def log_thread(msg: str):
    print(msg)

# -----------------------
# Repo helpers
# -----------------------
def repo_open() -> Optional[Repo]:
    try:
        return Repo(PROJECT_PATH)
    except Exception as e:
        log(f"❌ Failed to open repo: {repr(e)}")
        return None

def create_branch_if_missing(repo: Repo, branch_name: str):
    if branch_name not in repo.branches:
        repo.git.branch(branch_name)
        log(f"🌿 Created branch {branch_name}")

def commit_all(repo: Repo, message: str, action_buffer: Optional[List[dict]] = None, target_branch: str = ""):
    if DRY_RUN:
        log(f"💡 Dry-run enabled, skipping commit for {len(action_buffer) if action_buffer else 0} actions on branch {target_branch}")
        return
    try:
        repo.git.add(all=True)
        repo.index.commit(message)
        log(f"✅ Committed: {message}")
    except GitCommandError as e:
        log(f"⚠️ Commit failed: {repr(e)}")

def flush_to_flood(repo: Repo, branch_name: str):
    try:
        if FLOOD_BRANCH not in repo.branches:
            repo.git.branch(FLOOD_BRANCH)
        repo.git.checkout(FLOOD_BRANCH)
        try:
            repo.git.merge(branch_name, "--no-ff", "--strategy-option=theirs")
        except GitCommandError:
            repo.git.merge("--abort")
            log(f"⚠️ Merge conflict during flush_to_flood on {branch_name}")
            return
        commits = list(repo.iter_commits(FLOOD_BRANCH))
        if len(commits) > 250:
            repo.git.reset("--hard", commits[249].hexsha)
            log("♻️ FLOOD branch trimmed to 250 commits")
        if not DRY_RUN:
            repo.git.push("--set-upstream", "origin", FLOOD_BRANCH)
        log(f"🌊 FLOOD branch updated with {branch_name}")
    except Exception as e:
        log(f"💥 flush_to_flood failed: {repr(e)}")

# -----------------------
# Copilot / LLM
# -----------------------
def delegate_to_copilot(task: dict):
    if not task:
        return
    try:
        with open(COPILOT_DELEGATIONS_LOG, "a", encoding="utf-8") as f:
            f.write(f"Delegated task: {task}\n{'-'*60}\n")
        log(f"🤖 Task delegated to copilot: {task.get('file', 'unknown')}")
    except Exception as e:
        log(f"💥 delegate_to_copilot error: {repr(e)}")

def generate_copilot_fail_report(report: Optional[dict] = None) -> dict:
    if report is None:
        report = {"status": "failed", "errors": [], "timestamp": time.time()}
    log(f"📄 Copilot fail report generated: {report}")
    return report

def handle_shutdown():
    log("⚡ Shutdown initiated")
    shutdown_event.set()
    while not llm_queue.empty():
        llm_queue.get_nowait()
        llm_queue.task_done()

def init_db():
    try:
        DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("""
                  CREATE TABLE IF NOT EXISTS applied_actions (
                                                                 id INTEGER PRIMARY KEY AUTOINCREMENT,
                                                                 file TEXT,
                                                                 action_type TEXT,
                                                                 symbol TEXT,
                                                                 timestamp REAL
                  )
                  """)
        c.execute("""
                  CREATE TABLE IF NOT EXISTS llm_logs (
                                                          id INTEGER PRIMARY KEY AUTOINCREMENT,
                                                          prompt TEXT,
                                                          response TEXT,
                                                          timestamp REAL
                  )
                  """)
        conn.commit()
        conn.close()
        log(f"💾 Database initialized at {DB_PATH}")
    except Exception as e:
        log(f"💥 init_db error: {repr(e)}")

# -----------------------
# Patch / TS logic
# -----------------------
def apply_patch(patch: dict):
    file_path = Path(patch.get("file", ""))
    if not file_path.exists():
        log(f"❌ File not found: {file_path}")
        return False
    code = file_path.read_text(encoding="utf-8")
    ptype = patch.get("type")
    symbol = patch.get("symbol")
    extra = patch.get("extra", {})

    try:
        if ptype == "insert_import":
            if symbol not in code:
                code = f"import {{ {symbol} }} from '{extra.get('module', './{file_path.stem}')}';\n" + code
        elif ptype == "create_function":
            fn_args = extra.get("args", "...args: any[]")
            fn_body = extra.get("body", "throw new Error('Not implemented');")
            if symbol not in code:
                code += f"\nexport function {symbol}({fn_args}) {{ {fn_body} }}\n"
        elif ptype == "stub_variable":
            var_type = extra.get("type", "any")
            if symbol not in code:
                code += f"\nlet {symbol}: {var_type};\n"
        elif ptype == "replace_text":
            search_text = extra.get("search", "")
            replace_text = extra.get("replace", "")
            if search_text and search_text in code:
                code = code.replace(search_text, replace_text)
                log(f"🔧 Replaced '{search_text}' with '{replace_text}' in {file_path}")
        elif ptype == "append_code":
            snippet = extra.get("code", "")
            code += "\n" + snippet
        else:
            log(f"⚠️ Unknown patch type: {ptype}")
            return False
        file_path.write_text(code, encoding="utf-8")
        log(f"✅ Patch applied: {ptype} -> {file_path}")
        return True
    except Exception as e:
        log(f"💥 Failed to apply patch {ptype} on {file_path}: {repr(e)}")
        return False

def apply_ts_actions(actions: List[dict]):
    for patch in actions:
        apply_patch(patch)

# -----------------------
# Worker threads
# -----------------------
def worker_thread_cycle(task_source_queue: queue.Queue):
    while not shutdown_event.is_set():
        try:
            task = task_source_queue.get(timeout=2)
            if isinstance(task, dict):
                apply_ts_actions([task])
            task_source_queue.task_done()
        except queue.Empty:
            continue
        except Exception as e:
            log(f"💥 Worker error: {repr(e)}")

def copilot_retrier(interval: int = 120):
    while not shutdown_event.is_set():
        try:
            if not COPILOT_DELEGATIONS_LOG.exists():
                time.sleep(interval)
                continue
            content = COPILOT_DELEGATIONS_LOG.read_text(encoding="utf-8").strip()
            if not content:
                time.sleep(interval)
                continue
            entries = [b.strip() for b in content.split("-"*60) if b.strip()]
            for block in entries:
                ts_error = {"file": "<unknown>", "message": block[:80], "type": "create_function", "symbol": "LLMGenerated"}
                apply_ts_actions([ts_error])
            time.sleep(interval)
        except Exception as e:
            log(f"💥 copilot_retrier error: {repr(e)}")
            time.sleep(interval)

# -----------------------
# Auto TS fix
# -----------------------
def auto_ts_fix_cycle_safe(repo_obj: Optional[Repo],
                           last_commit_time: float,
                           min_commit_interval: int = 300,
                           target_branch: str = "Orion",
                           action_buffer: Optional[List[dict]] = None) -> tuple[List[dict], float]:
    """
    Version "safe" de auto_ts_fix_cycle, compatible avec hyper_worker.
    """
    applied_actions: List[dict] = []
    if action_buffer is None:
        action_buffer = []

    if not applied_actions:
        return applied_actions, last_commit_time

    action_buffer.extend(applied_actions)
    now_ts = time.time()
    if repo_obj and (now_ts - last_commit_time >= min_commit_interval) and action_buffer:
        try:
            create_branch_if_missing(repo_obj, target_branch)
            repo_obj.git.checkout(target_branch)
            commit_all(repo_obj, f"Auto TS update - {len(action_buffer)} actions",
                       action_buffer=action_buffer, target_branch=target_branch)
            flush_to_flood(repo_obj, target_branch)
            last_commit_time = now_ts
            action_buffer.clear()
        except Exception as e:
            log(f"⚠️ Commit failed: {repr(e)}")
    return applied_actions, last_commit_time

# -----------------------
# Main worker
# -----------------------
def main_worker_safe_hyper(num_threads: int = 4):
    repo_obj = repo_open()
    if not repo_obj:
        log("❌ Repo not available, exiting.")
        return
    # Pour simplifier, utilise auto_ts_fix_cycle_safe et worker_thread_cycle
    threads = [threading.Thread(target=worker_thread_cycle, args=(llm_queue,), daemon=True)
               for _ in range(num_threads)]
    for t in threads:
        t.start()
    retrier_thread = threading.Thread(target=copilot_retrier, daemon=True)
    retrier_thread.start()


def start_hot_reload():
    return None


def handle_ts_error():
    return None


def ask_llm():
    return None