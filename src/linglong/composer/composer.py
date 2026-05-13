"""流水线编排器

串联各层组件，执行完整的内容生产流程。
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from linglong.composer.assets.image_asset_fetcher import ImageAssetFetcher
from linglong.composer.assets.image_asset_selector import ImageAssetSelector
from linglong.composer.assets.text import TextAssetGenerator
from linglong.composer.distiller.aggregator import ArticleMaterial, DailyAggregator
from linglong.composer.distiller.llm_distiller import LLMDistiller
from linglong.composer.draft import DraftManager
from linglong.composer.ingest_adapter import IngestAdapter, MemoryFragment
from linglong.composer.state import ComposerState
from linglong.composer.templates.blog import BlogTemplate
from linglong.core.config import get_config
from linglong.core.models import EntityStatus
from linglong.dispatch.manager import DispatchManager
from linglong.knowledge.store import KnowledgeStore

logger = logging.getLogger(__name__)


@dataclass
class ComposerResult:
    """流水线执行结果"""

    success: bool = True
    articles: list[dict[str, Any]] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    def add_article(self, article_info: dict):
        self.articles.append(article_info)

    def add_error(self, error: str):
        self.errors.append(error)
        self.success = False

    def __repr__(self):
        return f"ComposerResult(success={self.success}, articles={len(self.articles)}, errors={len(self.errors)})"


class Composer:
    """内容生产流水线"""

    def __init__(self):
        self.config = get_config().composer
        self.text_gen = TextAssetGenerator({"excerpt_length": self.config.assets_excerpt_length})

        # 状态管理：内容哈希去重
        self.state = ComposerState()
        self.draft_manager = DraftManager()

        # 聚合器：始终需要按天分组
        self.aggregator = DailyAggregator()

        # 提炼器：LLM 模式 或 规则聚合模式
        if self.config.distiller_use_llm:
            llm_config = {
                "provider": self.config.llm_provider,
                "model": self.config.llm_model,
                "api_key": self.config.llm_api_key,
                "base_url": self.config.llm_base_url,
                "temperature": self.config.llm_temperature,
                "max_tokens": self.config.llm_max_tokens,
            }
            self.distiller = LLMDistiller(llm_config)
            logger.info("Distiller 模式: LLM 智能提炼")
        else:
            self.distiller = DailyAggregator()
            logger.info("Distiller 模式: 规则聚合")

    def run(
        self,
        since: datetime | None = None,
        dry_run: bool = False,
        draft: bool = False,
    ) -> ComposerResult:
        """执行完整流水线

        Args:
            since: 只处理该时间之后的记忆，None 表示全部
            dry_run: 试运行模式，不实际保存
            draft: 草稿模式，生成文章到草稿目录等待审核

        Returns:
            ComposerResult: 执行结果
        """
        result = ComposerResult()

        # 1. 从 KnowledgeStore 提取记忆
        fragments = self._extract_fragments(since)
        if not fragments:
            logger.warning("没有提取到任何记忆片段")
            return result

        # 去重：跳过已处理的内容
        fragments = self.state.filter_new(fragments)
        if not fragments:
            logger.info("没有新的记忆片段需要处理")
            return result

        logger.info(f"共提取 {len(fragments)} 条新记忆片段")

        # 2. 分组策略
        strategy = "theme" if self.config.distiller_use_llm else "daily"

        if strategy == "theme":
            if not isinstance(self.distiller, LLMDistiller):
                logger.error("theme 策略需要 distiller_use_llm=true")
                result.add_error("theme 策略需要 distiller_use_llm=true")
                return result

            groups = self.distiller.group_by_theme(fragments)
            logger.info(f"主题分析完成，共 {len(groups)} 个主题")
        else:
            # 默认按天聚合
            groups = self.aggregator.aggregate(fragments)
            logger.info(f"聚合为 {len(groups)} 天的内容")

        # 3. 逐组生成文章
        for key, frags in groups.items():
            try:
                article_result = self._process_day(key, frags, dry_run=dry_run, draft=draft)
                result.add_article(article_result)
                if not dry_run and not draft:
                    self.state.mark_processed(frags)
            except Exception as e:
                error_msg = f"处理 {key} 失败: {e}"
                logger.exception(error_msg)
                result.add_error(error_msg)

        return result

    def _extract_fragments(self, since: datetime | None = None) -> list[MemoryFragment]:
        """从 KnowledgeStore 提取片段"""
        store = KnowledgeStore()
        entities = store.search(status=EntityStatus.AUTO_CONFIRMED, limit=100)
        fragments = IngestAdapter.adapt_many(entities)

        if since:
            fragments = [f for f in fragments if f.timestamp >= since]

        logger.info(f"从 KnowledgeStore 提取到 {len(fragments)} 条片段")
        return fragments

    def _process_day(
        self,
        date_key: str,
        fragments: list[MemoryFragment],
        dry_run: bool = False,
        draft: bool = False,
    ) -> dict:
        """处理一天的内容，生成文章或保存草稿

        Returns a dispatch-ready result dict.
        """
        logger.info(f"处理 {date_key} 的内容，共 {len(fragments)} 条片段")

        # 3.1 提炼素材（LLM 模式 或 规则模式）
        if isinstance(self.distiller, LLMDistiller):
            material = self.distiller.distill(date_key, fragments)
            content_with_intro = material.raw_content
            excerpt = material.excerpt
            tags = material.tags
        else:
            # 规则聚合模式
            material = ArticleMaterial(
                date=date_key,
                fragments=fragments,
                title=f"每日回顾 {date_key}",
            )
            excerpt = self.text_gen.generate_excerpt(fragments)
            tags = self.text_gen.generate_tags(fragments)
            intro = self.text_gen.generate_intro(excerpt)
            material.excerpt = excerpt
            material.tags = tags
            raw_content = material.compile_content()
            content_with_intro = f"{intro}\n\n{raw_content}"

        # 3.2 应用模板
        template = BlogTemplate({})
        metadata = {
            "title": material.title,
            "date": date_key,
            "tags": material.tags,
            "categories": material.categories,
            "excerpt": excerpt,
        }
        # 3.3 Image assets (background + article image)
        if self.config.image_assets.enabled:
            try:
                image_cfg = self.config.image_assets
                selector = ImageAssetSelector({
                    "sources": [s.model_dump() for s in image_cfg.sources],
                    "selection": image_cfg.selection.model_dump(),
                })
                # Build resolver for sources that need Playwright
                resolver = self._build_image_resolver(image_cfg.sources)
                used_urls: list[str] = []
                for usage in ("background", "article_image"):
                    if usage not in image_cfg.specs:
                        continue
                    spec = image_cfg.specs[usage]
                    source_urls = selector.select(usage, count=1)
                    if not source_urls:
                        continue
                    # Resolve page URLs to image URLs if needed
                    resolved = self._resolve_image_urls(
                        source_urls, image_cfg.sources, resolver
                    )
                    if not resolved:
                        continue
                    fetcher = ImageAssetFetcher(spec)
                    path = fetcher.fetch(resolved[0])
                    if path:
                        metadata[usage] = str(path)
                        used_urls.append(source_urls[0])
                if used_urls:
                    selector.record_used(used_urls)
            except Exception as e:
                logger.warning("Image asset processing failed: %s", e)

        formatted = template.apply(content_with_intro, metadata)

        # 草稿模式：保存到草稿目录
        if draft and not dry_run:
            fragment_hashes = [f.content_hash for f in fragments]
            entry = self.draft_manager.save_draft(
                title=material.title,
                date=date_key,
                content=formatted,
                metadata=metadata,
                fragment_hashes=fragment_hashes,
            )
            return {
                "date": date_key,
                "fragments_count": len(fragments),
                "title": material.title,
                "tags": tags,
                "draft_id": entry.id,
                "dispatch_ready": False,
                "status": "draft_saved",
            }

        # 正常运行模式：返回 dispatch-ready 结果
        if dry_run:
            return {
                "date": date_key,
                "fragments_count": len(fragments),
                "title": material.title,
                "tags": tags,
                "dispatch_ready": False,
                "status": "dry_run",
            }

        article_result = {
            "date": date_key,
            "fragments_count": len(fragments),
            "title": material.title,
            "tags": tags,
            "content": formatted,
            "metadata": metadata,
            "dispatch_ready": True,
            "status": "dispatch_ready",
        }

        if self.config.auto_publish:
            try:
                dispatch = DispatchManager()
                publish_result = dispatch.publish(article_result, self.config.default_publisher)
                article_result["publish_result"] = publish_result
            except Exception as e:
                logger.exception("Auto-publish failed for %s: %s", date_key, e)
                article_result["publish_error"] = str(e)

        return article_result

    def _build_image_resolver(self, sources) -> "PageImageResolver | None":
        """Build a Playwright resolver if any source needs it."""
        from linglong.composer.assets.page_image_resolver import PageImageResolver

        for src in sources:
            if src.resolve_via == "playwright":
                delay = tuple(src.delay_range) if len(src.delay_range) == 2 else (3, 8)
                return PageImageResolver(
                    headless=src.headless,
                    delay_range=delay,
                    max_count=src.max_count,
                )
        return None

    def _resolve_image_urls(
        self, urls: list[str], sources, resolver
    ) -> list[str]:
        """Resolve page URLs to image URLs using Playwright if needed.

        Returns the original URLs if no resolver is needed or available.
        """
        if resolver is None:
            return urls

        needs_resolve = any(s.resolve_via == "playwright" for s in sources)
        if not needs_resolve:
            return urls

        if not resolver.health_check():
            logger.warning("Playwright not available, using URLs as-is")
            return urls

        try:
            resolved = resolver.resolve_sync(urls)
            return resolved if resolved else urls
        except Exception as e:
            logger.warning("Playwright resolution failed: %s, using URLs as-is", e)
            return urls
