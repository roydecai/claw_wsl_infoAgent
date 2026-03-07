"""收集器模块"""

from .base import BaseCollector
from .web_search import WebSearchCollector
from .web_fetch import WebFetchCollector
from .local_search import LocalSearchCollector

__all__ = [
    "BaseCollector",
    "WebSearchCollector", 
    "WebFetchCollector",
    "LocalSearchCollector",
]
