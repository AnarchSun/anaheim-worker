# PATH: src/workers/utils/apply_ts_actions.py
#!/usr/bin/env python3
from workers.utils.apply_patch import apply_patch   # ✅ fixed import

def apply_ts_actions(actions):
    """Apply TypeScript actions using patch utilities."""
    for action in actions:
        print(f"[TS ACTION] Applying: {action}")
        apply_patch(action)
