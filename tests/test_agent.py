import asyncio

from info_gatherer.agent import InfoGathererAgent
from info_gatherer.models import GatherRequest, InfoItem, SourceType


class DummyCollector:
    def __init__(self, source_type: SourceType, items=None, should_fail=False):
        self.source_type = source_type
        self.items = items or []
        self.should_fail = should_fail

    async def collect(self, query: str, max_results: int = 10):
        if self.should_fail:
            raise RuntimeError("collector failed")
        return self.items[:max_results]


def test_collect_counts_errors_and_merges_results():
    agent = InfoGathererAgent()
    agent.collectors = {
        SourceType.WEB_SEARCH: DummyCollector(
            SourceType.WEB_SEARCH,
            items=[
                InfoItem(
                    id="1",
                    title="Python Asyncio",
                    source="test",
                    source_type=SourceType.WEB_SEARCH,
                    content="asyncio event loop",
                )
            ],
        ),
        SourceType.WEB_FETCH: DummyCollector(SourceType.WEB_FETCH, should_fail=True),
    }

    request = GatherRequest(
        query="python asyncio",
        max_results=5,
        sources=[SourceType.WEB_SEARCH, SourceType.WEB_FETCH],
    )

    items, error_count = asyncio.run(agent._collect(request))

    assert len(items) == 1
    assert error_count == 1


def test_gather_sets_total_and_dedup_count():
    repeated = InfoItem(
        id="a",
        title="A",
        source="test",
        source_type=SourceType.WEB_SEARCH,
        content="same content",
    )
    agent = InfoGathererAgent()
    agent.collectors = {
        SourceType.WEB_SEARCH: DummyCollector(
            SourceType.WEB_SEARCH,
            items=[repeated, repeated.model_copy(update={"id": "b"})],
        )
    }

    request = GatherRequest(query="same", max_results=10, sources=[SourceType.WEB_SEARCH])
    result = asyncio.run(agent.gather(request))

    assert result.total_count == 2
    assert result.dedup_count == 1
    assert len(result.items) == 1
