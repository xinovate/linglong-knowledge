"""Tests for IngestAgent."""

import json
from datetime import date
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from linglong.ingest.agent import (
    IngestAgent,
    _dedup_results,
    _format_github,
    _format_results,
    _format_rss,
    _is_noise_url,
    _parse_opengithub_table,
)
from linglong.ingest.package import SearchQueryConfig, SourcePackage


def _make_package() -> SourcePackage:
    return SourcePackage(
        name="test-brief",
        topic="AI 早报",
        output={"format": "morning-brief"},
        search_queries=[
            SearchQueryConfig(
                keywords=["OpenAI news 2026", "Anthropic Claude latest"],
                max_results=5,
                max_age_days=3,
            ),
        ],
    )


class TestNoiseFilter:
    def test_dictionary_is_noise(self):
        assert _is_noise_url("https://www.iciba.com/word?w=open")

    def test_baidu_baike_is_noise(self):
        assert _is_noise_url("https://baike.baidu.com/item/test")

    def test_news_site_is_not_noise(self):
        assert not _is_noise_url("https://www.36kr.com/p/123456")

    def test_tech_blog_is_not_noise(self):
        assert not _is_noise_url("https://openai.com/blog/something")


class TestDedup:
    def test_removes_duplicate_urls(self):
        results = [
            {"title": "A", "url": "https://a.com/1", "snippet": ""},
            {"title": "B", "url": "https://b.com/1", "snippet": ""},
            {"title": "A2", "url": "https://a.com/1", "snippet": "dup"},
        ]
        deduped = _dedup_results(results)
        assert len(deduped) == 2

    def test_empty_list(self):
        assert _dedup_results([]) == []


class TestFormatResults:
    def test_formats_with_numbering(self):
        results = [
            {"title": "Test News", "url": "https://example.com/1", "snippet": "A test"},
        ]
        text = _format_results(results)
        assert "1. Test News" in text
        assert "https://example.com/1" in text
        assert "A test" in text

    def test_truncates_long_snippet(self):
        results = [
            {"title": "T", "url": "https://x.com", "snippet": "x" * 300},
        ]
        text = _format_results(results)
        assert len(text.split("摘要: ")[1].split("\n")[0]) <= 200


class TestIngestAgent:
    @pytest.mark.asyncio
    async def test_run_produces_output(self):
        pkg = _make_package()
        agent = IngestAgent()

        mock_search_results = [
            {"title": "OpenAI release", "url": "https://openai.com/blog/x", "snippet": "GPT-5"},
            {"title": "Claude update", "url": "https://anthropic.com/news/y", "snippet": "Opus 4"},
        ]

        with patch("linglong.ingest.agent._searxng_search", new_callable=AsyncMock, return_value=mock_search_results), \
             patch("linglong.ingest.agent._github_trending", new_callable=AsyncMock, return_value=([], "trending")), \
             patch("linglong.ingest.agent._fetch_rss_feeds", new_callable=AsyncMock, return_value=[]), \
             patch("linglong.ingest.agent._call_llm", return_value="# AI 早报 · 2026-05-25\n\nMorning brief content"):
            output = await agent.run(pkg)

        assert "AI 早报" in output

    @pytest.mark.asyncio
    async def test_run_with_no_results(self):
        pkg = _make_package()
        agent = IngestAgent()

        with patch("linglong.ingest.agent._searxng_search", new_callable=AsyncMock, return_value=[]), \
             patch("linglong.ingest.agent._github_trending", new_callable=AsyncMock, return_value=([], "trending")), \
             patch("linglong.ingest.agent._fetch_rss_feeds", new_callable=AsyncMock, return_value=[]):
            output = await agent.run(pkg)

        assert "暂无搜索结果" in output

    @pytest.mark.asyncio
    async def test_search_failure_continues(self):
        pkg = _make_package()
        agent = IngestAgent()

        async def mock_search(query, max_results=15):
            if "OpenAI" in query:
                return [{"title": "OK", "url": "https://ok.com", "snippet": "s"}]
            raise Exception("Search failed")

        with patch("linglong.ingest.agent._searxng_search", side_effect=mock_search), \
             patch("linglong.ingest.agent._github_trending", new_callable=AsyncMock, return_value=([], "trending")), \
             patch("linglong.ingest.agent._fetch_rss_feeds", new_callable=AsyncMock, return_value=[]), \
             patch("linglong.ingest.agent._call_llm", return_value="# AI 早报"):
            output = await agent.run(pkg)

        assert "AI 早报" in output

    @pytest.mark.asyncio
    async def test_preference_injection(self):
        from linglong.ingest.feedback import FeedbackStore

        pkg = _make_package()
        store = MagicMock(spec=FeedbackStore)
        store.get_preference_text.return_value = "用户偏好：funding 类型偏好"

        agent = IngestAgent(feedback_store=store)

        mock_results = [{"title": "T", "url": "https://t.com", "snippet": "s"}]

        with patch("linglong.ingest.agent._searxng_search", new_callable=AsyncMock, return_value=mock_results), \
             patch("linglong.ingest.agent._github_trending", new_callable=AsyncMock, return_value=([], "trending")), \
             patch("linglong.ingest.agent._fetch_rss_feeds", new_callable=AsyncMock, return_value=[]), \
             patch("linglong.ingest.agent._call_llm", return_value="# AI 早报") as mock_llm:
            await agent.run(pkg)

        # Verify preference text was passed to LLM
        call_args = mock_llm.call_args
        system_prompt = call_args[0][0] if call_args[0] else call_args[1].get("system", "")
        assert "偏好" in system_prompt


