import os
import socket
import threading
import time
from pathlib import Path

import uvicorn
from fastapi import FastAPI
from mcp.server import MCPServer

from github_client import GithubClient
from sweeper import start_sweeper
from tools.cleanup_workspace import cleanup_workspace as _cleanup_workspace
from tools.extract_test_metadata import extract_test_metadata as _extract_test_metadata
from tools.find_test_files import find_test_files as _find_test_files
from tools.get_previous_analysis import get_previous_analysis as _get_previous_analysis
from tools.read_test_file import read_test_file as _read_test_file
from tools.save_coverage_report import save_coverage_report as _save_coverage_report

mcp = MCPServer("testscope-test-analysis")
_github_client = GithubClient()
WORKSPACE_ROOT = Path(os.environ.get("WORKSPACE_ROOT", "/workspace"))

@mcp.tool()
async def find_test_files(analysis_id: str, repository: str, ref: str, keywords: list[str]) -> dict:
    owner, repo = repository.split("/", 1)
    clone_url = f"https://x-access-token:{os.environ['GITHUB_TOKEN']}@github.com/{repository}.git"
    return await _find_test_files(analysis_id, clone_url, ref, keywords, _github_client, owner, repo)

@mcp.tool()
def read_test_file(analysis_id: str, path: str) -> dict:
    return _read_test_file(analysis_id, path, root=WORKSPACE_ROOT)

@mcp.tool()
def extract_test_metadata(analysis_id: str, path: str) -> dict:
    content = _read_test_file(analysis_id, path, root=WORKSPACE_ROOT)["content"]
    return _extract_test_metadata(content)

@mcp.tool()
def save_coverage_report(analysis_id: str, repository: str, issue_number: int, requirement: dict,
                          coverage_matrix: list, missing_tests: list, test_plan: list, status: str,
                          tool_call_trace: list) -> dict:
    return _save_coverage_report(analysis_id, repository, issue_number, requirement, coverage_matrix,
                                  missing_tests, test_plan, status, tool_call_trace)

@mcp.tool()
def get_previous_analysis(repository: str, issue_number: int) -> dict:
    return _get_previous_analysis(repository, issue_number)

@mcp.tool()
def cleanup_workspace(analysis_id: str) -> dict:
    return _cleanup_workspace(analysis_id, root=WORKSPACE_ROOT)

def build_health_app() -> FastAPI:
    app = FastAPI()
    app.get("/health/live")(lambda: {"status": "ok"})
    app.get("/health/ready")(lambda: {"status": "ok"})
    return app

def _wait_until_listening(port: int, timeout_seconds: float = 30.0) -> None:
    """Poll (cheap: no fastapi/uvicorn work) until the main MCP transport is accepting
    connections, so the health server's own (heavier) uvicorn startup doesn't compete with
    mcp.run()'s startup for CPU/GIL time in this same process. Falls through on timeout —
    best-effort sequencing, not a correctness gate; the health app's responses were never
    MCP-state-aware to begin with (see build_health_app)."""
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=0.5):
                return
        except OSError:
            time.sleep(0.1)

def _start_health_server(port: int = 8101):
    _wait_until_listening(int(os.environ.get("MCP_PORT", "8100")))
    uvicorn.run(build_health_app(), host="0.0.0.0", port=port, log_level="warning")

if __name__ == "__main__":
    start_sweeper(WORKSPACE_ROOT, interval_seconds=900, max_age_seconds=3600)
    threading.Thread(target=_start_health_server, daemon=True).start()
    mcp.run(
        transport="streamable-http",
        host=os.environ.get("MCP_HOST", "0.0.0.0"),
        port=int(os.environ.get("MCP_PORT", "8100")),
    )
