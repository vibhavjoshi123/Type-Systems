"""Configuration management for Hypergraph Context Graph."""

from __future__ import annotations

from pydantic import Field
from pydantic_settings import BaseSettings


class TypeDBSettings(BaseSettings):
    """TypeDB 3.x connection settings (supports Core and Cloud)."""

    address: str = Field(
        default="localhost:1729",
        alias="TYPEDB_ADDRESS",
        description="TypeDB server address (host:port or cloud URL)",
    )
    database: str = Field(default="context_graph", alias="TYPEDB_DATABASE")
    username: str = Field(default="admin", alias="TYPEDB_USERNAME")
    password: str = Field(default="password", alias="TYPEDB_PASSWORD")
    tls_enabled: bool = Field(
        default=False,
        alias="TYPEDB_TLS_ENABLED",
        description="Enable TLS (required for TypeDB Cloud)",
    )
    tls_root_ca: str | None = Field(
        default=None,
        alias="TYPEDB_TLS_ROOT_CA",
        description="Path to TLS root CA certificate",
    )

    model_config = {
        "env_prefix": "TYPEDB_",
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "extra": "ignore",
    }


class LLMSettings(BaseSettings):
    """LLM provider settings."""

    anthropic_api_key: str | None = Field(default=None, alias="LLM_ANTHROPIC_API_KEY")
    openai_api_key: str | None = Field(default=None, alias="LLM_OPENAI_API_KEY")
    default_provider: str = Field(default="anthropic", alias="LLM_DEFAULT_PROVIDER")
    default_model: str = Field(default="claude-sonnet-4-20250514", alias="LLM_DEFAULT_MODEL")
    max_tokens: int = Field(default=4096, alias="LLM_MAX_TOKENS")
    temperature: float = Field(default=0.0, alias="LLM_TEMPERATURE")

    model_config = {
        "env_prefix": "LLM_",
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "extra": "ignore",
    }


class ConnectorSettings(BaseSettings):
    """Enterprise connector settings."""

    salesforce_username: str | None = Field(default=None, alias="CONNECTOR_SALESFORCE_USERNAME")
    salesforce_password: str | None = Field(default=None, alias="CONNECTOR_SALESFORCE_PASSWORD")
    salesforce_token: str | None = Field(default=None, alias="CONNECTOR_SALESFORCE_TOKEN")
    slack_bot_token: str | None = Field(default=None, alias="CONNECTOR_SLACK_BOT_TOKEN")
    pagerduty_api_key: str | None = Field(default=None, alias="CONNECTOR_PAGERDUTY_API_KEY")

    model_config = {
        "env_prefix": "CONNECTOR_",
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "extra": "ignore",
    }


class APISettings(BaseSettings):
    """FastAPI application settings."""

    host: str = Field(default="0.0.0.0", alias="API_HOST")
    port: int = Field(default=8000, alias="API_PORT")
    debug: bool = Field(default=False, alias="API_DEBUG")
    cors_origins: list[str] = Field(default=["*"], alias="API_CORS_ORIGINS")
    api_key: str | None = Field(default=None, alias="API_KEY")
    rate_limit_rpm: int = Field(default=120, alias="API_RATE_LIMIT_RPM")
    log_format: str = Field(default="text", alias="LOG_FORMAT")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")

    model_config = {
        "env_prefix": "API_",
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "extra": "ignore",
    }


class Settings(BaseSettings):
    """Root settings aggregating all configuration."""

    typedb: TypeDBSettings = Field(default_factory=TypeDBSettings)
    llm: LLMSettings = Field(default_factory=LLMSettings)
    connectors: ConnectorSettings = Field(default_factory=ConnectorSettings)
    api: APISettings = Field(default_factory=APISettings)

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "extra": "ignore"}


def get_settings() -> Settings:
    """Create and return application settings."""
    return Settings()
