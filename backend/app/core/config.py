from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    environment: str = "development"

    supabase_url: str = ""
    supabase_anon_key: str = ""
    supabase_service_role_key: str = ""
    supabase_jwt_secret: str = ""

    redis_url: str = "redis://localhost:6379/0"

    anthropic_api_key: str = ""
    claude_model_fast: str = "claude-haiku-4-5-20251001"
    claude_model_smart: str = "claude-sonnet-5"

    tavily_api_key: str = ""
    exa_api_key: str = ""
    firecrawl_api_key: str = ""

    max_runs_per_user_per_day: int = 30
    max_concurrent_runs_per_user: int = 3
    default_retention_days: int = 90

    cors_origins: list[str] = ["http://localhost:3000"]


settings = Settings()
