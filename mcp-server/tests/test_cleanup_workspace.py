from pathlib import Path
from tools.cleanup_workspace import cleanup_workspace

def test_deletes_existing_workspace(tmp_path):
    root = tmp_path / "workspace_root"
    (root / "a1").mkdir(parents=True)
    result = cleanup_workspace("a1", root=root)
    assert result == {"deleted": True}
    assert not (root / "a1").exists()

def test_reports_false_when_nothing_to_delete(tmp_path):
    root = tmp_path / "workspace_root"
    result = cleanup_workspace("does-not-exist", root=root)
    assert result == {"deleted": False}
