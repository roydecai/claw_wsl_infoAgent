"""本地文件搜索收集器"""

import os
from pathlib import Path
from typing import Optional
import structlog

from ..models import InfoItem, SourceType
from .base import BaseCollector

logger = structlog.get_logger(__name__)


class LocalSearchCollector(BaseCollector):
    """本地文件搜索收集器"""
    
    # 支持的文件扩展名
    SUPPORTED_EXTENSIONS = {
        '.txt', '.md', '.markdown',
        '.py', '.js', '.ts', '.json', '.yaml', '.yml',
        '.html', '.xml',
        '.pdf',  # 需要额外处理
    }
    
    def __init__(self, search_paths: Optional[list[str]] = None):
        super().__init__(SourceType.LOCAL_FILE)
        self.search_paths = search_paths or []
    
    def add_search_path(self, path: str) -> None:
        """添加搜索路径"""
        if os.path.exists(path):
            self.search_paths.append(path)
    
    async def collect(self, query: str, max_results: int = 10) -> list[InfoItem]:
        """
        搜索本地文件
        
        Args:
            query: 搜索关键词
            max_results: 最大结果数
            
        Returns:
            信息项列表
        """
        self._logger.info("starting_local_search", query=query, paths=self.search_paths)
        
        items = []
        keywords = query.lower().split()
        
        for search_path in self.search_paths:
            path = Path(search_path)
            if not path.exists():
                continue
            
            # 递归搜索文件
            for file_path in path.rglob('*'):
                if not file_path.is_file():
                    continue
                
                # 检查扩展名
                if file_path.suffix.lower() not in self.SUPPORTED_EXTENSIONS:
                    continue
                
                # 跳过大型文件
                if file_path.stat().st_size > 1024 * 1024:  # 1MB
                    continue
                
                # 读取并搜索内容
                try:
                    content = file_path.read_text(encoding='utf-8', errors='ignore')
                    content_lower = content.lower()
                    
                    # 检查是否包含关键词
                    if any(kw in content_lower for kw in keywords):
                        # 提取匹配的行
                        matches = self._extract_matches(content, keywords)
                        
                        item = InfoItem(
                            id=self._generate_id(str(file_path), file_path.name),
                            title=file_path.name,
                            url=str(file_path),
                            source="local",
                            source_type=self.source_type,
                            content=matches[:500],
                            summary=f"在 {file_path.parent.name}/{file_path.name} 中找到匹配",
                        )
                        items.append(item)
                        
                        if len(items) >= max_results:
                            break
                            
                except Exception as e:
                    self._logger.warning("file_read_failed", path=str(file_path), error=str(e))
                
                if len(items) >= max_results:
                    break
            
            if len(items) >= max_results:
                break
        
        self._logger.info("local_search_completed", items_found=len(items))
        return items
    
    def _extract_matches(self, content: str, keywords: list[str]) -> str:
        """提取包含关键词的行"""
        lines = content.split('\n')
        matches = []
        
        for line in lines:
            line_lower = line.lower()
            if any(kw in line_lower for kw in keywords):
                # 保留匹配的行，去除多余空白
                matched_line = ' '.join(line.split())
                matches.append(matched_line)
        
        # 返回前10个匹配行
        return '\n'.join(matches[:10])
