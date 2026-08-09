import os
import subprocess
import sys
import time
from pathlib import Path
import pytest

@pytest.fixture(scope="session", autouse=True)
def mcp_test_analysis_server():
    mcp_server_dir = Path(__file__).parent.parent.parent.parent / "mcp-server"
    # This subprocess is a separate OS process — moto's mock_aws() (used by
    # test_runner_e2e.py's full_env fixture) only patches boto3 within the pytest
    # process itself, so it has NO effect here. report_saver's save_coverage_report call
    # crosses into this subprocess and makes a REAL, unmocked boto3 call. If this machine
    # has ambient AWS credentials (e.g. ~/.aws/credentials), inheriting the parent
    # environment wholesale would let that real call succeed against a real account —
    # confirmed empirically during development (boto3 logged "Found credentials in shared
    # credentials file"). Stripping AWS_* from the inherited env and forcing moto's own
    # documented fake-credential convention guarantees any real AWS call here fails fast
    # (InvalidClientTokenId) instead of possibly succeeding against real infrastructure.
    base_env = {k: v for k, v in os.environ.items() if not k.startswith("AWS_")}
    proc = subprocess.Popen(
        [sys.executable, "server.py"],
        cwd=str(mcp_server_dir),
        env={**base_env, "AWS_ACCESS_KEY_ID": "testing", "AWS_SECRET_ACCESS_KEY": "testing",
             "AWS_SECURITY_TOKEN": "testing", "AWS_SESSION_TOKEN": "testing", "AWS_DEFAULT_REGION": "us-east-1",
             "MCP_PORT": "8198", "DYNAMODB_TABLE": "testscope-analyses-test",
             "S3_BUCKET": "testscope-reports-test", "GITHUB_TOKEN": "unused",
             "MCP_GITHUB_URL": "http://localhost:8197/mcp", "WORKSPACE_ROOT": "/tmp/testscope-e2e-workspace"},
    )
    # plan.md's own snippet used time.sleep(1.0) here, but Task 8's live verification
    # (mcp-server/tests/test_mcp_integration.py) already measured real subprocess startup
    # (boto3/GitPython/mcp/uvicorn imports) at ~5-6s and bumped this to 8.0 — applying that
    # same already-established fix here rather than reintroducing a known-flaky value.
    time.sleep(8.0)
    yield
    proc.terminate()
    proc.wait(timeout=5)
