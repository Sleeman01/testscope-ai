import os

import boto3


def get_dynamodb_table():
    return boto3.resource("dynamodb").Table(get_table_name())

def get_s3_client():
    return boto3.client("s3")

def get_table_name() -> str:
    return os.environ["DYNAMODB_TABLE"]

def get_s3_bucket_name() -> str:
    return os.environ["S3_BUCKET"]
