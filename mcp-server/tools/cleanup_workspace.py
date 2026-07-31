import os
from pathlib import Path
from workspace import WorkspaceManager

_manager = WorkspaceManager()

def cleanup_workspace(analysis_id: str, root: Path | None = None) -> dict:
    root = root or Path(os.environ.get("WORKSPACE_ROOT", "/workspace"))
    deleted = _manager.cleanup(analysis_id, root)
    return {"deleted": deleted}
