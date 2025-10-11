# Debug Main Flow — Anaheim Worker

```mermaid
flowchart TD
    A["🛠️ debug_main(dry_run=True)"] --> B["🛠️ Log: DEBUG iteration started"]
    B --> C["📦 repo = repo_open()"]
    C -->|repo is None| D["❌ Repo not available → abort"]
    C -->|repo available| E["✅ Continue execution"]

    E --> F["📝 ts_error_stub = {file:'<unknown>', type:'create_function', symbol:'DebugStub'}"]
    F --> G["⚡ apply_ts_actions([ts_error_stub])\n(patchée → tracker.calls.append)"]
    G --> H["✅ Log: Stub TS action applied"]

    H --> I["🔧 for err in ts_errors: handle_ts_error(err)\n(patchée → prints '[worker-safe] TS error handled')"]
    I --> J["💡 if dry_run → devtools_check_stub()\n(patchée → prints stub call)"]

    J --> K["🌿 for branch in ['Orion','Orion-Exploration']:\n  applied_actions, last_commit_times[...] = auto_ts_fix_cycle_safe(repo, last_commit_time)\n  (patchée → tracker.calls.append)\n  if applied_actions → log('🛠 branch applied X actions')"]

    K --> L["🛑 Log: DEBUG iteration finished"]
