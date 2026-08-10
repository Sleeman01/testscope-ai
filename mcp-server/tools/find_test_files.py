import os
from pathlib import Path

from workspace import WorkspaceError, WorkspaceManager

MAX_REPO_BYTES = 500 * 1024 * 1024
MAX_FILES = 30
_manager = WorkspaceManager()

async def find_test_files(analysis_id: str, clone_url: str, ref: str, keywords: list[str], github_client, owner: str = "", repo: str = "") -> dict:
    size_bytes = await github_client.get_repo_size_bytes(owner, repo)
    if size_bytes > MAX_REPO_BYTES:
        raise WorkspaceError("REPO_TOO_LARGE", f"Repo is {size_bytes} bytes, exceeds {MAX_REPO_BYTES}")

    root = Path(os.environ.get("WORKSPACE_ROOT", "/workspace"))
    workspace = _manager.get_or_clone(analysis_id, clone_url, ref, root)

    candidates = [
        p for p in workspace.rglob("test_*.py")
    ] + [p for p in workspace.rglob("*_test.py")]
    scored = []
    for path in set(candidates):
        text = path.read_text(errors="ignore").lower()
        matched = [kw for kw in keywords if kw.lower() in text or kw.lower() in path.name.lower()]
        if matched or not keywords:
            scored.append({
                "path": str(path.relative_to(workspace)),
                "size_bytes": path.stat().st_size,
                "matched_keywords": matched,
            })
    scored.sort(key=lambda f: len(f["matched_keywords"]), reverse=True)
    return {"files": scored[:MAX_FILES]}
