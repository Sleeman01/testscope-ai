from functools import lru_cache
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    env: str = "dev"
    dynamodb_table: str
    s3_bucket: str
    sqs_queue_url: str
    mcp_github_url: str
    mcp_test_analysis_url: str
    anthropic_api_key: str = ""
    anthropic_model: str = "claude-sonnet-4-5-20250929"

@lru_cache
def get_settings() -> Settings:
    return Settings()
