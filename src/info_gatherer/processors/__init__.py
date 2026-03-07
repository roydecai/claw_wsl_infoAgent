"""处理器模块"""

from .dedup import DedupProcessor
from .rank import RankProcessor
from .summarize import SummarizeProcessor

__all__ = [
    "DedupProcessor",
    "RankProcessor", 
    "SummarizeProcessor",
]
