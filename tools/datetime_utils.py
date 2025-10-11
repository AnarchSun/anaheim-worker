# tools/datetime_utils.py
from datetime import datetime, timezone

def now_utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S %Z")
