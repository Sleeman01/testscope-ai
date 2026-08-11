from fastapi.testclient import TestClient

from api_app.main import create_app


def test_health_live_returns_ok():
    client = TestClient(create_app())
    response = client.get("/health/live")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}

def test_health_ready_returns_ok(monkeypatch):
    monkeypatch.setenv("DYNAMODB_TABLE", "t")
    monkeypatch.setenv("S3_BUCKET", "b")
    monkeypatch.setenv("SQS_QUEUE_URL", "https://sqs.us-east-1.amazonaws.com/000/q")
    monkeypatch.setenv("MCP_GITHUB_URL", "http://mcp-github")
    monkeypatch.setenv("MCP_TEST_ANALYSIS_URL", "http://mcp-test-analysis")
    client = TestClient(create_app())
    response = client.get("/health/ready")
    assert response.status_code == 200
