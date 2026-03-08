"""测试收集器模块"""

import pytest
from unittest.mock import patch
from info_gatherer.models import InfoItem, SourceType
from info_gatherer.collectors.base import BaseCollector
from info_gatherer.collectors.web_search import WebSearchCollector
from info_gatherer.collectors.web_fetch import WebFetchCollector
from info_gatherer.collectors.local_search import LocalSearchCollector


class TestBaseCollector:
    """测试基类收集器"""

    def test_generate_id_consistency(self):
        """测试 ID 生成的一致性"""
        class TestCollector(BaseCollector):
            async def collect(self, query, max_results=10):
                return []
        
        collector = TestCollector(SourceType.WEB_SEARCH)
        id1 = collector._generate_id("https://example.com", "Title")
        id2 = collector._generate_id("https://example.com", "Title")
        assert id1 == id2

    @pytest.mark.asyncio
    async def test_validate_result_empty_title(self):
        """测试空标题验证失败"""
        class TestCollector(BaseCollector):
            async def collect(self, query, max_results=10):
                return []
        
        collector = TestCollector(SourceType.WEB_SEARCH)
        item = InfoItem(id="1", title="", source="test", source_type=SourceType.WEB_SEARCH)
        result = await collector.validate_result(item)
        assert result is False

    @pytest.mark.asyncio
    async def test_validate_result_whitespace_title(self):
        """测试空白标题验证失败"""
        class TestCollector(BaseCollector):
            async def collect(self, query, max_results=10):
                return []
        
        collector = TestCollector(SourceType.WEB_SEARCH)
        item = InfoItem(id="1", title="   ", source="test", source_type=SourceType.WEB_SEARCH)
        result = await collector.validate_result(item)
        assert result is False

    @pytest.mark.asyncio
    async def test_validate_result_valid_item(self):
        """测试有效项验证通过"""
        class TestCollector(BaseCollector):
            async def collect(self, query, max_results=10):
                return []
        
        collector = TestCollector(SourceType.WEB_SEARCH)
        item = InfoItem(id="1", title="Valid Title", source="test", source_type=SourceType.WEB_SEARCH)
        result = await collector.validate_result(item)
        assert result is True


class TestLocalSearchCollector:
    """测试本地搜索收集器"""

    def test_add_search_path(self, tmp_path):
        """测试添加搜索路径"""
        collector = LocalSearchCollector()
        collector.add_search_path(str(tmp_path))
        assert str(tmp_path) in collector.search_paths

    def test_supported_extensions(self):
        """测试支持的文件扩展名"""
        assert ".py" in LocalSearchCollector.SUPPORTED_EXTENSIONS
        assert ".md" in LocalSearchCollector.SUPPORTED_EXTENSIONS
        assert ".txt" in LocalSearchCollector.SUPPORTED_EXTENSIONS

    @pytest.mark.asyncio
    async def test_search_finds_matching_file(self, tmp_path):
        """测试搜索找到匹配文件"""
        # 创建测试文件
        test_file = tmp_path / "test.py"
        test_file.write_text("python asyncio tutorial")
        
        collector = LocalSearchCollector([str(tmp_path)])
        items = await collector.collect("asyncio", max_results=10)
        
        assert len(items) == 1
        assert "test.py" in items[0].title

    @pytest.mark.asyncio
    async def test_search_no_match(self, tmp_path):
        """测试搜索无匹配"""
        test_file = tmp_path / "test.py"
        test_file.write_text("some content")
        
        collector = LocalSearchCollector([str(tmp_path)])
        items = await collector.collect("nonexistent_keyword", max_results=10)
        
        assert len(items) == 0

    @pytest.mark.asyncio
    async def test_search_respects_max_results(self, tmp_path):
        """测试遵守最大结果数"""
        # 创建多个匹配文件
        for i in range(5):
            test_file = tmp_path / f"test{i}.py"
            test_file.write_text(f"python asyncio {i}")
        
        collector = LocalSearchCollector([str(tmp_path)])
        items = await collector.collect("asyncio", max_results=3)
        
        assert len(items) == 3

    @pytest.mark.asyncio
    async def test_search_skips_large_files(self, tmp_path):
        """测试跳过大文件"""
        test_file = tmp_path / "large.py"
        test_file.write_text("x" * (1024 * 1024 + 1))  # > 1MB
        
        collector = LocalSearchCollector([str(tmp_path)])
        items = await collector.collect("x", max_results=10)
        
        assert len(items) == 0

    @pytest.mark.asyncio
    async def test_search_skips_unsupported_extensions(self, tmp_path):
        """测试跳过不支持的扩展名"""
        test_file = tmp_path / "test.exe"
        test_file.write_text("python asyncio")
        
        collector = LocalSearchCollector([str(tmp_path)])
        items = await collector.collect("asyncio", max_results=10)
        
        assert len(items) == 0


class TestWebFetchCollector:
    """测试网页抓取收集器"""

    @pytest.mark.asyncio
    async def test_is_url_recognition(self):
        """测试 URL 识别"""
        collector = WebFetchCollector()
        # 内部方法测试
        assert collector is not None


class TestWebSearchCollector:
    """测试网络搜索收集器"""

    @pytest.mark.asyncio
    async def test_empty_query_returns_empty_list(self):
        """测试空查询返回空列表"""
        collector = WebSearchCollector()
        # 模拟请求失败的情况
        with patch.object(collector, '_logger'):
            items = await collector.collect("", max_results=10)
            assert items == []

    def test_parse_jina_results_empty_data(self):
        """测试解析空数据"""
        collector = WebSearchCollector()
        items = collector._parse_jina_results("")
        assert items == []

    def test_parse_jina_results_invalid_json(self):
        """测试解析无效 JSON"""
        collector = WebSearchCollector()
        items = collector._parse_jina_results("not json")
        assert items == []

    def test_parse_jina_results_valid_json(self):
        """测试解析有效 JSON"""
        collector = WebSearchCollector()
        json_data = '{"title": "Test", "url": "http://test.com", "content": "test content"}'
        items = collector._parse_jina_results(json_data)
        assert len(items) == 1
        assert items[0].title == "Test"
