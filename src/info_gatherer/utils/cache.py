"""缓存管理"""

import json
import time
from pathlib import Path
from typing import Any, Optional
import structlog

from ..config import get_settings

logger = structlog.get_logger(__name__)


class CacheManager:
    """缓存管理器"""
    
    def __init__(self, cache_dir: Optional[Path] = None):
        """
        初始化缓存管理器
        
        Args:
            cache_dir: 缓存目录，默认为 ~/.cache/info_gatherer
        """
        self.settings = get_settings()
        
        if cache_dir:
            self.cache_dir = cache_dir
        else:
            from pathlib import Path
            home = Path.home()
            self.cache_dir = home / ".cache" / "info_gatherer"
        
        # 确保目录存在
        self.cache_dir.mkdir(parents=True, exist_ok=True)
    
    def get(self, key: str) -> Optional[Any]:
        """
        获取缓存
        
        Args:
            key: 缓存键
            
        Returns:
            缓存值，如果不存在或已过期返回 None
        """
        if not self.settings.cache_enabled:
            return None
        
        cache_file = self._get_cache_file(key)
        
        if not cache_file.exists():
            return None
        
        try:
            # 检查是否过期
            mtime = cache_file.stat().st_mtime
            age = time.time() - mtime
            
            if age > self.settings.cache_ttl_seconds:
                cache_file.unlink()
                return None
            
            # 读取缓存
            with open(cache_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                logger.debug("cache_hit", key=key)
                return data.get('value')
                
        except Exception as e:
            logger.warning("cache_read_failed", key=key, error=str(e))
            return None
    
    def set(self, key: str, value: Any) -> None:
        """
        设置缓存
        
        Args:
            key: 缓存键
            value: 缓存值
        """
        if not self.settings.cache_enabled:
            return
        
        cache_file = self._get_cache_file(key)
        
        try:
            data = {
                'key': key,
                'value': value,
                'created_at': time.time()
            }
            
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
                
            logger.debug("cache_set", key=key)
            
        except Exception as e:
            logger.warning("cache_write_failed", key=key, error=str(e))
    
    def delete(self, key: str) -> None:
        """删除缓存"""
        cache_file = self._get_cache_file(key)
        if cache_file.exists():
            cache_file.unlink()
            logger.debug("cache_deleted", key=key)
    
    def clear(self) -> None:
        """清空所有缓存"""
        for cache_file in self.cache_dir.glob("*.json"):
            cache_file.unlink()
        logger.info("cache_cleared")
    
    def _get_cache_file(self, key: str) -> Path:
        """获取缓存文件路径"""
        # 使用安全的文件名
        safe_key = "".join(c if c.isalnum() or c in "._-" else "_" for c in key)
        return self.cache_dir / f"{safe_key[:50]}.json"
