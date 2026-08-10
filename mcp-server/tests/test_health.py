import os

# server.py instantiates GithubClient() at module scope, which reads MCP_GITHUB_URL
# eagerly — must be set before import, since monkeypatch fixtures don't run until after
# collection-time imports complete. No other test imports `server` directly (they import
# github_client.GithubClient itself and set this via monkeypatch inside the test function),
# so this is the first place that requirement surfaces.
os.environ.setdefault("MCP_GITHUB_URL", "http://mcp-github:8100/mcp")
os.environ.setdefault("GITHUB_TOKEN", "test-token")

from fastapi.testclient import TestClient

from server import build_health_app


def test_health_live_returns_ok():
    client = TestClient(build_health_app())
    response = client.get("/health/live")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_health_ready_returns_ok():
    client = TestClient(build_health_app())
    response = client.get("/health/ready")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
