import json

import boto3


class ReportStore:
    def __init__(self, bucket: str):
        self._bucket = bucket
        self._client = boto3.client("s3")

    def presigned_url(self, s3_key: str, expires_in: int = 300) -> str:
        return self._client.generate_presigned_url(
            "get_object", Params={"Bucket": self._bucket, "Key": s3_key}, ExpiresIn=expires_in,
        )

    def read_json(self, s3_key: str) -> dict:
        body = self._client.get_object(Bucket=self._bucket, Key=s3_key)["Body"].read()
        return json.loads(body)
