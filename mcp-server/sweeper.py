import threading
from pathlib import Path

from workspace import WorkspaceManager

_manager = WorkspaceManager()

def start_sweeper(root: Path, interval_seconds: int = 900, max_age_seconds: int = 3600) -> threading.Thread:
    def _loop():
        while True:
            _manager.sweep_stale(root, max_age_seconds)
            threading.Event().wait(interval_seconds)

    thread = threading.Thread(target=_loop, daemon=True, name="workspace-sweeper")
    thread.start()
    return thread
