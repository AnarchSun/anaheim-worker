#!/usr/bin/env python3
import time
from worker_full import (
    PROJECT_PATH,
    governance_dir,
    run_tsc,
    run_resolver,
    apply_ts_actions,
    collect_errors,
    analyze_and_fix,
    repo_open,
    apply_strategy_and_commit,
    log,
    BRANCH
)

# Stub LLM rapide
def ask_llm_stub(prompt, timeout=5):
    log("💡 LLM simulated: returning empty string")
    return ""

# Stub Playwright rapide
def devtools_check_stub():
    log("💡 Playwright simulated: skipped")

def fastloop_main():
    log("🛠️ Anaheim Worker fast-loop started")
    repo = repo_open()

    iteration = 0
    while True:
        iteration += 1
        log(f"🔁 Iteration {iteration}")

        # 1️⃣ TypeScript check
        paths_to_check = [PROJECT_PATH]
        if governance_dir.exists():
            paths_to_check.append(governance_dir)
        ts_errors_file = run_tsc(paths=paths_to_check)
        log(f"✅ TSC check done, errors file: {ts_errors_file}")

        # 2️⃣ Resolver TS
        ts_actions = run_resolver(ts_errors_file)
        log(f"✅ Resolver actions: {ts_actions}")
        apply_ts_actions(ts_actions)

        # 3️⃣ Collect errors & LLM
        errs, _ = collect_errors()
        log(f"✅ Collected errors: {len(errs)}")
        analyze_and_fix(errs)
        log("✅ LLM analysis simulated")

        # 4️⃣ Playwright
        devtools_check_stub()
        log("✅ Playwright check simulated")

        # 5️⃣ Commit / push
        apply_strategy_and_commit(repo, errs)
        log("✅ Commit & push attempted")

        # Pause rapide pour testing
        time.sleep(10)  # boucle toutes les 10 secondes

if __name__ == "__main__":
    fastloop_main()
