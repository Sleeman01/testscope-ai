import boto3
import pytest
from moto import mock_aws
from models import AnalysisRecord
from dynamodb import AnalysisStore

@pytest.fixture
def store(monkeypatch):
    monkeypatch.setenv("AWS_DEFAULT_REGION", "us-east-1")
    with mock_aws():
        ddb = boto3.client("dynamodb", region_name="us-east-1")
        ddb.create_table(
            TableName="t", KeySchema=[{"AttributeName": "analysis_id", "KeyType": "HASH"}],
            AttributeDefinitions=[
                {"AttributeName": "analysis_id", "AttributeType": "S"},
                {"AttributeName": "repository_issue", "AttributeType": "S"},
                {"AttributeName": "created_at", "AttributeType": "S"},
                {"AttributeName": "gsi2_pk", "AttributeType": "S"},
            ],
            BillingMode="PAY_PER_REQUEST",
            GlobalSecondaryIndexes=[
                {"IndexName": "repository_issue-index", "KeySchema": [
                    {"AttributeName": "repository_issue", "KeyType": "HASH"},
                    {"AttributeName": "created_at", "KeyType": "RANGE"}],
                 "Projection": {"ProjectionType": "ALL"}},
                {"IndexName": "recent-index", "KeySchema": [
                    {"AttributeName": "gsi2_pk", "KeyType": "HASH"},
                    {"AttributeName": "created_at", "KeyType": "RANGE"}],
                 "Projection": {"ProjectionType": "ALL"}},
            ],
        )
        yield AnalysisStore(table_name="t")

def test_upsert_then_get_roundtrips(store):
    record = AnalysisRecord(analysis_id="a1", repository="acme/widgets", issue_number=42,
                             status="running", created_at="2026-01-01T00:00:00Z", updated_at="2026-01-01T00:00:00Z")
    store.upsert(record)
    fetched = store.get("a1")
    assert fetched.status == "running"

def test_upsert_is_idempotent_last_write_wins(store):
    r1 = AnalysisRecord(analysis_id="a1", repository="acme/widgets", issue_number=42,
                         status="running", created_at="2026-01-01T00:00:00Z", updated_at="2026-01-01T00:00:00Z")
    r2 = r1.model_copy(update={"status": "completed", "updated_at": "2026-01-01T00:05:00Z"})
    store.upsert(r1)
    store.upsert(r2)
    assert store.get("a1").status == "completed"

def test_query_by_repo_issue_orders_newest_first(store):
    for i, ts in enumerate(["2026-01-01T00:00:00Z", "2026-01-02T00:00:00Z"]):
        store.upsert(AnalysisRecord(analysis_id=f"a{i}", repository="acme/widgets", issue_number=42,
                                     status="completed", created_at=ts, updated_at=ts))
    results = store.query_by_repo_issue("acme/widgets", 42)
    assert [r.analysis_id for r in results] == ["a1", "a0"]

def test_list_recent_paginates_across_two_pages_without_skipping_or_repeating(store):
    # Regression test: an earlier version of this cursor only carried `created_at`, not
    # `analysis_id` — which DynamoDB's GSI ExclusiveStartKey requires alongside it. That
    # bug wouldn't raise on its own (the types still matched); it just made page 2 wrong.
    for i, ts in enumerate([f"2026-01-0{n}T00:00:00Z" for n in range(1, 4)]):
        store.upsert(AnalysisRecord(analysis_id=f"a{i}", repository="acme/widgets", issue_number=i,
                                     status="completed", created_at=ts, updated_at=ts))
    page1, cursor = store.list_recent(limit=2)
    assert [r.analysis_id for r in page1] == ["a2", "a1"]
    assert cursor is not None
    page2, cursor2 = store.list_recent(limit=2, cursor=cursor)
    assert [r.analysis_id for r in page2] == ["a0"]
    assert cursor2 is None

def test_upsert_coerces_float_coverage_summary_for_dynamodb(store):
    # DynamoDB's put_item rejects native Python floats outright (raises TypeError) —
    # confirmed the hard way in mcp-server's save_coverage_report/get_previous_analysis
    # (Tasks 6 & 7, see docs/project-log.md). AnalysisRecord.coverage_summary is a bare
    # dict that can carry a float straight from a fixture or LLM-produced summary, so the
    # store itself must coerce it rather than trusting every caller to pre-convert.
    record = AnalysisRecord(analysis_id="a1", repository="acme/widgets", issue_number=42,
                             status="completed", created_at="2026-01-01T00:00:00Z",
                             updated_at="2026-01-01T00:00:00Z",
                             coverage_summary={"percent_covered": 80.0})
    store.upsert(record)
    fetched = store.get("a1")
    assert fetched.coverage_summary["percent_covered"] == 80.0
