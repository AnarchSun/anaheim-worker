# src/workers/modules/anarcrypt_worker_hyper.py
#!/usr/bin/env python3
from .hyper_optimal_worker import (
    PROJECT_PATH, log, repo_open, apply_ts_actions, handle_ts_error,
    auto_ts_fix_cycle_safe, ask_llm, llm_queue, shutdown_event,
    worker_thread_cycle, copilot_retrier, start_hot_reload
)

def run_hyper_worker(dry_run: bool = True):
    from hyper_optimal_worker import hyper_worker_main
    hyper_worker_main(num_threads=4, dry_run=dry_run)

if __name__ == "__main__":
    run_hyper_worker(dry_run=True)
