import os
from pathlib import Path

MAX_BYTES = 50 * 1024

def read_test_file(analysis_id: str, path: str, root: Path | None = None) -> dict:
    root = root or Path(os.environ.get("WORKSPACE_ROOT", "/workspace"))
    full_path = (root / analysis_id / path).resolve()
    workspace_root = (root / analysis_id).resolve()
    if workspace_root not in full_path.parents and full_path != workspace_root:
        raise ValueError(f"Path {path} escapes workspace for {analysis_id}")
    raw = full_path.read_bytes()
    truncated = len(raw) > MAX_BYTES
    content = raw[:MAX_BYTES].decode(errors="ignore") if truncated else raw.decode(errors="ignore")
    return {"content": content, "truncated": truncated}
