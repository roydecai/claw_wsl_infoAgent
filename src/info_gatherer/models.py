"""数据模型定义"""

from datetime import datetime
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field, HttpUrl


class SourceType(str, Enum):
    """信息来源类型"""
    WEB_SEARCH = "web_search"
    WEB_FETCH = "web_fetch"
    LOCAL_FILE = "local_file"
    RSS = "rss"
    API = "api"


class InfoItem(BaseModel):
    """单条信息项"""
    id: str
    title: str
    url: Optional[str] = None
    source: str
    source_type: SourceType
    content: str = ""
    summary: Optional[str] = None
    published_at: Optional[datetime] = None
    fetched_at: datetime = Field(default_factory=datetime.now)
    tags: list[str] = Field(default_factory=list)
    relevance_score: float = 0.0
    credibility_score: float = 0.5
    
    class Config:
        use_enum_values = True


class GatherRequest(BaseModel):
    """信息收集请求"""
    query: str = Field(..., description="搜索查询关键词")
    max_results: int = Field(default=10, ge=1, le=100)
    sources: list[SourceType] = Field(
        default=[SourceType.WEB_SEARCH, SourceType.WEB_FETCH],
        description="信息来源列表"
    )
    time_range: Optional[str] = Field(default=None, description="时间范围，如 '7d', '30d'")


class GatherResult(BaseModel):
    """信息收集结果"""
    request: GatherRequest
    items: list[InfoItem] = Field(default_factory=list)
    total_count: int = 0
    dedup_count: int = 0
    error_count: int = 0
    duration_seconds: float = 0.0
    
    def add_item(self, item: InfoItem) -> None:
        """添加信息项"""
        self.items.append(item)
        self.total_count += 1
