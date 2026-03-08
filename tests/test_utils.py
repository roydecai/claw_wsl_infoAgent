"""测试工具模块"""

import pytest
from datetime import datetime, timedelta
from info_gatherer.utils.cache import CacheManager
from info_gatherer.utils.retry import with_retry


class TestCacheManager:
    """测试缓存管理器"""

    def test_init_creates_directory(self, tmp_path):
        """测试初始化创建缓存目录"""
        cache_dir = tmp_path / "test_cache"
        _ = CacheManager(cache_dir)
        assert cache_dir.exists()

    def test_set_and_get(self, tmp_path):
        """测试设置和获取缓存"""
        cache_dir = tmp_path / "test_cache"
        manager = CacheManager(cache_dir)
        
        manager.set("key1", {"data": "value"})
        result = manager.get("key1")
        
        assert result == {"data": "value"}

    def test_get_nonexistent_key_returns_none(self, tmp_path):
        """测试获取不存在的键返回 None"""
        cache_dir = tmp_path / "test_cache"
        manager = CacheManager(cache_dir)
        
        result = manager.get("nonexistent")
        assert result is None

    def test_delete_removes_cache(self, tmp_path):
        """测试删除缓存"""
        cache_dir = tmp_path / "test_cache"
        manager = CacheManager(cache_dir)
        
        manager.set("key1", {"data": "value"})
        manager.delete("key1")
        
        result = manager.get("key1")
        assert result is None

    def test_clear_removes_all(self, tmp_path):
        """测试清空所有缓存"""
        cache_dir = tmp_path / "test_cache"
        manager = CacheManager(cache_dir)
        
        manager.set("key1", {"data": "1"})
        manager.set("key2", {"data": "2"})
        manager.clear()
        
        assert manager.get("key1") is None
        assert manager.get("key2") is None

    def test_expired_cache_returns_none(self, tmp_path):
        """测试过期缓存返回 None"""
        cache_dir = tmp_path / "test_cache"
        manager = CacheManager(cache_dir)
        
        # 设置一个立即过期的值（通过修改文件时间）
        manager.set("key1", {"data": "value"})
        cache_file = list(cache_dir.glob("*.json"))[0]
        
        # 修改文件时间为很久以前
        old_time = datetime.now() - timedelta(days=365)
        old_timestamp = old_time.timestamp()
        import os
        os.utime(cache_file, (old_timestamp, old_timestamp))
        
        result = manager.get("key1")
        assert result is None


class TestRetryDecorator:
    """测试重试装饰器"""

    @pytest.mark.asyncio
    async def test_success_no_retry(self):
        """测试成功时不重试"""
        call_count = 0
        
        @with_retry(max_retries=2, delay=0.01)
        async def success_func():
            nonlocal call_count
            call_count += 1
            return "success"
        
        result = await success_func()
        assert result == "success"
        assert call_count == 1

    @pytest.mark.asyncio
    async def test_retry_on_failure(self):
        """测试失败时重试"""
        call_count = 0
        
        @with_retry(max_retries=2, delay=0.01)
        async def fail_func():
            nonlocal call_count
            call_count += 1
            raise ValueError("test error")
        
        with pytest.raises(ValueError):
            await fail_func()
        
        assert call_count == 3  # 初始 + 2次重试

    @pytest.mark.asyncio
    async def test_retry_then_success(self):
        """测试重试后成功"""
        call_count = 0
        
        @with_retry(max_retries=2, delay=0.01)
        async def eventually_success():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise ValueError("not yet")
            return "success"
        
        result = await eventually_success()
        assert result == "success"
        assert call_count == 2

    def test_sync_function_retry(self):
        """测试同步函数重试"""
        call_count = 0
        
        @with_retry(max_retries=2, delay=0.01)
        def sync_fail():
            nonlocal call_count
            call_count += 1
            raise ValueError("sync error")
        
        with pytest.raises(ValueError):
            sync_fail()
        
        assert call_count == 3

    @pytest.mark.asyncio
    async def test_specific_exception_filter(self):
        """测试特定异常过滤"""
        call_count = 0
        
        @with_retry(max_retries=2, delay=0.01, exceptions=(ValueError,))
        async def raise_different_errors():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise TypeError("type error")  # 不应重试
            raise ValueError("value error")
        
        with pytest.raises(TypeError):
            await raise_different_errors()
        
        assert call_count == 1  # 不重试 TypeError
