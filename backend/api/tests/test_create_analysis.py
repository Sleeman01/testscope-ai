import boto3
import pytest
from moto import mock_aws
from fastapi.testclient import TestClient

@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv("AWS_DEFAULT_REGION", "us-east-1")
    monkeypatch.setenv("DYNAMODB_TABLE", "testscope-analyses-test")
    monkeypatch.setenv("S3_BUCKET", "testscope-reports-test")
    monkeypatch.setenv("SQS_QUEUE_URL", "https://queue.amazonaws.com/123/q")
    monkeypatch.setenv("MCP_GITHUB_URL", "http://mcp-github")
    monkeypatch.setenv("MCP_TEST_ANALYSIS_URL", "http://mcp-test-analysis")
    with mock_aws():
        ddb = boto3.client("dynamodb", region_name="us-east-1")
        ddb.create_table(
            TableName="testscope-analyses-test", KeySchema=[{"AttributeName": "analysis_id", "KeyType": "HASH"}],
            AttributeDefinitions=[{"AttributeName": "analysis_id", "AttributeType": "S"}],
            BillingMode="PAY_PER_REQUEST",
        )
        sqs = boto3.client("sqs", region_name="us-east-1")
        sqs.create_queue(QueueName="q")
        from app.main import create_app
        yield TestClient(create_app())

def test_create_analysis_returns_202_and_enqueues(client):
    response = client.post("/api/analyses", json={"repository": "acme/widgets", "issue_number": 42})
    assert response.status_code == 202
    body = response.json()
    assert body["status"] == "pending"
    assert "analysis_id" in body

def test_create_analysis_does_not_dedupe_concurrent_requests(client):
    r1 = client.post("/api/analyses", json={"repository": "acme/widgets", "issue_number": 42})
    r2 = client.post("/api/analyses", json={"repository": "acme/widgets", "issue_number": 42})
    assert r1.json()["analysis_id"] != r2.json()["analysis_id"]  # stated v1 limitation, spec §7
