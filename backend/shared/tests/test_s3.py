import json
import boto3
import pytest
from moto import mock_aws
from s3 import ReportStore

@pytest.fixture
def store(monkeypatch):
    monkeypatch.setenv("AWS_DEFAULT_REGION", "us-east-1")
    with mock_aws():
        s3 = boto3.client("s3", region_name="us-east-1")
        s3.create_bucket(Bucket="testscope-reports-test")
        yield ReportStore(bucket="testscope-reports-test")

def test_presigned_url_is_generated_for_the_bucket_and_key(store):
    url = store.presigned_url("acme/widgets/42/a1.json")
    assert "testscope-reports-test" in url
    assert "acme/widgets/42/a1.json" in url

def test_read_json_roundtrips_a_put_object(store):
    payload = {"analysis_id": "a1", "coverage_summary": {"percent_covered": 80.0}}
    boto3.client("s3", region_name="us-east-1").put_object(
        Bucket="testscope-reports-test", Key="acme/widgets/42/a1.json", Body=json.dumps(payload)
    )
    assert store.read_json("acme/widgets/42/a1.json") == payload
