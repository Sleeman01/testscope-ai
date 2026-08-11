import boto3
import pytest
from dynamodb import AnalysisStore
from moto import mock_aws

from worker_app.nodes.job_intake import job_intake


@pytest.fixture
def store(monkeypatch):
    monkeypatch.setenv("AWS_DEFAULT_REGION", "us-east-1")
    with mock_aws():
        ddb = boto3.client("dynamodb", region_name="us-east-1")
        ddb.create_table(
            TableName="t", KeySchema=[{"AttributeName": "analysis_id", "KeyType": "HASH"}],
            AttributeDefinitions=[{"AttributeName": "analysis_id", "AttributeType": "S"}],
            BillingMode="PAY_PER_REQUEST",
        )
        yield AnalysisStore(table_name="t")

def test_job_intake_writes_running_status(store):
    state = {"analysis_id": "a1", "repository": "acme/widgets", "issue_number": 42, "notes": None,
             "tool_call_trace": [], "warnings": []}
    result = job_intake(state, store)
    assert result["status"] == "running"
    assert store.get("a1").status == "running"

def test_job_intake_is_idempotent_on_redelivery(store):
    state = {"analysis_id": "a1", "repository": "acme/widgets", "issue_number": 42, "notes": None,
              "tool_call_trace": [], "warnings": []}
    job_intake(state, store)
    result = job_intake(state, store)  # simulates SQS redelivery
    assert result["status"] == "running"
