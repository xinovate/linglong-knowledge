"""Image asset fetcher — download, filter, compress images from URL lists.

Generalized from linglong-pipeline's TuchongImageFetcher.
Supports multiple sources via config-driven headers and specs.
"""

import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
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


class ImageAssetFetcher:
    """Download and process images to match a target spec.

    Pipeline: download → size/filter check → clear EXIF → save as JPEG.
    """

    def __init__(self, spec: ImageAssetSpecConfig, headers: dict[str, str] | None = None):
        self.spec = spec
        self.headers = headers or _DEFAULT_HEADERS
        self.output_dir = Path(spec.output_dir).expanduser()

    def fetch(self, url: str) -> Path | None:
        """Download a single image and process it.

        Returns the local path on success, None on failure.
        """
        self.output_dir.mkdir(parents=True, exist_ok=True)
        try:
            resp = requests.get(url, headers=self.headers, timeout=30, verify=False)
            resp.raise_for_status()
        except Exception as e:
            logger.warning("Download failed for %s: %s", url, e)
            return None

        # Write to temp file first
        tmp_path = self.output_dir / "_tmp_download.jpg"
        tmp_path.write_bytes(resp.content)

        if tmp_path.stat().st_size < 1000:
            logger.warning("File too small for %s", url)
            tmp_path.unlink(missing_ok=True)
            return None

        # Validate and process
        result = self._process(tmp_path, url)
        if result is None:
            tmp_path.unlink(missing_ok=True)
        return result

    def fetch_batch(self, urls: list[str], max_workers: int = 3) -> list[Path]:
        """Download multiple images concurrently.

        Returns list of successfully processed local paths.
        """
        results: list[Path] = []
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {executor.submit(self.fetch, url): url for url in urls}
            for future in as_completed(futures):
                path = future.result()
                if path is not None:
                    results.append(path)
        return results

    def _process(self, tmp_path: Path, original_url: str) -> Path | None:
        """Validate size, clear EXIF, save as JPEG.

        Returns processed path or None if size doesn't match spec.
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

                # Clear EXIF orientation by re-saving
                img = img.convert("RGB")
                # Use URL hash to avoid collisions
                filename = f"{abs(hash(original_url)) % 10**10:010d}.jpg"
                out_path = self.output_dir / filename
                img.save(out_path, "JPEG", quality=self.spec.quality)
                size_kb = out_path.stat().st_size // 1024
                logger.info("Processed: %s (%dx%d, %dKB)", filename, w, h, size_kb)
                return out_path
        except Exception as e:
            logger.error("Processing failed for %s: %s", original_url, e)
            return None
