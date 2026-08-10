from fastapi.testclient import TestClient

from app.main import create_app


def test_metrics_endpoint_exposes_request_count(monkeypatch):
    monkeypatch.setenv("DYNAMODB_TABLE", "t"); monkeypatch.setenv("S3_BUCKET", "b")
    monkeypatch.setenv("SQS_QUEUE_URL", "q"); monkeypatch.setenv("MCP_GITHUB_URL", "g")
    monkeypatch.setenv("MCP_TEST_ANALYSIS_URL", "m")
    client = TestClient(create_app())
    client.get("/health/live")
    response = client.get("/metrics")
    assert response.status_code == 200
    assert "testscope_api_requests_total" in response.text
