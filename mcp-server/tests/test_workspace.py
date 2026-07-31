import pytest
from pathlib import Path
from workspace import WorkspaceManager, WorkspaceError
from tests.fixtures.make_bare_repo import make_bare_repo

def test_get_or_clone_creates_workspace_and_reuses_it(tmp_path):
    clone_url = make_bare_repo(tmp_path)
    root = tmp_path / "workspace_root"
    mgr = WorkspaceManager()
    path1 = mgr.get_or_clone("analysis-1", clone_url, "main", root)
    assert (path1 / "tests" / "test_login.py").exists()
    path2 = mgr.get_or_clone("analysis-1", clone_url, "main", root)
    assert path1 == path2  # reused, not re-cloned

def test_get_or_clone_raises_on_bad_url(tmp_path):
    root = tmp_path / "workspace_root"
    mgr = WorkspaceManager()
    with pytest.raises(WorkspaceError) as exc:
        mgr.get_or_clone("analysis-2", "file:///no/such/repo.git", "main", root)
    assert exc.value.code == "CLONE_FAILED"
    assert not (root / "analysis-2").exists()  # partial dir removed on failure
