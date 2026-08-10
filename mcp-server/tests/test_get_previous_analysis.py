from decimal import Decimal

import boto3
import pytest
from moto import mock_aws


@pytest.fixture
def table_with_gsi(monkeypatch):
    monkeypatch.setenv("AWS_DEFAULT_REGION", "us-east-1")
    monkeypatch.setenv("DYNAMODB_TABLE", "testscope-analyses-test")
    with mock_aws():
        ddb = boto3.client("dynamodb", region_name="us-east-1")
        ddb.create_table(
            TableName="testscope-analyses-test",
            KeySchema=[{"AttributeName": "analysis_id", "KeyType": "HASH"}],
            AttributeDefinitions=[
                {"AttributeName": "analysis_id", "AttributeType": "S"},
                {"AttributeName": "repository_issue", "AttributeType": "S"},
                {"AttributeName": "created_at", "AttributeType": "S"},
            ],
            BillingMode="PAY_PER_REQUEST",
            GlobalSecondaryIndexes=[{
                "IndexName": "repository_issue-index",
                "KeySchema": [
                    {"AttributeName": "repository_issue", "KeyType": "HASH"},
                    {"AttributeName": "created_at", "KeyType": "RANGE"},
                ],
                "Projection": {"ProjectionType": "ALL"},
            }],
        )
        table = boto3.resource("dynamodb", region_name="us-east-1").Table("testscope-analyses-test")
        table.put_item(Item={"analysis_id": "a1", "repository_issue": "acme/widgets#42", "created_at": "2026-01-01T00:00:00Z", "status": "completed", "coverage_summary": {"percent_covered": Decimal("80.0")}, "s3_report_key": "acme/widgets/42/a1.json"})
        table.put_item(Item={"analysis_id": "a2", "repository_issue": "acme/widgets#42", "created_at": "2026-01-02T00:00:00Z", "status": "completed", "coverage_summary": {"percent_covered": Decimal("90.0")}, "s3_report_key": "acme/widgets/42/a2.json"})
        yield

def test_returns_analyses_newest_first(table_with_gsi):
    from tools.get_previous_analysis import get_previous_analysis
    result = get_previous_analysis("acme/widgets", 42)
    ids = [a["analysis_id"] for a in result["analyses"]]
    assert ids == ["a2", "a1"]
