"""
化学学习助手 - 后端配置
"""
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import model_validator
from typing import Optional

# 已知的不安全默认值（生产环境必须通过 .env 覆盖）
_INSECURE_DEFAULTS = {
    "SECRET_KEY": "chemlearn-secret-key-change-in-production-2026",
    "ADMIN_PASSWORD": "admin123",
}


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore", case_sensitive=True)

    # 应用
    APP_NAME: str = "ChemLearn API"
    API_V1_PREFIX: str = "/api/v1"
    DEBUG: bool = True

    # 数据库
    DATABASE_URL: str = "sqlite+aiosqlite:///./chemlearn.db"

    # Redis缓存（可选，不配置则使用内存缓存）
    REDIS_URL: str = ""

    # JWT
    SECRET_KEY: str = "chemlearn-secret-key-change-in-production-2026"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7天

    # 内置管理员
    ADMIN_USERNAME: str = "admin"
    ADMIN_PASSWORD: str = "admin123"
    ADMIN_EMAIL: str = "admin@chemlearn.local"

    # AI 问答（OpenAI 兼容接口，可接豆包/DeepSeek）
    AI_API_BASE: str = "https://api.openai.com/v1"
    AI_API_KEY: str = ""
    AI_MODEL: str = "gpt-4o-mini"
    AI_TIMEOUT: int = 60

    # AI独立服务（拆分部署时配置，留空则使用本地AIService）
    AI_SERVICE_URL: str = ""

    # CORS
    CORS_ORIGINS: list = ["*"]

    # SMTP 邮件配置
    SMTP_HOST: str = ""
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM: str = "ChemLearn API <noreply@chemlearn.com>"
    SMTP_USE_TLS: bool = True

    @model_validator(mode="after")
    def check_production_security(self):
        """生产模式（DEBUG=False）下禁止使用默认密钥/密码，防止伪造 JWT 与默认管理员账户。"""
        if not self.DEBUG:
            if self.SECRET_KEY == _INSECURE_DEFAULTS["SECRET_KEY"]:
                raise RuntimeError(
                    "安全拦截：生产环境（DEBUG=false）仍在使用默认 SECRET_KEY。"
                    "请在 .env 中设置一个强随机密钥，例如："
                    "python -c \"import secrets; print(secrets.token_urlsafe(48))\""
                )
            if self.ADMIN_PASSWORD == _INSECURE_DEFAULTS["ADMIN_PASSWORD"]:
                raise RuntimeError(
                    "安全拦截：生产环境（DEBUG=false）仍在使用默认管理员密码 admin123，"
                    "请在 .env 中设置 ADMIN_PASSWORD。"
                )
        return self


settings = Settings()
