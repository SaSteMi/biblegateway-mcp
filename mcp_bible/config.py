"""
Configuration management for Bible MCP Server

Shows how to extend core configuration classes for your service.
"""

import os
from typing import Optional, List
from pydantic import BaseModel, Field

from mcp_bible.core.config import (
    AuthentikConfig,
    BaseServerConfig,
    RedisCacheConfig,
    load_dotenv
)

# Ensure environment variables are loaded
load_dotenv()


class BibleAPIConfig(BaseModel):
    """
    Configuration for Bible API

    This shows how to add service-specific configuration
    """
    base_url: str = Field(
        default="https://www.biblegateway.com/passage/",
        description="Bible Gateway base URL"
    )
    default_version: str = Field(
        default="ESV",
        description="Default Bible version"
    )
    supported_versions: List[str] = Field(
        default=["ESV", "NIV", "KJV", "NASB", "NKJV", "NLT", "AMP", "MSG"],
        description="List of supported Bible versions (any valid BibleGateway version code is supported)"
    )
    timeout: float = Field(
        default=30.0,
        description="HTTP request timeout in seconds"
    )

    @classmethod
    def from_env(cls) -> "BibleAPIConfig":
        """Load Bible API config from environment variables"""
        base_url = os.getenv("BIBLE_API_URL", cls.model_fields["base_url"].default)
        default_version = os.getenv("BIBLE_DEFAULT_VERSION", cls.model_fields["default_version"].default)
        timeout = float(os.getenv("BIBLE_TIMEOUT", cls.model_fields["timeout"].default))

        # Parse supported versions from comma-separated string
        versions_str = os.getenv("BIBLE_SUPPORTED_VERSIONS", "")
        supported_versions = [v.strip() for v in versions_str.split(",")] if versions_str else cls.model_fields["supported_versions"].default

        return cls(
            base_url=base_url,
            default_version=default_version,
            supported_versions=supported_versions,
            timeout=timeout
        )


class ServerConfig(BaseServerConfig):
    """
    Server configuration for Bible MCP

    Extends BaseServerConfig with Bible-specific settings
    """
    mcp_only: bool = Field(
        default=False,
        description="If True, serve pure MCP protocol; if False, serve REST + MCP"
    )
    cors_origins: List[str] = Field(
        default=["http://localhost:3000", "http://localhost:8080"],
        description="List of allowed origins for CORS"
    )

    @classmethod
    def from_env(cls) -> "ServerConfig":
        """Load server configuration from environment variables"""
        config = super().from_env(env_prefix="MCP_")

        # Parse MCP_ONLY
        mcp_only = os.getenv("MCP_ONLY", "false").lower() == "true"
        config.mcp_only = mcp_only

        # Parse auth_enabled
        auth_enabled = os.getenv("MCP_AUTH_ENABLED", "false").lower() == "true"
        config.auth_enabled = auth_enabled

        # Parse CORS origins
        cors_str = os.getenv("MCP_CORS_ORIGINS", "http://localhost:3000,http://localhost:8080")
        config.cors_origins = [origin.strip() for origin in cors_str.split(",")]

        return config


class AppConfig(BaseModel):
    """
    Complete application configuration

    Aggregates all configuration sections into a single object.
    """
    server: ServerConfig
    redis_cache: RedisCacheConfig
    bible_api: BibleAPIConfig
    authentik: Optional[AuthentikConfig] = None

    @classmethod
    def from_env(cls) -> "AppConfig":
        """Load complete configuration from environment variables"""
        server = ServerConfig.from_env()
        redis_cache = RedisCacheConfig.from_env(env_prefix="MCP_")
        bible_api = BibleAPIConfig.from_env()

        # Only load Authentik config if using HTTP transport with auth enabled
        authentik = None
        if server.transport == "http" and server.auth_enabled:
            authentik = AuthentikConfig.from_env_optional()

        return cls(
            server=server,
            redis_cache=redis_cache,
            bible_api=bible_api,
            authentik=authentik
        )


# Global configuration instance
_config: Optional[AppConfig] = None


def get_config() -> AppConfig:
    """Get global application configuration"""
    global _config
    if _config is None:
        _config = AppConfig.from_env()
    return _config


def load_config() -> AppConfig:
    """Load application configuration from environment"""
    global _config
    _config = AppConfig.from_env()
    return _config