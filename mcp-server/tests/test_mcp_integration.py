import asyncio
import json
import os
import sys
from pathlib import Path

import pytest
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client

from tests.fixtures.make_bare_repo import make_bare_repo


def _payload(result):
    # structured_content is None for tools with plain `dict` return-type annotations in
    # this SDK version (confirmed for both our own tools and the external github-mcp-server
    # — not specific to either); the payload is JSON text in content[0].text instead.
    if result.structured_content is not None:
        return result.structured_content
    text = next(b.text for b in result.content if getattr(b, "text", None))
    return json.loads(text)

@pytest.mark.asyncio
async def test_find_and_extract_over_real_mcp_transport(tmp_path, monkeypatch):
    make_bare_repo(tmp_path)
    monkeypatch.setenv("WORKSPACE_ROOT", str(tmp_path / "workspace_root"))
    monkeypatch.setenv("DYNAMODB_TABLE", "unused-in-this-test")
    monkeypatch.setenv("S3_BUCKET", "unused-in-this-test")
    monkeypatch.setenv("GITHUB_TOKEN", "unused-in-this-test")
    monkeypatch.setenv("MCP_GITHUB_URL", "http://localhost:1")  # unused: find_test_files below skips the size check via a stub

    # This test exercises read_test_file + extract_test_metadata + cleanup_workspace directly
    # over real MCP transport, seeding the workspace ourselves to avoid needing a live mcp-github.
    proc = await asyncio.create_subprocess_exec(
        sys.executable, "server.py",
        env={**os.environ, "MCP_PORT": "8199"},
        cwd=str(Path(__file__).parent.parent),
    )
    try:
        await asyncio.sleep(8.0)  # subprocess startup (boto3/GitPython/mcp/uvicorn imports) measured ~5-6s in this environment
        workspace = tmp_path / "workspace_root" / "int-test-1"
        workspace.mkdir(parents=True)
        (workspace / "test_login.py").write_text(
            "def test_login_rejects_invalid_password():\n    assert True\n"
        )
        async with (
            streamable_http_client("http://localhost:8199/mcp") as (read, write),
            ClientSession(read, write) as session,
        ):
            await session.initialize()
            read_result = await session.call_tool("read_test_file", {"analysis_id": "int-test-1", "path": "test_login.py"})
            assert "test_login_rejects_invalid_password" in _payload(read_result)["content"]

            meta_result = await session.call_tool("extract_test_metadata", {"analysis_id": "int-test-1", "path": "test_login.py"})
            names = [t["name"] for t in _payload(meta_result)["tests"]]
            assert "test_login_rejects_invalid_password" in names

            cleanup_result = await session.call_tool("cleanup_workspace", {"analysis_id": "int-test-1"})
            assert _payload(cleanup_result)["deleted"] is True
    finally:
        proc.terminate()
        await asyncio.wait_for(proc.wait(), timeout=5)
