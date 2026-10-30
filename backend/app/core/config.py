from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    environment: str = "development"

    supabase_url: str = ""
    supabase_anon_key: str = ""
    supabase_service_role_key: str = ""
    supabase_jwt_secret: str = ""

    redis_url: str = "redis://localhost:6379/0"

    # AI provider selection. "gemini" and "ollama" are free; "anthropic" is
    # optional/premium and never auto-selected by the Free Basic Plan.
    ai_provider: str = "gemini"  # gemini | ollama | anthropic

    gemini_api_key: str = ""
    gemini_model: str = "gemini-2.0-flash"

    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3.2"

    anthropic_api_key: str = ""
    claude_model_fast: str = "claude-haiku-4-5-20251001"
    claude_model_smart: str = "claude-sonnet-5"

    # Search provider selection. "duckduckgo" needs no key at all.
    search_provider: str = "duckduckgo"  # duckduckgo | searxng | tavily | exa | brave
    searxng_base_url: str = ""
    tavily_api_key: str = ""
    exa_api_key: str = ""
    brave_api_key: str = ""

    # Website extraction. "local" (trafilatura/BeautifulSoup) needs no key.
    extraction_provider: str = "local"  # local | firecrawl
    firecrawl_api_key: str = ""
    jina_reader_api_key: str = ""  # optional; Jina Reader works keyless at lower limits

    max_runs_per_user_per_day: int = 30
    max_concurrent_runs_per_user: int = 3
    default_retention_days: int = 90

    database_url: str = "sqlite:///./prospectlens.db"  # local path until Supabase Postgres is configured

    cors_origins: list[str] = ["http://localhost:3000"]


settings = Settings()
