import shutil
import subprocess
import time
from pathlib import Path


class WorkspaceError(Exception):
    def __init__(self, code: str, message: str):
        self.code = code
        self.message = message
        super().__init__(message)

class WorkspaceManager:
    def get_or_clone(self, analysis_id: str, clone_url: str, ref: str, root: Path) -> Path:
        target = root / analysis_id
        if target.exists():
            return target
        root.mkdir(parents=True, exist_ok=True)
        try:
            subprocess.run(
                ["git", "clone", "--depth", "1", "--single-branch", "--branch", ref, clone_url, str(target)],
                check=True, capture_output=True, text=True, timeout=30,
            )
        except subprocess.TimeoutExpired:
            shutil.rmtree(target, ignore_errors=True)
            raise WorkspaceError("CLONE_TIMEOUT", f"Clone of {clone_url} exceeded 30s")
        except subprocess.CalledProcessError as e:
            shutil.rmtree(target, ignore_errors=True)
            stderr = (e.stderr or "")[:500]
            raise WorkspaceError("CLONE_FAILED", f"git clone failed: {stderr}")
        return target

    def cleanup(self, analysis_id: str, root: Path) -> bool:
        target = root / analysis_id
        if target.exists():
            shutil.rmtree(target, ignore_errors=True)
            return True
        return False

    def sweep_stale(self, root: Path, max_age_seconds: int) -> int:
        if not root.exists():
            return 0
        now = time.time()
        removed = 0
        for entry in root.iterdir():
            if entry.is_dir() and (now - entry.stat().st_mtime) > max_age_seconds:
                shutil.rmtree(entry, ignore_errors=True)
                removed += 1
        return removed
