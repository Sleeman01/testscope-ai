import json

import boto3
import pytest
from moto import mock_aws


@pytest.fixture
def aws_env(monkeypatch):
    monkeypatch.setenv("AWS_DEFAULT_REGION", "us-east-1")
    monkeypatch.setenv("DYNAMODB_TABLE", "testscope-analyses-test")
    monkeypatch.setenv("S3_BUCKET", "testscope-reports-test")
    with mock_aws():
        ddb = boto3.client("dynamodb", region_name="us-east-1")
        ddb.create_table(
            TableName="testscope-analyses-test",
            KeySchema=[{"AttributeName": "analysis_id", "KeyType": "HASH"}],
            AttributeDefinitions=[{"AttributeName": "analysis_id", "AttributeType": "S"}],
            BillingMode="PAY_PER_REQUEST",
        )
        s3 = boto3.client("s3", region_name="us-east-1")
        s3.create_bucket(Bucket="testscope-reports-test")
        yield

def test_writes_dynamodb_item_and_s3_report(aws_env):
    from tools.save_coverage_report import save_coverage_report
    result = save_coverage_report(
        analysis_id="a1", repository="acme/widgets", issue_number=42,
        requirement={"feature_name": "Login"}, coverage_matrix=[{"criterion_id": "AC1", "status": "Covered"}],
        missing_tests=[], test_plan=[], status="completed", tool_call_trace=[],
    )
    assert result["s3_report_key"] == "acme/widgets/42/a1.json"
    assert result["dynamodb_status"] == "saved"

    import boto3
    ddb = boto3.resource("dynamodb", region_name="us-east-1")
    item = ddb.Table("testscope-analyses-test").get_item(Key={"analysis_id": "a1"})["Item"]
    assert item["status"] == "completed"
    assert item["repository"] == "acme/widgets"

    s3 = boto3.client("s3", region_name="us-east-1")
    body = s3.get_object(Bucket="testscope-reports-test", Key="acme/widgets/42/a1.json")["Body"].read()
    assert json.loads(body)["status"] == "completed"
    md = s3.get_object(Bucket="testscope-reports-test", Key="acme/widgets/42/a1.md")["Body"].read().decode()
    assert "Login" in md
