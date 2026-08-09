import json
import boto3

class JobQueue:
    def __init__(self, queue_url: str):
        self._queue_url = queue_url
        self._client = boto3.client("sqs")

    def send_job(self, analysis_id: str, repository: str, issue_number: int, notes: str | None) -> None:
        body = {"analysis_id": analysis_id, "repository": repository, "issue_number": issue_number, "notes": notes}
        self._client.send_message(QueueUrl=self._queue_url, MessageBody=json.dumps(body))

    def receive_jobs(self, max_messages: int = 1, wait_seconds: int = 20) -> list[dict]:
        response = self._client.receive_message(
            QueueUrl=self._queue_url, MaxNumberOfMessages=max_messages, WaitTimeSeconds=wait_seconds,
        )
        return [{"body": json.loads(m["Body"]), "receipt_handle": m["ReceiptHandle"]} for m in response.get("Messages", [])]

    def delete_message(self, receipt_handle: str) -> None:
        self._client.delete_message(QueueUrl=self._queue_url, ReceiptHandle=receipt_handle)
