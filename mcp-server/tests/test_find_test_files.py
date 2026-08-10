from unittest.mock import AsyncMock

import pytest

from tests.fixtures.make_bare_repo import make_bare_repo
from tools.find_test_files import find_test_files


@pytest.mark.asyncio
async def test_finds_files_matching_keywords(tmp_path, monkeypatch):
    clone_url = make_bare_repo(tmp_path)
    monkeypatch.setenv("WORKSPACE_ROOT", str(tmp_path / "workspace_root"))
    fake_mcp_client = AsyncMock()
    fake_mcp_client.get_repo_size_bytes = AsyncMock(return_value=1024)
    result = await find_test_files(
        analysis_id="a1", clone_url=clone_url, ref="main",
        keywords=["login"], github_client=fake_mcp_client,
    )
    paths = [f["path"] for f in result["files"]]
    assert any("test_login.py" in p for p in paths)

@pytest.mark.asyncio
async def test_rejects_oversized_repo(tmp_path, monkeypatch):
    monkeypatch.setenv("WORKSPACE_ROOT", str(tmp_path / "workspace_root"))
    fake_mcp_client = AsyncMock()
    fake_mcp_client.get_repo_size_bytes = AsyncMock(return_value=600 * 1024 * 1024)
    from workspace import WorkspaceError
    with pytest.raises(WorkspaceError) as exc:
        await find_test_files(
            analysis_id="a2", clone_url="file:///irrelevant", ref="main",
            keywords=["login"], github_client=fake_mcp_client,
        )
    assert exc.value.code == "REPO_TOO_LARGE"
