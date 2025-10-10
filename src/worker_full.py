import hashlib
import json
import os
import queue
import signal
import subprocess
import threading
import time
import traceback
from pathlib import Path
from types import FrameType

import yaml
from git import Repo, InvalidGitRepositoryError, NoSuchPathError
from openai import OpenAI, RateLimitError, OpenAIError
from playwright.sync_api import sync_playwright
from db import init_db, add_or_increment, get_fix
from git_utils import create_branch_if_missing, commit_all
from openai.types.chat import (
    ChatCompletionSystemMessageParam,
    ChatCompletionUserMessageParam,
)

# -----------------------
# Config paths
# -----------------------
REPO_PATH_FALLBACK = "/home/anarchsun/RustroverProjects/anarcrypt.sol/anaheim-worker/anaheim-putsch-self-governance-solana-dapp"
CFG_PATH = os.path.join(os.environ.get("REPO_PATH", REPO_PATH_FALLBACK), "../config/worker_config.yml")

def load_config(cfg_path):
    try:
        with open(cfg_path, "r") as f:
            return yaml.safe_load(f)
    except FileNotFoundError:
        raise FileNotFoundError(f"❌ Config missing: {cfg_path}")
    except yaml.YAMLError as e:
        raise RuntimeError(f"⚠️ YAML error in {cfg_path}: {e}")

cfg = load_config(CFG_PATH)

def resolve_path(env_key, cfg_key, fallback):
    return Path(os.getenv(env_key, cfg.get(cfg_key, fallback))).resolve()

REPO = resolve_path("REPO_PATH", "repo_path", REPO_PATH_FALLBACK)
PROJECT_PATH = REPO
DB_PATH = resolve_path("DB_PATH", "db_path", "/home/anarchsun/.../memory.sqlite")
BRANCH = os.getenv("WORKER_BRANCH", cfg.get("worker_branch", "Orion"))
ROOTS_THRESHOLD = cfg.get("roots_error_threshold", 6)
GOV_PATH = resolve_path("GOV_PATH", "gov_path", PROJECT_PATH.parent / "governance")
if not GOV_PATH.exists() and (PROJECT_PATH.parent / "governance").exists():
    GOV_PATH = (PROJECT_PATH.parent / "governance").resolve()
governance_dir = GOV_PATH

LOG_DIR = PROJECT_PATH.parent / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)
LOG_FILE = LOG_DIR / "anaheim_worker.log"

# -----------------------
# Logging
# -----------------------
def log(msg: str):
    ts = time.strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line)
    try:
        with open(LOG_FILE, "a") as f:
            f.write(line + "\n")
    except OSError as e:
        print(f"⚠️ Log write failed: {e}")

def log_thread(msg: str, url: str | None = None):
    thread_name = threading.current_thread().name
    prefix = f"[{thread_name}]"
    if url:
        prefix += f"[{url}]"
    log(f"{prefix} {msg}")

# -----------------------
# Init DB & Repo
# -----------------------
init_db()

def repo_open() -> Repo | None:
    try:
        log(f"🔍 Opening repo at {PROJECT_PATH}")
        return Repo(PROJECT_PATH)
    except (InvalidGitRepositoryError, NoSuchPathError) as ex:
        log(f"❌ Invalid repo: {ex}")
        return None

# -----------------------
# TypeScript helpers
# -----------------------
def run_tsc(paths: list[Path] | None = None, timeout: int = 120) -> Path:
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
                timeout=timeout,
            )
    return combined_log

def run_resolver(errors_file: Path) -> list[dict]:
    result = subprocess.run(
        ["node", "src/utils/resolver/index.js", str(errors_file)],
        cwd=PROJECT_PATH,
        capture_output=True,
        text=True,
        check=False
    )
    if result.stdout.strip():
        return json.loads(result.stdout)
    return []

# -----------------------
# TypeScript patch helpers (stubs)
# -----------------------
def insert_import(target_file: Path, symbol: str, module: str):
    log(f"📝 insert_import called on {target_file} with symbol={symbol}, module={module}")

def create_function(target_file: Path, function_name: str):
    log(f"📝 create_function called on {target_file}, function={function_name}")

def patch_function_signature(target_file: Path, function_name: str, param_name: str, param_type: str):
    log(f"📝 patch_function_signature called on {target_file}, function={function_name}, param={param_name}:{param_type}")

