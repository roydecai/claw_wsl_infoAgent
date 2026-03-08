"""配置管理"""

from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """应用配置"""
    
    # 并发配置
    max_concurrent_requests: int = 5
    request_timeout_seconds: int = 30
    
    # 缓存配置
    cache_enabled: bool = True
    cache_ttl_seconds: int = 3600
    
    # 重试配置
    max_retries: int = 3
    retry_delay_seconds: float = 1.0
    
    # 输出配置
    default_output_format: str = "markdown"
    max_summary_length: int = 500
    
    # 搜索配置
    tavily_api_key: str = ""
    
    # 日志配置
    log_level: str = "INFO"
    
    model_config = SettingsConfigDict(
        env_prefix="INFO_GATHERER_",
        env_file=".env",
        env_file_encoding="utf-8",
    )


@lru_cache
def get_settings() -> Settings:
    """获取配置单例"""
    return Settings()
