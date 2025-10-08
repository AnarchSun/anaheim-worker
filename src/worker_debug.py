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
    LOG_FILE,
    log,
    BRANCH
)

def debug_main():
    log("🛠️ Anaheim Worker debug iteration started")
    repo = repo_open()

    # 1️⃣ Lancer TSC
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

    # 3️⃣ Collect errors & LLM
    errs, _ = collect_errors()
    log(f"✅ Collected errors: {len(errs)}")
    analyze_and_fix(errs)
    log("✅ LLM analysis done")

    # 4️⃣ Playwright check
    devtools_check()
    log("✅ Playwright checks done")

    # 5️⃣ Commit & push strategy
    apply_strategy_and_commit(repo, errs)
    log("✅ Commit & push attempted")

    log("🛑 Debug iteration finished")

if __name__ == "__main__":
    debug_main()
