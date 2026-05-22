"""Web search source adapter — Playwright+Google or httpx+Bing CN."""

import logging
import re
from datetime import date, timedelta
from html.parser import HTMLParser
from urllib.parse import quote_plus, urlparse

import httpx

from linglong.core.config import get_config
from linglong.core.models import Entity, EntityFacet, Source, SourceType
from linglong.ingest.adapter import SourceAdapter

logger = logging.getLogger(__name__)

# Low-quality sites to exclude from results
_EXCLUDED_DOMAINS = {
    "baike.baidu.com",
    "baidu.com",
    "zdic.net",
    "wikipedia.org",
    "zhihu.com",
    "csdn.net",
    "chatgpt-chinese.com",
    "ai-bot.cn",
    "ai-kit.cn",
    "aigc.cn",
    "github-cn.com",
    "github.net.cn",
    "smapply.org",
    "apifox.com",
    "runoob.com",
    "unitconverters.net",
    "jishuzhan.net",
    "open-openai.com",
    "openaicto.com",
    "xiniushu.com",
    "claude-zh.cn",
    "apps.microsoft.com",
    "cloud.tencent.com",
    "douyin.com",
    "doubao.com",
    "deepseek.com",
    "tiangong.cn",
    "anthropic.com",
    "claude.ai",
    "claude.com",
    "github.com",
    "datawhalechina.github.io",
}


class _SearchResultParser(HTMLParser):
    """HTML parser that extracts search results from Bing CN and Google."""

    def __init__(self) -> None:
        super().__init__()
        self.results: list[dict[str, str]] = []
        self._in_result = False
        self._in_h2 = False
        self._in_h3 = False
        self._in_link = False
        self._title_buf: list[str] = []
        self._snippet_buf: list[str] = []
        self._collecting_snippet = False
        self._result_title = ""
        self._result_url = ""
        self._result_snippet = ""

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attr_dict = {k: (v or "") for k, v in attrs}
        classes = attr_dict.get("class", "")

        if tag == "li" and "b_algo" in classes:
            self._in_result = True
            self._result_title = ""
            self._result_url = ""
            self._result_snippet = ""
            return

        if not self._in_result:
            if tag == "div" and "g" in classes.split():
                self._in_result = True
                self._result_title = ""
                self._result_url = ""
                self._result_snippet = ""
            return

        if tag == "h2":
            self._in_h2 = True
            self._title_buf = []

        if tag == "h3":
            self._in_h3 = True
            self._title_buf = []

        if tag in ("a", "cite") and "href" in attr_dict:
            href = attr_dict["href"]
            if href.startswith("http") and not self._result_url:
                self._result_url = href
                self._in_link = True
                self._title_buf = []

        if tag == "p" and self._result_title:
            self._collecting_snippet = True
            self._snippet_buf = []

        if tag in ("div", "span") and self._result_title:
            snippet_classes = {"b_caption", "b_lineclamp", "VwiC3b", "IsZvec"}
            if snippet_classes & set(classes.split()):
                self._collecting_snippet = True
                self._snippet_buf = []

    def handle_endtag(self, tag: str) -> None:
        if tag == "h2" and self._in_h2:
            self._in_h2 = False
            title = " ".join(t for t in self._title_buf if t).strip()
            if title and not self._result_title:
                self._result_title = _clean_title(title)

        if tag == "h3" and self._in_h3:
            self._in_h3 = False
            title = " ".join(t for t in self._title_buf if t).strip()
            if title and not self._result_title:
                self._result_title = _clean_title(title)

        if tag == "a" and self._in_link:
            self._in_link = False
            if not self._result_title:
                title = " ".join(t for t in self._title_buf if t).strip()
                if title:
                    self._result_title = _clean_title(title)

        if tag == "p" and self._collecting_snippet:
            self._collecting_snippet = False
            snippet = " ".join(t for t in self._snippet_buf if t).strip()
            if snippet and len(snippet) > len(self._result_snippet):
                self._result_snippet = snippet

        if tag in ("div", "span") and self._collecting_snippet:
            self._collecting_snippet = False
            snippet = " ".join(t for t in self._snippet_buf if t).strip()
            if snippet and len(snippet) > len(self._result_snippet):
                self._result_snippet = snippet

        if tag == "li" and self._in_result:
            self._finalize()

        if tag == "div" and self._in_result and self._result_title:
            self._finalize()

    def handle_data(self, data: str) -> None:
        text = data.strip()
        if not text:
            return

        if self._in_h2 or self._in_h3 or self._in_link:
            self._title_buf.append(text)

        if self._collecting_snippet:
            self._snippet_buf.append(text)

    def _finalize(self) -> None:
        if self._result_title and self._result_url:
            if not _is_excluded_url(self._result_url):
                self.results.append({
                    "title": self._result_title[:200],
                    "url": self._result_url,
                    "snippet": self._result_snippet[:300],
                })
        self._in_result = False
        self._result_title = ""
        self._result_url = ""
        self._result_snippet = ""


