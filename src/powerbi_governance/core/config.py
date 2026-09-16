"""
Configuration management using Pydantic Settings

Centralizes all application configuration with environment variable override support.
Provides singleton access to validated settings across the application.
"""

from functools import lru_cache
from typing import Optional

from pydantic import Field, PostgresDsn, computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Application settings with environment variable override support.
    
    Settings are loaded from .env file first, then environment variables.
    Follows 12-factor app methodology.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ========================================================================
    # ENVIRONMENT
    # ========================================================================
    environment: str = Field(default="development", description="Deployment environment")
    debug: bool = Field(default=False, description="Enable debug mode")

    # ========================================================================
    # DATABASE
    # ========================================================================
    database_url: PostgresDsn = Field(
        description="SQLAlchemy database connection string"
    )
    database_pool_size: int = Field(default=10, description="Connection pool size")
    database_max_overflow: int = Field(default=20, description="Connection pool overflow")
    database_pool_recycle: int = Field(default=3600, description="Connection pool recycle time in seconds")
    database_echo: bool = Field(default=False, description="Enable SQLAlchemy SQL logging")

    # ========================================================================
    # MICROSOFT AUTHENTICATION (Service Principal)
    # ========================================================================
    azure_tenant_id: str = Field(description="Azure AD Tenant ID")
    azure_client_id: str = Field(description="Service Principal Client ID")
    azure_client_secret: str = Field(description="Service Principal Client Secret")

    # ========================================================================
    # POWER BI API
    # ========================================================================
    powerbi_api_base_url: str = Field(
        default="https://api.powerbi.com/v1.0/myorg",
        description="Power BI REST API base URL"
    )
    powerbi_admin_api_enabled: bool = Field(default=True, description="Enable Power BI Admin APIs")
    powerbi_timeout_seconds: int = Field(default=30, description="Power BI API timeout in seconds")

    # ========================================================================
    # MICROSOFT GRAPH API
    # ========================================================================
    graph_api_base_url: str = Field(
        default="https://graph.microsoft.com/v1.0",
        description="Microsoft Graph API base URL"
    )
    graph_timeout_seconds: int = Field(default=30, description="Graph API timeout in seconds")

    # ========================================================================
    # XMLA ENDPOINT
    # ========================================================================
    xmla_endpoint_enabled: bool = Field(default=True, description="Enable XMLA endpoint support")
    xmla_timeout_seconds: int = Field(default=60, description="XMLA timeout in seconds")

    # ========================================================================
    # LOGGING
    # ========================================================================
    log_level: str = Field(default="INFO", description="Logging level")
    log_format: str = Field(default="json", description="Log format (json or text)")
    log_file_enabled: bool = Field(default=True, description="Enable file logging")
    log_file_path: str = Field(default="logs/powerbi_governance.log", description="Log file path")
    log_max_bytes: int = Field(default=10485760, description="Max log file size in bytes (10MB)")
    log_backup_count: int = Field(default=5, description="Number of backup log files")

    # ========================================================================
    # RETRY POLICY
    # ========================================================================
    retry_max_attempts: int = Field(default=3, description="Maximum retry attempts")
    retry_backoff_factor: float = Field(default=2, description="Exponential backoff factor")
    retry_initial_delay: float = Field(default=1, description="Initial retry delay in seconds")

    # ========================================================================
    # SYNC JOBS
    # ========================================================================
    sync_workspaces_enabled: bool = Field(default=True, description="Enable workspace sync job")
    sync_usage_metrics_enabled: bool = Field(default=True, description="Enable usage metrics sync job")
    sync_activity_events_enabled: bool = Field(default=True, description="Enable activity events sync job")
    sync_cron_schedule: str = Field(default="0 2 * * *", description="Cron schedule for sync jobs (2 AM daily)")

    # ========================================================================
    # CACHE
    # ========================================================================
    cache_enabled: bool = Field(default=True, description="Enable caching")
    cache_ttl_seconds: int = Field(default=3600, description="Cache TTL in seconds")

    # ========================================================================
    # SECURITY
    # ========================================================================
    azure_keyvault_enabled: bool = Field(default=False, description="Enable Azure Key Vault")
    azure_keyvault_url: Optional[str] = Field(default=None, description="Azure Key Vault URL")

    @computed_field
    @property
    def is_production(self) -> bool:
        """Check if running in production"""
        return self.environment.lower() == "production"

    @computed_field
    @property
    def is_development(self) -> bool:
        """Check if running in development"""
        return self.environment.lower() == "development"

    @computed_field
    @property
    def is_testing(self) -> bool:
        """Check if running in test mode"""
        return self.environment.lower() == "testing"

    def __repr__(self) -> str:
        """Secure representation - never expose secrets"""
        return (
            f"Settings(environment={self.environment}, "
            f"debug={self.debug}, "
            f"database={self.database_url.host}, "
            f"log_level={self.log_level})"
        )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """
    Get cached singleton settings instance.
    
    Uses lru_cache to ensure only one Settings object is created,
    reducing overhead on repeated calls.
    
    Returns:
        Settings: Validated application settings instance
        
    Raises:
        ValidationError: If settings cannot be validated from environment
    """
    return Settings()