def patch_type_annotation(target_file: Path, symbol: str, new_type: str):
    log(f"📝 patch_type_annotation called on {target_file}, symbol={symbol}, new_type={new_type}")

def patch_contextual_insert(target_path: Path, snippet: str, insert_after=None, line: int | None = None, context_snippet: str | None = None):
    try:
        content = target_path.read_text().splitlines()
        insert_index: int | None = None
        if line and 0 <= line-1 < len(content):
            insert_index = line-1
        elif context_snippet:
            for i, l in enumerate(content):
                if context_snippet.strip() in l:
                    insert_index = i+1
                    break
        elif insert_after:
            for i, l in enumerate(content):
                if insert_after.strip() in l:
                    insert_index = i+1
                    break
        if insert_index is None:
            content.append(snippet)
        else:
            content.insert(insert_index, snippet)
        target_path.write_text("\n".join(content))
        log(f"✨ Inserted snippet into {target_path} at line {insert_index or 'EOF'}")
    except Exception as ex:
        log(f"⚠️ patch_contextual_insert failed on {target_path}: {repr(ex)}")

# -----------------------
# Unified LLM queue
# -----------------------
llm_queue: queue.Queue = queue.Queue()
_API_KEY = os.getenv("OPENAI_API_KEY")
_client: OpenAI | None = OpenAI(api_key=_API_KEY) if _API_KEY else None

def ask_llm(prompt: str) -> str:
    """
    Query GPT-4o-mini safely with retries, JSON parsing, and logging.
    Returns a JSON string or "[]" if all attempts fail.
    """

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        log("❌ No OPENAI_API_KEY found. Skipping LLM call.")
        return "[]"

    client = OpenAI(api_key=api_key)

    messages = [
        ChatCompletionSystemMessageParam(
            role="system",
            content=(
                "You are an autonomous TypeScript repair assistant. "
                "Return ONLY a valid JSON array of patch actions, no prose, no markdown. "
                "Each action must specify: action, file, and required parameters."
            )
        ),
        ChatCompletionUserMessageParam(
            role="user",
            content=prompt.strip()
        )
    ]

    for attempt in range(3):
        try:
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=messages,
                temperature=0.2,
                max_tokens=800,
            )

            raw = (response.choices[0].message.content or "").strip()
            log(f"🤖 Raw LLM response (len={len(raw)}): {raw[:180]}{'...' if len(raw) > 180 else ''}")

            try:
                parsed = json.loads(raw)
                if isinstance(parsed, list):
                    return json.dumps(parsed, indent=2)
                else:
                    log(f"⚠️ Expected JSON list, got {type(parsed).__name__} instead.")
            except json.JSONDecodeError as e:
                log(f"⚠️ Malformed JSON (attempt {attempt+1}): {repr(e)}")

            time.sleep(1.5)

        except RateLimitError as rl:
            log(f"⏳ RateLimit (attempt {attempt+1}): {repr(rl)}")
            time.sleep(2 ** attempt + 0.5)  # jitter minimal
        except OpenAIError as oe:
            log(f"⚠️ OpenAI error (attempt {attempt+1}): {repr(oe)}")
            time.sleep(1.5)
        except Exception as ex_outer:
            log(f"💥 ask_llm exception (attempt {attempt+1}): {repr(ex_outer)}\n{traceback.format_exc()}")
            time.sleep(1.5)

    log("🚫 All retries failed. Returning empty patch list.")
    return "[]"

def analyze_and_fix(errors: list[dict]):
    for err_obj in errors:
        try:
            key = hashlib.sha256(json.dumps(err_obj, sort_keys=True).encode()).hexdigest()
            prev_fix = get_fix()
            if prev_fix:
                add_or_increment()
                continue
            prompt = f"Error:\n{json.dumps(err_obj, indent=2)}\nProvide a patch with a short explanation."
            llm_response = ask_llm(prompt)
            add_or_increment()
            patch_file = Path(DB_PATH.parent) / f"patches/patch_{key}.txt"
            patch_file.parent.mkdir(parents=True, exist_ok=True)
            patch_file.write_text(llm_response, encoding="utf-8")
            log(f"🛠️ LLM generated patch for error key {key}")
        except Exception as ex_inner:
            log(f"💥 analyze_and_fix failed: {repr(ex_inner)}\n{traceback.format_exc()}")

