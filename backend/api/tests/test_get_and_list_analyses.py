import boto3
import pytest
from fastapi.testclient import TestClient
from moto import mock_aws


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
            AttributeDefinitions=[
                {"AttributeName": "analysis_id", "AttributeType": "S"},
                {"AttributeName": "repository_issue", "AttributeType": "S"},
                {"AttributeName": "created_at", "AttributeType": "S"},
                {"AttributeName": "gsi2_pk", "AttributeType": "S"},
            ],
            BillingMode="PAY_PER_REQUEST",
            GlobalSecondaryIndexes=[
                {"IndexName": "repository_issue-index", "KeySchema": [
                    {"AttributeName": "repository_issue", "KeyType": "HASH"},
                    {"AttributeName": "created_at", "KeyType": "RANGE"}],
                 "Projection": {"ProjectionType": "ALL"}},
                {"IndexName": "recent-index", "KeySchema": [
                    {"AttributeName": "gsi2_pk", "KeyType": "HASH"},
                    {"AttributeName": "created_at", "KeyType": "RANGE"}],
                 "Projection": {"ProjectionType": "ALL"}},
            ],
        )
        sqs = boto3.client("sqs", region_name="us-east-1")
        sqs.create_queue(QueueName="q")
        from api_app.main import create_app
        yield TestClient(create_app())

def test_get_returns_404_for_unknown_id(client):
    response = client.get("/api/analyses/does-not-exist")
    assert response.status_code == 404

def test_get_returns_created_analysis(client):
    created = client.post("/api/analyses", json={"repository": "acme/widgets", "issue_number": 42}).json()
    response = client.get(f"/api/analyses/{created['analysis_id']}")
    assert response.status_code == 200
    assert response.json()["status"] == "pending"

def test_list_returns_recent_analyses(client):
    client.post("/api/analyses", json={"repository": "acme/widgets", "issue_number": 1})
    client.post("/api/analyses", json={"repository": "acme/widgets", "issue_number": 2})
    response = client.get("/api/analyses?limit=10")
    assert response.status_code == 200
    assert len(response.json()["analyses"]) == 2

def test_list_filters_by_repository_and_issue_number(client):
    client.post("/api/analyses", json={"repository": "acme/widgets", "issue_number": 1})
    client.post("/api/analyses", json={"repository": "acme/widgets", "issue_number": 2})
    response = client.get("/api/analyses?repository=acme/widgets&issue_number=1")
    assert response.status_code == 200
    body = response.json()
    assert len(body["analyses"]) == 1
    assert body["analyses"][0]["issue_number"] == 1
    assert body["next_cursor"] is None
