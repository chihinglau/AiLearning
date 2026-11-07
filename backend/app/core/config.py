from functools import lru_cache
from typing import List

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """应用配置，全部可通过环境变量或 .env 覆盖。"""

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

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

    # R-02 生产化：登录/注册限流（进程内滑动窗口，单实例部署适用）
    rate_limit_enabled: bool = True
    login_rate_limit_per_minute: int = 10
    register_rate_limit_per_minute: int = 5

    # R-02 合规留存：审计日志至少保留 6 个月，默认 24 个月后清理
    audit_retention_months: int = 24

    # R-03 法务：隐私政策/用户协议公网地址（为空时按请求 Host 推导）
    legal_public_base_url: str = ""

    # R-06 备案与上架信息：备案号、软著登记号在取得后回填，App「关于」页展示
    app_display_name: str = "深爱学"
    app_version_label: str = "1.0.0"
    icp_record_no: str = ""
    app_record_no: str = ""
    software_copyright_no: str = ""
    support_email: str = "support@ailearning.cn"

    # P2-06 AI 讲解：默认关闭外部 LLM（走规则兜底），生产按需开启
    llm_enabled: bool = False
    llm_api_key: str = ""
    llm_base_url: str = "https://api.openai.com/v1"
    llm_model: str = "gpt-4o-mini"
    llm_timeout_seconds: float = 20.0
    ai_max_input_chars: int = 300
    ai_max_output_chars: int = 1200
    ai_rate_limit_per_hour: int = 20

    @property
    def is_production(self) -> bool:
        return self.app_env.strip().lower() in {"prod", "production"}


DEFAULT_JWT_SECRET = "change-me-in-production"
MIN_JWT_SECRET_LENGTH = 32


def validate_settings() -> None:
    """生产环境启动前校验：禁止默认密钥、debug、自动建表与过宽的 CORS。"""
    if not settings.is_production:
        return
    problems: list[str] = []
    if (
        settings.jwt_secret == DEFAULT_JWT_SECRET
        or len(settings.jwt_secret) < MIN_JWT_SECRET_LENGTH
    ):
        problems.append(
            f"JWT_SECRET 必须显式设置且长度 >= {MIN_JWT_SECRET_LENGTH}"
            "（当前为默认值或过短）"
        )
    if settings.debug:
        problems.append("生产环境必须设置 DEBUG=false")
    if settings.auto_create_tables:
        problems.append(
            "生产环境禁止 AUTO_CREATE_TABLES=true，请使用 alembic upgrade head"
        )
    origins = [item.strip() for item in settings.cors_origins if item.strip()]
    if not origins or "*" in origins:
        problems.append("CORS_ORIGINS 必须配置明确域名，禁止空值或通配 *")
    elif any("localhost" in item or "127.0.0.1" in item for item in origins):
        problems.append("CORS_ORIGINS 不得包含 localhost/127.0.0.1")
    if problems:
        raise RuntimeError("生产环境配置不合规：" + "；".join(problems))


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
