import boto3
import pytest
from moto import mock_aws
from sqs import JobQueue

@pytest.fixture
def queue(monkeypatch):
    monkeypatch.setenv("AWS_DEFAULT_REGION", "us-east-1")
    with mock_aws():
        sqs = boto3.client("sqs", region_name="us-east-1")
        queue_url = sqs.create_queue(QueueName="jobs")["QueueUrl"]
        yield JobQueue(queue_url=queue_url)

def test_send_job_then_receive_jobs_returns_the_same_body(queue):
    queue.send_job(analysis_id="a1", repository="acme/widgets", issue_number=42, notes="check login")
    messages = queue.receive_jobs(max_messages=1, wait_seconds=0)
    assert len(messages) == 1
    assert messages[0]["body"] == {
        "analysis_id": "a1", "repository": "acme/widgets", "issue_number": 42, "notes": "check login",
    }

def test_delete_message_empties_the_queue(queue):
    queue.send_job(analysis_id="a1", repository="acme/widgets", issue_number=42, notes=None)
    messages = queue.receive_jobs(max_messages=1, wait_seconds=0)
    queue.delete_message(messages[0]["receipt_handle"])
    assert queue.receive_jobs(max_messages=1, wait_seconds=0) == []