def _clean_title(title: str) -> str:
    """Clean up extracted title — remove URL fragments, breadcrumbs, etc."""
    title = re.sub(r"^[\w.-]+\s+(https?://\S+)", "", title).strip()
    title = re.sub(r"^(https?://\S+)\s*", "", title).strip()
    title = re.sub(r"\s+(https?://\S+)$", "", title).strip()
    title = re.sub(r"^.*?›\s*", "", title).strip()
    # Remove site prefix like "github.com › karpathy" → keep "karpathy"
    title = re.sub(r"^[\w.-]+\.\w+\s*›\s*", "", title).strip()
    return title


def _is_excluded_url(url: str) -> bool:
    """Check if URL should be excluded (low-quality sites)."""
    try:
        parsed = urlparse(url)
        domain = parsed.netloc.lower()
        for excluded in _EXCLUDED_DOMAINS:
            if excluded in domain:
                return True
    except Exception:
        pass
    return False


def _entity_title(entity: Entity) -> str:
    """Extract title from entity content."""
    for line in entity.content.split("\n"):
        line = line.strip()
        if line.startswith("# "):
            return line[2:].strip()
    return entity.content[:80].strip()


def _bing_date_filter(max_age_days: int) -> str:
    """Build Bing CN date filter parameter.

    Returns URL parameter like &filters=ex1:"ez1_20260515"
    which limits results to after that date.
    """
    if max_age_days <= 0:
        return ""
    cutoff = date.today() - timedelta(days=max_age_days)
    return f'&filters=ex1:"ez1_{cutoff.strftime("%Y%m%d")}"'


def _google_date_filter(max_age_days: int) -> str:
    """Build Google date filter parameter (tbs=qdr:dN for past N days)."""
    if max_age_days <= 0:
        return ""
    if max_age_days <= 1:
        return "&tbs=qdr:d"
    if max_age_days <= 7:
        return "&tbs=qdr:w"
    if max_age_days <= 30:
        return "&tbs=qdr:m"
    return "&tbs=qdr:y"


def _parse_search_html(html: str, max_results: int) -> list[dict[str, str]]:
    """Parse search engine HTML, return list of {title, url, snippet}."""
    parser = _SearchResultParser()
    try:
        parser.feed(html)
    except Exception:
        pass
    return parser.results[:max_results]