def llm_worker(shutdown_event: threading.Event | None = None):
    while not (shutdown_event and shutdown_event.is_set() if shutdown_event else False):
        try:
            err_obj = llm_queue.get(timeout=1)
        except queue.Empty:
            continue
        try:
            analyze_and_fix([err_obj])
        except Exception as ex_worker:
            log(f"💥 LLM worker crash on {err_obj}: {repr(ex_worker)}\n{traceback.format_exc()}")
        finally:
            llm_queue.task_done()

# -----------------------
# Auto TypeScript fix cycle
# -----------------------
def auto_ts_fix_cycle() -> list[dict]:
    applied_actions: list[dict] = []
    patches_dir = Path(DB_PATH.parent) / "patches"
    patches_dir.mkdir(exist_ok=True)
    error_queue_file = patches_dir / "ts_errors.json"

    if error_queue_file.exists():
        try:
            errors = json.loads(error_queue_file.read_text(encoding="utf-8"))
        except json.JSONDecodeError as e:
            log(f"⚠️ Failed to read TS error queue: {repr(e)}")
            errors = []
    else:
        errors = []

    if not errors:
        log("ℹ️ No TypeScript errors to auto-fix.")
        return applied_actions

    prompt = f"Fix these TypeScript errors:\n{json.dumps(errors, indent=2)}"
    try:
        ts_actions_raw = ask_llm(prompt)
        ts_actions: list[dict] = json.loads(ts_actions_raw)
    except json.JSONDecodeError as e:
        log(f"⚠️ LLM returned malformed JSON: {repr(e)}")
        ts_actions = []

    if not ts_actions:
        log("ℹ️ LLM returned no TypeScript patches.")
        return applied_actions

    apply_ts_actions(ts_actions)
    applied_actions.extend(ts_actions)

    applied_dir = patches_dir / "applied"
    applied_dir.mkdir(exist_ok=True)
    archive_file = applied_dir / f"applied_{int(time.time())}.json"
    try:
        archive_file.write_text(json.dumps(ts_actions, indent=2), encoding="utf-8")
        log(f"✅ Archived {len(ts_actions)} applied TypeScript patches to {archive_file}")
    except Exception as e:
        log(f"⚠️ Failed to archive patches: {repr(e)}")

    try:
        error_queue_file.write_text("[]", encoding="utf-8")
    except Exception as e:
        log(f"⚠️ Failed to clear TS error queue: {repr(e)}")

    log(f"✅ Applied {len(ts_actions)} TypeScript patches via LLM")
    return applied_actions

# -----------------------
# Apply TypeScript actions
# -----------------------
def apply_ts_actions(actions: list[dict]):
    for act in actions:
        try:
            file_rel = act.get("file", "")
            action = act.get("action")
            symbol = act.get("symbol", "")
            module = act.get("module", "")
            fn_name = act.get("function", "")
            param = act.get("param", "")
            type_ = act.get("type", "")
            pkg = act.get("package", "")
            insert_after = act.get("insert_after")
            line = act.get("line")
            context_snippet = act.get("context_snippet", "")
            snippet = act.get("snippet", "")

            if file_rel.startswith("governance/") and governance_dir.exists():
                target_file = governance_dir / Path(file_rel).relative_to("governance")
            else:
                target_file = PROJECT_PATH / file_rel

            if action != "suggest_package" and not target_file.exists():
                log(f"⚠️ Target file does not exist: {target_file}, skipping action: {action}")
                continue

            if action == "add_import":
                insert_import(target_file, symbol, module)
            elif action == "create_function":
                create_function(target_file, symbol)
            elif action == "create_parameter":
                patch_function_signature(target_file, fn_name, param, type_)
            elif action == "change_type":
                patch_type_annotation(target_file, symbol, type_)
            elif action == "suggest_package":
                if pkg:
                    subprocess.run(["pnpm", "add", pkg], cwd=PROJECT_PATH)
                    log(f"📦 Suggested package installed: {pkg}")
                else:
                    log(f"⚠️ No package specified in suggest_package action: {act}")
            elif action == "insert_snippet":
                patch_contextual_insert(target_file, snippet, insert_after, line, context_snippet)
            else:
                log(f"ℹ️ Ignored unknown action: {act}")

        except Exception as e:
            # PATCH: Ensure file_rel always defined even if act is missing 'file'
            file_rel = act.get("file", "") if 'file' in act else "UNKNOWN"
            log(f"💥 apply_ts_actions failed on '{file_rel}' with action '{act.get('action', 'UNKNOWN')}': {repr(e)}\n{traceback.format_exc()}")


