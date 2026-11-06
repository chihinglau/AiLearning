from functools import lru_cache
from typing import List

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """应用配置，全部可通过环境变量或 .env 覆盖。"""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "AiLearning API"
    app_env: str = "dev"
    debug: bool = True
    api_prefix: str = "/api"

    database_url: str = "sqlite:///./ailearning_dev.db"
    auto_create_tables: bool = False

    jwt_secret: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 120

    study_curfew_start: int = 22
    study_curfew_end: int = 6
    default_daily_limit_minutes: int = 120

    cors_origins: List[str] = ["http://localhost:3000"]

    # P2-06 AI 讲解：默认关闭外部 LLM（走规则兜底），生产按需开启
    llm_enabled: bool = False
    llm_api_key: str = ""
    llm_base_url: str = "https://api.openai.com/v1"
    llm_model: str = "gpt-4o-mini"
    llm_timeout_seconds: float = 20.0
    ai_max_input_chars: int = 300
    ai_max_output_chars: int = 1200
    ai_rate_limit_per_hour: int = 20


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
