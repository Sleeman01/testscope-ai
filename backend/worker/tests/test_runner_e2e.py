from unittest.mock import AsyncMock, patch

import boto3
import pytest
from config import get_settings
from dynamodb import AnalysisStore
from moto import mock_aws

from app.runner import run_analysis


@pytest.fixture
def full_env(tmp_path, monkeypatch):
    # get_settings.cache_clear() before AND after — see test_runner.py's comment for the
    # test-ordering bug this fixes (get_settings is @lru_cache'd process-wide).
    monkeypatch.setenv("AWS_DEFAULT_REGION", "us-east-1")
    monkeypatch.setenv("DYNAMODB_TABLE", "testscope-analyses-test")
    monkeypatch.setenv("S3_BUCKET", "testscope-reports-test")
    monkeypatch.setenv("SQS_QUEUE_URL", "unused-in-this-test")
    monkeypatch.setenv("MCP_TEST_ANALYSIS_URL", "http://localhost:8198/mcp")
    monkeypatch.setenv("MCP_GITHUB_URL", "http://localhost:8197/mcp")  # stub, see conftest.py note
    monkeypatch.setenv("WORKSPACE_ROOT", str(tmp_path / "workspace_root"))
    monkeypatch.setenv("GITHUB_TOKEN", "unused")
    get_settings.cache_clear()
    with mock_aws():
        ddb = boto3.client("dynamodb", region_name="us-east-1")
        ddb.create_table(
            TableName="testscope-analyses-test", KeySchema=[{"AttributeName": "analysis_id", "KeyType": "HASH"}],
            AttributeDefinitions=[{"AttributeName": "analysis_id", "AttributeType": "S"}],
            BillingMode="PAY_PER_REQUEST",
        )
        s3 = boto3.client("s3", region_name="us-east-1")
        s3.create_bucket(Bucket="testscope-reports-test")
        yield
    get_settings.cache_clear()

@pytest.mark.asyncio
async def test_full_pipeline_reaches_completed_status(full_env):
    # LLM calls are stubbed end-to-end (no real Claude call); MCP calls to mcp-test-analysis
    # hit the real mcp-server subprocess (conftest.py), which itself hits moto-mocked AWS
    # for job_intake/runner's own upserts (in-process) — but NOT for report_saver's
    # save_coverage_report call, which crosses into that separate subprocess; moto's
    # mock_aws() only patches boto3 within this test process, not a spawned subprocess, so
    # that specific call is expected to fail there. That's fine: report_saver treats a save
    # failure as non-fatal by design (Task 17), so the pipeline still reaches "completed".
    stub_llm_by_tool = {
        "extract_requirement": {"feature_name": "Login", "business_objective": "auth", "functional_requirements": [],
                                 "acceptance_criteria": [{"id": "AC1", "text": "Invalid password returns 401"}],
                                 "validation_rules": [], "user_roles": [], "constraints": [], "gaps": []},
        "generate_keywords": {"keywords": ["login"]},
        "classify_coverage": [{"criterion_id": "AC1", "status": "Not covered", "evidence": [], "explanation": "no matching test"}],
        "generate_test_plan": [],
        "recommend_missing_tests": [{"behavior": "401 on bad password", "why_it_matters": "security",
                                       "suggested_type": "negative", "suggested_priority": "high",
                                       "related_criterion_id": "AC1", "risk": "unauthorized access"}],
    }
    async def fake_call_llm(system_prompt, user_prompt, response_model, tool_name):
        return response_model.model_validate(stub_llm_by_tool[tool_name])

    # Task 11 redesigned request_validator/requirement_retriever against design.md §5.2's
    # substitute-tool table (get_repository/get_issue/get_issue_comments never existed on the
    # real mcp-github server) — these fakes match that real implementation, not plan.md's
    # placeholder tool names.
    async def fake_search_repositories(tool_name, **kwargs):
        assert tool_name == "search_repositories"
        return {"items": [{"default_branch": "main", "size": 100}]}

    async def fake_fetch_issue_body(owner, repo, issue_number, github_token=None):
        return "Users must be rejected with 401 on invalid password."

    async def fake_issue_read_comments(tool_name, **kwargs):
        assert tool_name == "issue_read"
        # Bare list, matching the real server's confirmed shape (design.md §5.2) — not
        # {"comments": [...]}, which requirement_retriever.py incorrectly assumed until the
        # Task 43 fix (this stub encoded the same wrong assumption).
        return []

    # unittest.mock.patch replaces an attribute on the module it's given — it does NOT
    # retroactively change a name already imported elsewhere via `from x import y` (each
    # node module bound its own local reference to call_llm/call_github_tool at import
    # time). Patching app.llm_client.call_llm or app.mcp_clients.call_github_tool directly
    # (as plan.md's own snippet does) has no effect on any node's calls — confirmed by
    # running it that way first and observing real (failing) Anthropic/MCP calls instead of
    # the stubs. Every node that imports these must be patched at its own import site.
    with patch("app.nodes.requirement_parser.call_llm", new=AsyncMock(side_effect=fake_call_llm)), \
         patch("app.nodes.test_search_planner.call_llm", new=AsyncMock(side_effect=fake_call_llm)), \
         patch("app.nodes.coverage_analyzer.call_llm", new=AsyncMock(side_effect=fake_call_llm)), \
         patch("app.nodes.test_plan_generator.call_llm", new=AsyncMock(side_effect=fake_call_llm)), \
         patch("app.nodes.missing_test_recommender.call_llm", new=AsyncMock(side_effect=fake_call_llm)), \
         patch("app.nodes.request_validator.call_github_tool", new=AsyncMock(side_effect=fake_search_repositories)), \
         patch("app.nodes.requirement_retriever._fetch_issue_body", new=AsyncMock(side_effect=fake_fetch_issue_body)), \
         patch("app.nodes.requirement_retriever.call_github_tool", new=AsyncMock(side_effect=fake_issue_read_comments)):
        await run_analysis(analysis_id="e2e-1", repository="acme/widgets", issue_number=42, notes=None)

    store = AnalysisStore(table_name="testscope-analyses-test")
    record = store.get("e2e-1")
    assert record.status == "completed"
    assert record.missing_tests_count == 1
    # storage_status is deterministically "failed" here: the mcp-server subprocess's real,
    # unmocked save_coverage_report call gets conftest.py's forced fake AWS credentials,
    # so it's always rejected — proves both (a) storage_status now actually propagates
    # from report_saver through to the persisted record (it didn't before AgentState
    # declared the field — see state.py) and (b) report_saver's failure handling is
    # correctly non-fatal (status is still "completed" despite the save failing).
    assert record.storage_status == "failed"
