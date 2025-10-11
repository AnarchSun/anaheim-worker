#!/usr/bin/env python3
from worker_full import (
    PROJECT_PATH,
    governance_dir,
    run_tsc,
    run_resolver,
    apply_ts_actions,
    collect_errors,
    analyze_and_fix,
    devtools_check,
    repo_open,
    apply_strategy_and_commit,
    log,
    BRANCH
)

# Stub pour LLM simulé
def ask_llm_stub(prompt, timeout=5):
    log("💡 LLM simulated: returning empty string")
    return ""

# Stub pour Playwright rapide
def devtools_check_stub():
    log("💡 Playwright simulated: skipped")

def dryrun_main():
    log("🛠️ Anaheim Worker dry-run started")
    repo = repo_open()

    # 1️⃣ TSC
    paths_to_check = [PROJECT_PATH]
    if governance_dir.exists():
        paths_to_check.append(governance_dir)
    ts_errors_file = run_tsc(paths=paths_to_check)
    log(f"✅ TSC check done, errors file: {ts_errors_file}")

    # 2️⃣ Resolver TS
    ts_actions = run_resolver(ts_errors_file)
    log(f"✅ Resolver actions: {ts_actions}")
    apply_ts_actions(ts_actions)
    log("✅ Actions appliquées")

    # 3️⃣ Collect errors
    errs, _ = collect_errors()
    log(f"✅ Collected errors: {len(errs)}")
    analyze_and_fix(errs)  # LLM stub inside worker_full doit être remplacé si nécessaire
    log("✅ LLM analysis simulated")

    # 4️⃣ Playwright stub
    devtools_check_stub()
    log("✅ Playwright check simulated")

    # 5️⃣ Commit & push
    apply_strategy_and_commit(repo, errs)
    log("✅ Commit & push attempted (dry-run)")

    log("🛑 Dry-run finished")

if __name__ == "__main__":
    dryrun_main()
