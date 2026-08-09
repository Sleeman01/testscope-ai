import json
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
        s3 = boto3.client("s3", region_name="us-east-1")
        s3.create_bucket(Bucket="testscope-reports-test")
        from app.main import create_app
        yield TestClient(create_app())

def test_returns_404_for_unknown_id(client):
    response = client.get("/api/analyses/does-not-exist/report")
    assert response.status_code == 404

def test_returns_409_when_not_completed(client):
    created = client.post("/api/analyses", json={"repository": "acme/widgets", "issue_number": 42}).json()
    response = client.get(f"/api/analyses/{created['analysis_id']}/report")
    assert response.status_code == 409

def test_returns_report_when_completed(client):
    created = client.post("/api/analyses", json={"repository": "acme/widgets", "issue_number": 42}).json()
    analysis_id = created["analysis_id"]
    s3_key = f"acme/widgets/42/{analysis_id}.json"
    s3 = boto3.client("s3", region_name="us-east-1")
    s3.put_object(Bucket="testscope-reports-test", Key=s3_key, Body=json.dumps({
        "requirement": {"feature_name": "Login"}, "coverage_matrix": [], "test_plan": [],
        "missing_tests": [], "tool_call_trace": [],
    }).encode())
    ddb = boto3.resource("dynamodb", region_name="us-east-1").Table("testscope-analyses-test")
    ddb.update_item(Key={"analysis_id": analysis_id},
                     UpdateExpression="SET #s = :s, s3_report_key = :k",
                     ExpressionAttributeNames={"#s": "status"},
                     ExpressionAttributeValues={":s": "completed", ":k": s3_key})
    response = client.get(f"/api/analyses/{analysis_id}/report")
    assert response.status_code == 200
    body = response.json()
    assert body["requirement"]["feature_name"] == "Login"
    assert body["download_url"].startswith("https://")
