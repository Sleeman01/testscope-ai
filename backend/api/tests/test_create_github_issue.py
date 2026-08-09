import boto3
import json
import pytest
from moto import mock_aws
from unittest.mock import AsyncMock, patch
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
        s3 = boto3.client("s3", region_name="us-east-1")
        s3.create_bucket(Bucket="testscope-reports-test")
        from app.main import create_app
        yield TestClient(create_app())

def test_returns_404_for_unknown_id(client):
    response = client.post("/api/analyses/does-not-exist/github-issue")
    assert response.status_code == 404

def test_returns_409_when_not_completed(client):
    created = client.post("/api/analyses", json={"repository": "acme/widgets", "issue_number": 42}).json()
    response = client.post(f"/api/analyses/{created['analysis_id']}/github-issue")
    assert response.status_code == 409

def test_creates_issue_when_completed(client):
    created = client.post("/api/analyses", json={"repository": "acme/widgets", "issue_number": 42}).json()
    analysis_id = created["analysis_id"]
    s3_key = f"acme/widgets/42/{analysis_id}.json"
    boto3.client("s3", region_name="us-east-1").put_object(
        Bucket="testscope-reports-test", Key=s3_key,
        Body=json.dumps({"missing_tests": [{"behavior": "401 on bad password"}]}).encode(),
    )
    ddb = boto3.resource("dynamodb", region_name="us-east-1").Table("testscope-analyses-test")
    ddb.update_item(Key={"analysis_id": analysis_id}, UpdateExpression="SET #s = :s, s3_report_key = :k",
                     ExpressionAttributeNames={"#s": "status"}, ExpressionAttributeValues={":s": "completed", ":k": s3_key})
    with patch("app.routes.analyses.call_github_tool", new=AsyncMock(return_value={"html_url": "https://github.com/acme/widgets/issues/99"})):
        response = client.post(f"/api/analyses/{analysis_id}/github-issue")
    assert response.status_code == 200
    assert response.json()["github_issue_url"] == "https://github.com/acme/widgets/issues/99"