class TestParseOpengithub:
    def test_parses_table_rows(self):
        md = """## 日榜排行

| 排名 | 项目名 | Star⭐ | 今日增长量 |
|------|--------|--------|------------|
| 1 | [foo/bar](https://github.com/foo/bar) | 21.7k | 🔺2637 |
| 2 | [baz/qux](https://github.com/baz/qux) | 13.5k | 🔺1819 |
"""
        seen: set[str] = set()
        repos = _parse_opengithub_table(md, "日增长", 5, seen)
        assert len(repos) == 2
        assert repos[0]["title"] == "foo/bar (+2637⭐ 日增长)"
        assert repos[0]["stars"] == "21700"
        assert repos[1]["growth"] == "1819"

    def test_dedup_across_periods(self):
        md = """| 1 | [foo/bar](https://github.com/foo/bar) | 21k | 🔺1000 |"""
        seen: set[str] = set()
        r1 = _parse_opengithub_table(md, "日增长", 5, seen)
        r2 = _parse_opengithub_table(md, "周增长", 5, seen)
        assert len(r1) == 1
        assert len(r2) == 0

    def test_limit(self):
        rows = "| 1 | [r{i}](https://github.com/r{i}) | 1k | 🔺100 |"
        md = "\n".join(rows.format(i=i) for i in range(10))
        repos = _parse_opengithub_table(md, "日增长", 3, set())
        assert len(repos) == 3


class TestFormatGithub:
    def test_groups_by_period(self):
        repos = [
            {"title": "a (+100⭐ 日增长)", "url": "https://github.com/a", "snippet": "sa", "stars": "100", "growth": "100", "period": "日增长"},
            {"title": "b (+500⭐ 周增长)", "url": "https://github.com/b", "snippet": "sb", "stars": "500", "growth": "500", "period": "周增长"},
        ]
        text = _format_github(repos, "opengithubs")
        assert "### 日增长" in text
        assert "### 周增长" in text
        assert "OpenGithubs" in text


