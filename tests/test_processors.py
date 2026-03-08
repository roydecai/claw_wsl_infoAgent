"""测试处理器模块"""

from datetime import datetime
from info_gatherer.models import InfoItem, SourceType
from info_gatherer.processors.dedup import DedupProcessor
from info_gatherer.processors.rank import RankProcessor
from info_gatherer.processors.summarize import SummarizeProcessor


class TestDedupProcessor:
    """测试去重处理器"""

    def test_empty_list_returns_empty(self):
        processor = DedupProcessor()
        result, count = processor.process([])
        assert result == []
        assert count == 0

    def test_unique_items_preserved(self):
        processor = DedupProcessor()
        items = [
            InfoItem(id="1", title="A", source="test", source_type=SourceType.WEB_SEARCH, content="content A"),
            InfoItem(id="2", title="B", source="test", source_type=SourceType.WEB_SEARCH, content="content B"),
        ]
        result, count = processor.process(items)
        assert len(result) == 2
        assert count == 0

    def test_duplicate_items_removed(self):
        processor = DedupProcessor()
        items = [
            InfoItem(id="1", title="Same Title", source="test", source_type=SourceType.WEB_SEARCH, content="same content"),
            InfoItem(id="2", title="Same Title", source="test", source_type=SourceType.WEB_SEARCH, content="same content"),
        ]
        result, count = processor.process(items)
        assert len(result) == 1
        assert count == 1

    def test_similarity_computation(self):
        processor = DedupProcessor()
        item1 = InfoItem(id="1", title="A", source="test", source_type=SourceType.WEB_SEARCH, content="hello world python")
        item2 = InfoItem(id="2", title="B", source="test", source_type=SourceType.WEB_SEARCH, content="hello world python")
        similarity = processor.compute_similarity(item1, item2)
        assert similarity == 1.0

    def test_dissimilar_content_low_similarity(self):
        processor = DedupProcessor()
        item1 = InfoItem(id="1", title="A", source="test", source_type=SourceType.WEB_SEARCH, content="python programming")
        item2 = InfoItem(id="2", title="B", source="test", source_type=SourceType.WEB_SEARCH, content="cooking recipes")
        similarity = processor.compute_similarity(item1, item2)
        assert similarity < 0.3


class TestRankProcessor:
    """测试排序处理器"""

    def test_sort_by_relevance(self):
        processor = RankProcessor()
        items = [
            InfoItem(id="1", title="A", source="test", source_type=SourceType.WEB_SEARCH, relevance_score=0.5),
            InfoItem(id="2", title="B", source="test", source_type=SourceType.WEB_SEARCH, relevance_score=0.9),
            InfoItem(id="3", title="C", source="test", source_type=SourceType.WEB_SEARCH, relevance_score=0.3),
        ]
        result = processor.process(items, "relevance")
        assert result[0].relevance_score == 0.9
        assert result[1].relevance_score == 0.5
        assert result[2].relevance_score == 0.3

    def test_sort_by_credibility(self):
        processor = RankProcessor()
        items = [
            InfoItem(id="1", title="A", source="test", source_type=SourceType.WEB_SEARCH, credibility_score=0.5),
            InfoItem(id="2", title="B", source="test", source_type=SourceType.WEB_SEARCH, credibility_score=0.9),
        ]
        result = processor.process(items, "credibility")
        assert result[0].credibility_score == 0.9

    def test_sort_by_time(self):
        processor = RankProcessor()
        now = datetime.now()
        items = [
            InfoItem(id="1", title="A", source="test", source_type=SourceType.WEB_SEARCH, fetched_at=now),
            InfoItem(id="2", title="B", source="test", source_type=SourceType.WEB_SEARCH, fetched_at=now),
        ]
        result = processor.process(items, "time")
        assert len(result) == 2

    def test_empty_list_returns_empty(self):
        processor = RankProcessor()
        result = processor.process([], "relevance")
        assert result == []

    def test_compute_relevance_score_with_title_match(self):
        processor = RankProcessor()
        item = InfoItem(
            id="1",
            title="Python Tutorial",
            source="test",
            source_type=SourceType.WEB_SEARCH,
            content="some content"
        )
        score = processor.compute_relevance_score(item, "Python")
        assert score > 0.5  # Title match should give high score

    def test_compute_relevance_score_with_content_match(self):
        processor = RankProcessor()
        item = InfoItem(
            id="1",
            title="Tutorial",
            source="test",
            source_type=SourceType.WEB_SEARCH,
            content="This is about Python programming"
        )
        score = processor.compute_relevance_score(item, "Python")
        assert score > 0.0


class TestSummarizeProcessor:
    """测试摘要处理器"""

    def test_generate_summary_short_content(self):
        processor = SummarizeProcessor(max_summary_length=100)
        content = "Short content"
        summary = processor._generate_summary(content)
        assert summary == content

    def test_generate_summary_long_content_truncated(self):
        processor = SummarizeProcessor(max_summary_length=50)
        content = "A" * 100
        summary = processor._generate_summary(content)
        assert len(summary) <= 53  # 50 + "..."

    def test_process_adds_summary(self):
        processor = SummarizeProcessor()
        items = [
            InfoItem(id="1", title="A", source="test", source_type=SourceType.WEB_SEARCH, content="Some content here"),
        ]
        result = processor.process(items)
        assert result[0].summary is not None

    def test_process_preserves_existing_summary(self):
        processor = SummarizeProcessor()
        items = [
            InfoItem(id="1", title="A", source="test", source_type=SourceType.WEB_SEARCH, content="content", summary="Existing"),
        ]
        result = processor.process(items)
        assert result[0].summary == "Existing"

    def test_generate_overview_empty_items(self):
        processor = SummarizeProcessor()
        overview = processor.generate_overview([], "query")
        assert "未找到" in overview

    def test_generate_overview_with_items(self):
        processor = SummarizeProcessor()
        items = [
            InfoItem(id="1", title="A", source="Source1", source_type=SourceType.WEB_SEARCH),
            InfoItem(id="2", title="B", source="Source1", source_type=SourceType.WEB_SEARCH),
            InfoItem(id="3", title="C", source="Source2", source_type=SourceType.WEB_SEARCH),
        ]
        overview = processor.generate_overview(items, "test query")
        assert "test query" in overview
        assert "3" in overview
        assert "2" in overview  # 2 different sources
