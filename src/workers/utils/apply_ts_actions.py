from typing import List

from workers import apply_patch


def apply_ts_actions(actions: List[dict]):
    for patch in actions:
        apply_patch(patch)