class TestFormatRss:
    def test_empty_list(self):
        assert _format_rss([]) == ""

    def test_formats_items_with_source(self):
        items = [
            {"title": "AI News", "url": "https://example.com/1", "snippet": "Summary", "source": "AIHOT"},
        ]
        text = _format_rss(items)
        assert "[AIHOT] AI News" in text
        assert "https://example.com/1" in text
        assert "Summary" in text

    def test_truncates_long_snippet(self):
        items = [
            {"title": "T", "url": "https://x.com", "snippet": "x" * 400, "source": "S"},
        ]
        text = _format_rss(items)
        # Snippet in format output is truncated to 200 chars
        assert "摘要:" in text

    def test_omits_empty_snippet(self):
        items = [
            {"title": "T", "url": "https://x.com", "snippet": "", "source": "S"},
        ]
        text = _format_rss(items)
        assert "摘要" not in text


class TestFetchRssFeeds:
    @pytest.mark.asyncio
    async def test_fetches_and_parses_rss(self):
        rss_xml = """<?xml version="1.0"?>
        <rss version="2.0">
          <channel>
            <title>Test Feed</title>
            <item>
              <title>Test Article</title>
              <link>https://example.com/article1</link>
              <description>A test article about AI</description>
            </item>
          </channel>
        </rss>"""

        mock_response = MagicMock()
        mock_response.text = rss_xml
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        config_mock = MagicMock()
        config_mock.ingest.rss_sources = [
            {"name": "TestSource", "url": "https://example.com/feed"},
        ]

        with patch("linglong.ingest.agent.httpx.AsyncClient", return_value=mock_client), \
             patch("linglong.ingest.agent.get_config", return_value=config_mock):
            from linglong.ingest.agent import _fetch_rss_feeds
            items = await _fetch_rss_feeds()

        assert len(items) == 1
        assert items[0]["title"] == "Test Article"
        assert items[0]["source"] == "TestSource"

    @pytest.mark.asyncio
    async def test_dedup_by_url(self):
        rss_xml = """<?xml version="1.0"?>
        <rss version="2.0">
          <channel>
            <title>Feed</title>
            <item>
              <title>Article A</title>
              <link>https://example.com/1</link>
              <description>Desc A</description>
            </item>
            <item>
              <title>Article B</title>
              <link>https://example.com/1</link>
              <description>Desc B</description>
            </item>
          </channel>
        </rss>"""

        mock_response = MagicMock()
        mock_response.text = rss_xml
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        config_mock = MagicMock()
        config_mock.ingest.rss_sources = [
            {"name": "S1", "url": "https://s1.com/feed"},
            {"name": "S2", "url": "https://s2.com/feed"},
        ]

        with patch("linglong.ingest.agent.httpx.AsyncClient", return_value=mock_client), \
             patch("linglong.ingest.agent.get_config", return_value=config_mock):
            from linglong.ingest.agent import _fetch_rss_feeds
            items = await _fetch_rss_feeds()

        assert len(items) == 1
        assert items[0]["title"] == "Article A"

    @pytest.mark.asyncio
    async def test_continues_on_source_failure(self):
        good_xml = """<?xml version="1.0"?>
        <rss version="2.0">
          <channel>
            <title>Good</title>
            <item>
              <title>Good Article</title>
              <link>https://good.com/1</link>
              <description>OK</description>
            </item>
          </channel>
        </rss>"""

        good_response = MagicMock()
        good_response.text = good_xml
        good_response.raise_for_status = MagicMock()

        call_count = 0

        async def mock_get(url, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise Exception("Connection failed")
            return good_response

        mock_client = AsyncMock()
        mock_client.get = mock_get
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        config_mock = MagicMock()
        config_mock.ingest.rss_sources = [
            {"name": "Bad", "url": "https://bad.com/feed"},
            {"name": "Good", "url": "https://good.com/feed"},
        ]

        with patch("linglong.ingest.agent.httpx.AsyncClient", return_value=mock_client), \
             patch("linglong.ingest.agent.get_config", return_value=config_mock):
            from linglong.ingest.agent import _fetch_rss_feeds
            items = await _fetch_rss_feeds()

        assert len(items) == 1
        assert items[0]["source"] == "Good"