class WebSearchAdapter(SourceAdapter):
    """Adapter for web search via Google (Playwright), Bing CN (httpx), or ZhiPu API.

    Config keys:
        queries: list[str] — search keywords
        engine: str — "auto" | "google" | "bing_cn" | "zhipu" (overrides global)
        max_results: int — max results per query (default 10)
        max_age_days: int — limit results to last N days (default 7)
        concurrent: bool — fetch all queries in parallel (default False)
    """

    adapter_type = "web_search"

    async def fetch(self) -> list[Entity]:
        queries = self.config.get("queries", [])
        if not queries:
            return []

        max_results = self.config.get("max_results", 10)
        max_age_days = self.config.get("max_age_days", 7)
        engine = self.config.get("engine")
        if not engine or engine == "auto":
            engine = self._resolve_engine()

        concurrent = self.config.get("concurrent", False)

        if concurrent and len(queries) > 1:
            return await self._fetch_concurrent(queries, engine, max_results, max_age_days)

        return await self._fetch_sequential(queries, engine, max_results, max_age_days)

    async def _fetch_sequential(
        self, queries: list[str], engine: str, max_results: int, max_age_days: int
    ) -> list[Entity]:
        """Fetch queries one by one."""
        all_entities: list[Entity] = []
        for query in queries:
            try:
                results = await self._do_search(query, engine, max_results, max_age_days)
                all_entities.extend(results)
            except Exception as e:
                logger.warning("Search failed for '%s': %s", query, e)
        return all_entities

    async def _fetch_concurrent(
        self, queries: list[str], engine: str, max_results: int, max_age_days: int
    ) -> list[Entity]:
        """Fetch all queries with staggered concurrency to avoid rate limits."""
        import asyncio

        async def _safe_search(q: str, delay: float = 0) -> list[Entity]:
            if delay > 0:
                await asyncio.sleep(delay)
            try:
                return await self._do_search(q, engine, max_results, max_age_days)
            except Exception as e:
                logger.warning("Search failed for '%s': %s", q, e)
                return []

        # Stagger requests: 2 concurrent, 2s gap between batches
        batch_size = 2
        tasks = []
        for i, q in enumerate(queries):
            delay = (i // batch_size) * 2.0
            tasks.append(_safe_search(q, delay))

        results = await asyncio.gather(*tasks)

        all_entities: list[Entity] = []
        seen_titles: set[str] = set()
        for entities in results:
            for entity in entities:
                title = _entity_title(entity).lower()[:50]
                if title not in seen_titles:
                    all_entities.append(entity)
                    seen_titles.add(title)

        logger.info(
            "Concurrent search: %d queries → %d entities (after dedup)",
            len(queries),
            len(all_entities),
        )
        return all_entities

    async def _do_search(
        self, query: str, engine: str, max_results: int, max_age_days: int
    ) -> list[Entity]:
        """Dispatch to the right search backend."""
        if engine == "google":
            return await self._search_google(query, max_results, max_age_days)
        if engine == "searxng":
            return await self._search_searxng(query, max_results, max_age_days)
        if engine == "zhipu":
            return await self._search_zhipu(query, max_results)
        return await self._search_bing_cn(query, max_results, max_age_days)

    def _resolve_engine(self) -> str:
        config = get_config()
        setting = config.ingest.search_engine
        if setting in ("google", "bing_cn", "zhipu", "searxng"):
            return setting
        # auto: searxng if configured, else zhipu if API key, else bing_cn
        if config.ingest.searxng_url:
            return "searxng"
        if config.composer.llm_api_key and config.composer.llm_base_url:
            return "zhipu"
        if config.ingest.proxy:
            return "google"
        return "bing_cn"

    async def _search_searxng(
        self, query: str, max_results: int, max_age_days: int
    ) -> list[Entity]:
        """Search via self-hosted SearXNG JSON API."""
        config = get_config()
        base_url = config.ingest.searxng_url.rstrip("/")
        timeout = config.ingest.search_timeout

        params: dict[str, str | int] = {
            "q": query,
            "format": "json",
            "categories": "general",
        }

        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.get(f"{base_url}/search", params=params)
            response.raise_for_status()

        data = response.json()
        results = data.get("results", [])[:max_results]

        entities = [
            self._make_entity(
                r["title"],
                r["url"],
                r.get("content", ""),
                query,
            )
            for r in results
            if r.get("title") and r.get("url") and not _is_excluded_url(r["url"])
        ]
        logger.info("SearXNG '%s': %d results", query, len(entities))
        return entities

    async def _search_bing_cn(
        self, query: str, max_results: int, max_age_days: int
    ) -> list[Entity]:
        """Search via Bing CN using httpx."""
        encoded_q = quote_plus(query)
        url = f"https://cn.bing.com/search?q={encoded_q}&count={max_results}"
        url += _bing_date_filter(max_age_days)
        config = get_config()
        timeout = config.ingest.search_timeout

        async with httpx.AsyncClient(
            timeout=timeout,
            headers={
                "User-Agent": (
                    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
                ),
                "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            },
            follow_redirects=True,
        ) as client:
            response = await client.get(url)
            response.raise_for_status()

        raw_results = _parse_search_html(response.text, max_results)
        entities = [
            self._make_entity(r["title"], r["url"], r["snippet"], query)
            for r in raw_results
            if r["title"] and r["url"]
        ]
        logger.info("Bing CN '%s': %d results", query, len(entities))
        return entities

    async def _search_google(
        self, query: str, max_results: int, max_age_days: int
    ) -> list[Entity]:
        """Search via Google using Playwright headless browser."""
        try:
            from playwright.async_api import async_playwright
        except ImportError:
            logger.warning("Playwright not installed, falling back to Bing CN")
            return await self._search_bing_cn(query, max_results, max_age_days)

        config = get_config()
        proxy = config.ingest.proxy
        timeout = config.ingest.search_timeout

        encoded_q = quote_plus(query)
        search_url = (
            f"https://www.google.com/search?q={encoded_q}"
            f"&num={max_results}&hl=zh-CN"
        )
        search_url += _google_date_filter(max_age_days)

        entities: list[Entity] = []
        async with async_playwright() as p:
            launch_args: dict = {"headless": True}
            if proxy:
                launch_args["proxy"] = {"server": proxy}

            browser = await p.chromium.launch(**launch_args)
            try:
                page = await browser.new_page()
                await page.goto(
                    search_url,
                    timeout=timeout * 1000,
                    wait_until="domcontentloaded",
                )
                html = await page.content()
            finally:
                await browser.close()

        raw_results = _parse_search_html(html, max_results)
        entities = [
            self._make_entity(r["title"], r["url"], r["snippet"], query)
            for r in raw_results
            if r["title"] and r["url"]
        ]
        logger.info("Google '%s': %d results", query, len(entities))
        return entities

    async def _search_zhipu(self, query: str, max_results: int) -> list[Entity]:
        """Search via ZhiPu BigModel API with web_search tool.

        ZhiPu's web_search returns a synthesized answer with numbered items,
        not raw search results. Each item is converted to an Entity.
        """
        config = get_config()
        api_key = config.composer.llm_api_key
        base_url = (config.composer.llm_base_url or "").rstrip("/")

        if not api_key:
            logger.warning("No LLM API key configured, falling back to Bing CN")
            return await self._search_bing_cn(query, max_results, 7)

        url = f"{base_url}/chat/completions"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        }
        payload = {
            "model": config.composer.llm_model or "glm-4-flash",
            "messages": [{"role": "user", "content": query}],
            "tools": [{"type": "web_search", "web_search": {"enable": True}}],
            "max_tokens": 2048,
        }

        async with httpx.AsyncClient(timeout=config.ingest.search_timeout) as client:
            response = await client.post(url, headers=headers, json=payload)
            response.raise_for_status()

        data = response.json()
        return self._parse_zhipu_response(data, query, max_results)

    def _parse_zhipu_response(
        self, data: dict, query: str, max_results: int
    ) -> list[Entity]:
        """Parse ZhiPu web_search response into Entity list.

        ZhiPu returns a synthesized content with numbered items like:
        1. Title/description...
        2. Title/description...
        """
        results: list[Entity] = []

        choices = data.get("choices", [])
        if not choices:
            return results

        content = choices[0].get("message", {}).get("content", "")
        if not content:
            return results

        # Split by numbered items: "1. xxx" "2. xxx" etc.
        items = re.split(r"\n\d+\.\s+", content)
        # First item before "1." is usually intro text, skip it
        if items and not content.strip().startswith("1."):
            items = items[1:]

        for item in items[:max_results]:
            text = item.strip()
            if not text or len(text) < 10:
                continue
            # Take first sentence as title, rest as snippet
            sentences = re.split(r"[。！？\n]", text, maxsplit=1)
            title = sentences[0].strip()[:150]
            snippet = sentences[1].strip()[:300] if len(sentences) > 1 else ""

            entity = Entity(
                content=f"# {title}\n\n{snippet}",
                facet=EntityFacet.REFERENCE,
                created_by="agent:web_search",
                confidence=get_config().ingest.default_confidence.get("web_search", 0.7),
                sources=[
                    Source(
                        type=SourceType.WEB_SEARCH,
                        name=self.source_id,
                        url="",
                        metadata={
                            "query": query,
                            "title": title,
                            "engine": "zhipu",
                        },
                    )
                ],
            )
            results.append(entity)

        logger.info("ZhiPu web_search '%s': %d results", query, len(results))
        return results

    def _make_entity(
        self, title: str, url: str, snippet: str, query: str
    ) -> Entity:
        content = f"# {title}\n\n{snippet}\n\n[Source]({url})"
        return Entity(
            content=content,
            facet=EntityFacet.REFERENCE,
            created_by="agent:web_search",
            confidence=get_config().ingest.default_confidence.get("web_search", 0.6),
            sources=[
                Source(
                    type=SourceType.WEB_SEARCH,
                    name=self.source_id,
                    url=url,
                    metadata={
                        "query": query,
                        "title": title,
                        "authority": self.metadata.get("authority", "medium"),
                    },
                )
            ],
        )

    def health_check(self) -> bool:
        return bool(self.config.get("queries"))
