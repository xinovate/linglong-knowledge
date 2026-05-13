"""Page image resolver — extract image URLs from web pages using Playwright.

Adapted from linglong-pipeline's TuchongSource.
Uses Playwright to visit pages and extract actual image URLs via regex.
Playwright is imported lazily so the module works without it installed.
"""

import asyncio
import logging
import random
import re

logger = logging.getLogger(__name__)

# 图虫图片 URL 匹配模式
_TUCHONG_IMAGE_PATTERN = re.compile(r"https://photo\.tuchong\.com/\d+/f/\d+\.jpg")

# 验证码/WAF 检测关键词
_CAPTCHA_KEYWORDS = ("captcha", "ttgcaptcha", "verify")


class PageImageResolver:
    """Resolve page URLs to actual image URLs using Playwright.

    Visits each page sequentially, extracts image URLs from HTML,
    handles captcha detection, and returns deduplicated results.
    """

    def __init__(
        self,
        headless: bool = True,
        delay_range: tuple[int, int] = (3, 8),
        max_count: int = 50,
    ):
        self.headless = headless
        self.delay_range = delay_range
        self.max_count = max_count

    def health_check(self) -> bool:
        """Check if Playwright is available."""
        try:
            from playwright.async_api import async_playwright  # noqa: F401

            return True
        except ImportError:
            logger.error("Playwright not installed. Run: pip install playwright && playwright install chromium")
            return False

    async def resolve(self, urls: list[str]) -> list[str]:
        """Resolve page URLs to image URLs.

        Args:
            urls: List of page URLs (e.g. https://tuchong.com/xxx/yyy/)

        Returns:
            List of deduplicated image URLs (e.g. https://photo.tuchong.com/xxx/f/yyy.jpg)
        """
        from playwright.async_api import async_playwright

        urls = urls[: self.max_count]
        logger.info("Resolving %d page URLs to image URLs", len(urls))
        results: list[str] = []
        seen: set[str] = set()

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=self.headless)
            context = await browser.new_context(
                user_agent=(
                    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
                ),
                viewport={"width": 1920, "height": 1080},
            )

            for i, page_url in enumerate(urls, 1):
                logger.info("[%d/%d] Resolving: %s", i, len(urls), page_url)
                page = await context.new_page()
                img_url = await self._resolve_single(page, page_url)
                await page.close()

                if img_url and img_url not in seen:
                    seen.add(img_url)
                    results.append(img_url)

                # 页面间随机延迟
                if i < len(urls):
                    delay = random.uniform(*self.delay_range)
                    await asyncio.sleep(delay)

            await browser.close()

        logger.info("Resolved %d image URLs from %d pages", len(results), len(urls))
        return results

    async def _resolve_single(self, page, url: str) -> str | None:
        """Resolve a single page URL to an image URL."""
        try:
            await page.goto(url, wait_until="networkidle", timeout=30000)
            await asyncio.sleep(2)

            html = await page.content()

            # 验证码/WAF 检测
            html_lower = html.lower()
            if any(kw in html_lower for kw in _CAPTCHA_KEYWORDS):
                logger.warning("Captcha/WAF detected, skipping: %s", url)
                return None

            # 提取图片 URL
            images = _TUCHONG_IMAGE_PATTERN.findall(html)
            if not images:
                logger.warning("No images found on page: %s", url)
                return None

            first_img = images[0]
            logger.info("  Found image: %s", first_img)
            return first_img

        except Exception as e:
            logger.error("Failed to resolve %s: %s", url, e)
            return None

    def resolve_sync(self, urls: list[str]) -> list[str]:
        """Synchronous wrapper for resolve()."""
        loop = asyncio.new_event_loop()
        try:
            return loop.run_until_complete(self.resolve(urls))
        finally:
            loop.close()
