from config import get_settings

def test_get_settings_reads_required_fields_from_env(monkeypatch):
    monkeypatch.setenv("DYNAMODB_TABLE", "testscope-analyses-test")
    monkeypatch.setenv("S3_BUCKET", "testscope-reports-test")
    monkeypatch.setenv("SQS_QUEUE_URL", "https://sqs.us-east-1.amazonaws.com/123/jobs")
    monkeypatch.setenv("MCP_GITHUB_URL", "http://mcp-github:8100")
    monkeypatch.setenv("MCP_TEST_ANALYSIS_URL", "http://mcp-test-analysis:8100")
    get_settings.cache_clear()

    settings = get_settings()

    assert settings.dynamodb_table == "testscope-analyses-test"
    assert settings.s3_bucket == "testscope-reports-test"
    assert settings.env == "dev"
    assert settings.anthropic_model == "claude-sonnet-4-5-20250929"
