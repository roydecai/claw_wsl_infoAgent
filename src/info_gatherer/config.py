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
    max_query_length: int = 500  # query 最大长度限制
    max_response_size: int = 10 * 1024 * 1024  # 响应大小限制 10MB
    
    # 日志配置
    log_level: str = "INFO"
    
    # LLM 配置（用于智能摘要）
    llm_api_key: str = ""  # LLM API Key
    llm_base_url: str = "https://api.openai.com/v1"  # LLM API 基础URL
    llm_model: str = "gpt-4o-mini"  # 默认模型
    llm_max_tokens: int = 200  # 摘要最大token数
    llm_temperature: float = 0.3  # 生成温度
    llm_timeout_seconds: int = 10  # LLM请求超时
    
    model_config = SettingsConfigDict(
        env_prefix="INFO_GATHERER_",
        env_file=".env",
        env_file_encoding="utf-8",
    )


@lru_cache
def get_settings() -> Settings:
    """获取配置单例"""
    return Settings()
