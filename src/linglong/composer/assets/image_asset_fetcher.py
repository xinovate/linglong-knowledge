"""图片资产获取器 — 下载、筛选、压缩、多尺寸生成。

从 linglong-pipeline 的 TuchongImageFetcher 演化而来。
支持多源配置驱动的 headers 和规格，生成 thumb/medium/large 响应式变体。
"""

import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import requests
from PIL import Image

from linglong.core.config import ImageAssetSpecConfig

logger = logging.getLogger(__name__)

_DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
}


@dataclass
class ImageResult:
    """图片处理结果，包含多个尺寸变体的路径。"""

    variants: dict[str, Path] = field(default_factory=dict)
    width: int = 0
    height: int = 0

    @property
    def thumb(self) -> Path | None:
        return self.variants.get("thumb")

    @property
    def medium(self) -> Path | None:
        return self.variants.get("medium")

    @property
    def large(self) -> Path | None:
        return self.variants.get("large")

    @property
    def best(self) -> Path:
        """返回最大可用变体。"""
        for name in ("large", "medium", "thumb"):
            if name in self.variants:
                return self.variants[name]
        # 兜底：返回任意变体
        return next(iter(self.variants.values()))


class ImageAssetFetcher:
    """下载并处理图片，生成多尺寸变体。

    流水线：下载 → 尺寸检查 → EXIF 清理 → 生成变体 → JPEG 保存。
    """

    def __init__(self, spec: ImageAssetSpecConfig, headers: dict[str, str] | None = None):
        self.spec = spec
        self.headers = headers or _DEFAULT_HEADERS
        self.output_dir = Path(spec.output_dir).expanduser()

    def fetch(self, url: str) -> ImageResult | None:
        """下载单张图片并生成多尺寸变体。

        Returns:
            ImageResult 成功时返回，失败返回 None。
        """
        self.output_dir.mkdir(parents=True, exist_ok=True)
        try:
            resp = requests.get(url, headers=self.headers, timeout=30, verify=False)
            resp.raise_for_status()
        except Exception as e:
            logger.warning("Download failed for %s: %s", url, e)
            return None

        # 先写入临时文件
        tmp_path = self.output_dir / "_tmp_download.jpg"
        tmp_path.write_bytes(resp.content)

        if tmp_path.stat().st_size < 1000:
            logger.warning("File too small for %s", url)
            tmp_path.unlink(missing_ok=True)
            return None

        # 校验并处理
        result = self._process(tmp_path, url)
        if result is None:
            tmp_path.unlink(missing_ok=True)
        return result

    def fetch_batch(self, urls: list[str], max_workers: int = 3) -> list[ImageResult]:
        """并发下载多张图片。

        Returns:
            成功处理的 ImageResult 列表。
        """
        results: list[ImageResult] = []
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {executor.submit(self.fetch, url): url for url in urls}
            for future in as_completed(futures):
                result = future.result()
                if result is not None:
                    results.append(result)
        return results

    def _process(self, tmp_path: Path, original_url: str) -> ImageResult | None:
        """校验尺寸、清理 EXIF、生成变体、保存为 JPEG。

        Returns:
            ImageResult 或 None（尺寸不符合规格时）。
        """
        try:
            with Image.open(tmp_path) as img:
                w, h = img.size
                if w < self.spec.min_width or h < self.spec.min_height:
                    logger.info(
                        "Skipped %s: %dx%d < %dx%d",
                        original_url, w, h, self.spec.min_width, self.spec.min_height,
                    )
                    return None

                # 清理 EXIF 方向信息，转为 RGB
                img = img.convert("RGB")
                hash_name = f"{abs(hash(original_url)) % 10**10:010d}"

                # 生成多尺寸变体
                variants = self._generate_variants(img, hash_name)

                logger.info(
                    "Processed: %s (%dx%d, %d variants)",
                    hash_name, w, h, len(variants),
                )
                return ImageResult(variants=variants, width=w, height=h)
        except Exception as e:
            logger.error("Processing failed for %s: %s", original_url, e)
            return None

    def _generate_variants(self, img: Image.Image, hash_name: str) -> dict[str, Path]:
        """从源图生成多尺寸变体。

        使用 thumbnail() 保持宽高比。仅生成小于原图的变体。
        """
        variants: dict[str, Path] = {}
        orig_w, orig_h = img.size

        for name, max_width in self.spec.variants.items():
            # 变体宽度超过原图时直接保存原图
            if max_width >= orig_w:
                out_path = self.output_dir / f"{hash_name}.{name}.jpg"
                img.save(out_path, "JPEG", quality=self.spec.quality)
                variants[name] = out_path
                continue

            # 按比例计算高度
            ratio = max_width / orig_w
            max_height = int(orig_h * ratio)

            # thumbnail() 会原地修改，需先复制
            variant = img.copy()
            variant.thumbnail((max_width, max_height), Image.LANCZOS)

            out_path = self.output_dir / f"{hash_name}.{name}.jpg"
            variant.save(out_path, "JPEG", quality=self.spec.quality)
            variant.close()
            variants[name] = out_path

            size_kb = out_path.stat().st_size // 1024
            logger.debug("Variant %s: %dpx, %dKB", name, max_width, size_kb)

        return variants
