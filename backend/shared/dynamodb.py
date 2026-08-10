import json
from decimal import Decimal

import boto3
from boto3.dynamodb.conditions import Key

from models import AnalysisRecord


def _to_dynamodb_safe(value):
    # boto3 rejects native Python floats for numeric attributes, even nested inside a
    # dict/list (put_item raises TypeError) — round-tripping through JSON with
    # parse_float=Decimal converts every float in the structure without hand-rolling a
    # recursive walk. See test_dynamodb.py's test_upsert_coerces_float_coverage_summary_for_dynamodb.
    return json.loads(json.dumps(value), parse_float=Decimal)

class AnalysisStore:
    def __init__(self, table_name: str):
        self._table = boto3.resource("dynamodb").Table(table_name)

    def upsert(self, record: AnalysisRecord) -> None:
        item = _to_dynamodb_safe(record.model_dump())
        item["repository_issue"] = f"{record.repository}#{record.issue_number}"
        item["gsi2_pk"] = "ANALYSIS"
        self._table.put_item(Item=item)

    def get(self, analysis_id: str) -> AnalysisRecord | None:
        response = self._table.get_item(Key={"analysis_id": analysis_id})
        item = response.get("Item")
        return AnalysisRecord.model_validate(item) if item else None

    def query_by_repo_issue(self, repository: str, issue_number: int) -> list[AnalysisRecord]:
        response = self._table.query(
            IndexName="repository_issue-index",
            KeyConditionExpression=Key("repository_issue").eq(f"{repository}#{issue_number}"),
            ScanIndexForward=False,
        )
        return [AnalysisRecord.model_validate(item) for item in response["Items"]]

    def list_recent(self, limit: int, cursor: str | None = None) -> tuple[list[AnalysisRecord], str | None]:
        # A GSI query's ExclusiveStartKey must carry the GSI's own key (gsi2_pk, created_at)
        # *and* the base table's primary key (analysis_id) — DynamoDB needs all three to
        # resume correctly, even though the GSI's own key alone looks sufficient. The opaque
        # cursor therefore has to encode both created_at and analysis_id, not created_at alone.
        kwargs = {
            "IndexName": "recent-index",
            "KeyConditionExpression": Key("gsi2_pk").eq("ANALYSIS"),
            "ScanIndexForward": False, "Limit": limit,
        }
        if cursor:
            created_at, analysis_id = cursor.split("|", 1)
            kwargs["ExclusiveStartKey"] = {"gsi2_pk": "ANALYSIS", "created_at": created_at, "analysis_id": analysis_id}
        response = self._table.query(**kwargs)
        records = [AnalysisRecord.model_validate(item) for item in response["Items"]]
        last_key = response.get("LastEvaluatedKey")
        next_cursor = f"{last_key['created_at']}|{last_key['analysis_id']}" if last_key else None
        return records, next_cursor
