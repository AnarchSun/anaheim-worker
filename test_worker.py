# FILE: test_worker.py
import threading
import time

from workers.modules.anaheim_worker_safe import llm_queue, log, worker_thread_cycle
from workers.modules.worker_fastloop import pause_event, save_queue_state, shutdown_event, load_queue_state


def test_hyper_fastloop_real_tasks():
    shutdown_event.clear()
    pause_event.set()  # pause worker so we can snapshot queue

    tasks_to_apply = [
        {
            "file": "src/workers/modules/worker_fastloop.py",
            "action_type": "syntax_fix",
            "description": "Added exception handling in worker_thread_cycle",
            "timestamp": time.time()
        },
        {
            "file": "src/workers/modules/worker_fastloop.py",
            "action_type": "queue_fix",
            "description": "Persist queue mid-run",
            "timestamp": time.time()
        },
        {
            "file": "src/workers/modules/worker_fastloop.py",
            "action_type": "logging_update",
            "description": "Redirect logs to logs/ folder",
            "timestamp": time.time()
        }
    ]

    for t in tasks_to_apply:
        llm_queue.put(t)

    log(f"📝 Tasks added: {[t['description'] for t in tasks_to_apply]}")

    # Snapshot queue safely before worker starts
    snapshot_before = list(llm_queue.queue)
    log(f"💾 Snapshot before processing: {snapshot_before}")

    # Start worker thread
    t_worker = threading.Thread(target=worker_thread_cycle, args=(llm_queue, 0), daemon=True)
    t_worker.start()

    time.sleep(0.1)  # let worker start
    pause_event.clear()  # allow processing

    # Let worker process tasks slowly
    time.sleep(2)

    # Save mid-run
    save_queue_state()
    log(f"💾 Snapshot mid-run: {list(llm_queue.queue)}")

    # Shutdown worker
    shutdown_event.set()
    t_worker.join(timeout=5)

    # Reload queue to verify persistence
    load_queue_state()
    log(f"📝 Remaining tasks after reload: {list(llm_queue.queue)}")

    # Verify queue items are dicts
    assert all(isinstance(t, dict) for t in list(llm_queue.queue)), "Queue items should be dicts with metadata"