# -----------------------
# Playwright helpers
# -----------------------
def check_page_continuous_queue(page, url: str, max_retries=30, base_delay=2, max_delay=60, shutdown_event: threading.Event | None = None):
    attempt = 0
    delay = base_delay
    while not (shutdown_event and shutdown_event.is_set() if shutdown_event else False):
        try:
            log_thread(f"🌐 Navigating to {url} (attempt {attempt+1})", url)
            page.goto(url, timeout=5000)
            log_thread(f"✅ Page loaded: {url}", url)
            attempt = 0
            delay = base_delay
        except Exception as ex:
            log_thread(f"⚠️ Error on {url}: {repr(ex)}", url)
            err_obj = {"msg": f"Playwright error on {url}", "details": str(ex)}
            add_or_increment()
            llm_queue.put(err_obj)
            attempt += 1
            delay = min(delay * 2, max_delay)
            if attempt >= max_retries:
                log_thread(f"⚠️ Max retries for {url}, waiting...", url)
                attempt = 0
                delay = base_delay
        time.sleep(delay)

# -----------------------
# Main worker loop
# -----------------------
def main_loop():
    log("🚀 Entering main loop...")
    repo = repo_open()
    shutdown_event = threading.Event()

    # PATCH: Handler for signal.signal must accept (signum, frame)
    def handle_sigint(_signum: int,
                      _frame: FrameType | None):
        log("🛑 SIGINT received, shutting down...")
        shutdown_event.set()

    signal.signal(signal.SIGINT, handle_sigint)


    for i in range(2):
        threading.Thread(
            target=llm_worker,
            args=(shutdown_event,),
            daemon=True,
            name=f"LLM-{i}"
        ).start()
    log("🤖 LLM workers started...")

    pages_list = cfg.get("playwright", {}).get("pages", [])
    if not pages_list:
        log("⚠️ No Playwright pages in config")
        return

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        context = browser.new_context()
        page_threads = []
        for url in pages_list:
            page = context.new_page()
            t = threading.Thread(
                target=check_page_continuous_queue,
                args=(page, url),
                kwargs={"shutdown_event": shutdown_event},
                daemon=True,
                name=f"PW-{url}"
            )
            t.start()
            page_threads.append(t)
            log_thread(f"🎭 Playwright thread started for {url}", url)

        while not shutdown_event.is_set():
            try:
                paths_to_check = [PROJECT_PATH, GOV_PATH] if GOV_PATH.exists() else [PROJECT_PATH]
                ts_errors_file = run_tsc(paths_to_check)
                ts_actions = run_resolver(ts_errors_file)
                apply_ts_actions(ts_actions)

                for act in ts_actions:
                    err_obj = {
                        "msg": f"TS action: {act.get('action', 'unknown')}",
                        "details": json.dumps(act)
                    }
                    llm_queue.put(err_obj)

                auto_actions = auto_ts_fix_cycle()
                if auto_actions:
                    apply_ts_actions(auto_actions)

                if repo:
                    create_branch_if_missing(repo, BRANCH)
                    repo.git.checkout(BRANCH)
                    total_actions = len(ts_actions) + len(auto_actions)
                    commit_branch = "roots" if total_actions <= ROOTS_THRESHOLD else BRANCH
                    commit_all(repo, f"Auto update - errors: {total_actions}")
                    try:
                        repo.git.push("--set-upstream", "origin", commit_branch)
                    except Exception as ex:
                        log(f"⚠️ Push failed: {repr(ex)}")

                log("⏱️ Sleeping 10s before next TypeScript/Git cycle...")
                time.sleep(10)

            except Exception as ex:
                log(f"💥 Main loop crash: {repr(ex)}\n{traceback.format_exc()}")

        log("🛑 Main loop exiting, waiting for LLM queue to finish...")
        shutdown_event.set()
        llm_queue.join()

        try:
            browser.close()
        except Exception as e:
            log(f"⚠️ Browser close failed: {repr(e)}")

        log("✅ Worker fully stopped.")

# -----------------------
# Entry point
# -----------------------
if __name__ == "__main__":
    main_loop()