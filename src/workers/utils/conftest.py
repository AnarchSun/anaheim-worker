import sys
import types
import pytest

class MockCallTracker:
    """Tracker pour suivre tous les appels aux fonctions mockées."""
    def __init__(self):
        self.calls = []

    def track(self, func_name, *args, **kwargs):
        print(f"[mock-call] {func_name} called with args={args}, kwargs={kwargs}")
        self.calls.append((func_name, args, kwargs))
        if func_name == "repo_open":
            return {"repo": "mock"}
        if func_name == "apply_ts_actions":
            return None
        if func_name == "log":
            return None
        if func_name == "auto_ts_fix_cycle_safe":
            return ([{"mock_action": True}], args[1] + 1)
        return None

@pytest.fixture(autouse=True)
def mock_missing_modules():
    tracker = MockCallTracker()
    modules_to_mock = ["hyper_optimal_worker"]

    for mod_name in modules_to_mock:
        if mod_name not in sys.modules:
            fake_mod = types.ModuleType(mod_name)
            fake_mod.repo_open = lambda: tracker.track("repo_open")
            fake_mod.apply_ts_actions = lambda actions: tracker.track("apply_ts_actions", actions)
            fake_mod.log = lambda msg: tracker.track("log", msg)
            fake_mod.auto_ts_fix_cycle_safe = lambda repo, last_commit_time: tracker.track(
                "auto_ts_fix_cycle_safe", repo, last_commit_time
            )
            sys.modules[mod_name] = fake_mod

    return tracker
