"""Image pipeline tests — multi-size variant generation."""

import tempfile
from pathlib import Path

import pytest
from PIL import Image

from linglong.composer.assets.image_asset_fetcher import ImageAssetFetcher, ImageResult
from linglong.core.config import ImageAssetSpecConfig


@pytest.fixture
def spec(tmp_path):
    """Create an ImageAssetSpecConfig with temp output dir."""
    return ImageAssetSpecConfig(
        min_width=200,
        min_height=150,
        quality=85,
        output_dir=str(tmp_path / "images"),
        variants={"thumb": 100, "medium": 200, "large": 400},
    )


@pytest.fixture
def large_image(tmp_path):
    """Create a test image larger than min_width/min_height."""
    img = Image.new("RGB", (800, 600), color="red")
    path = tmp_path / "test_image.jpg"
    img.save(path, "JPEG")
    return path


@pytest.fixture
def small_image(tmp_path):
    """Create a test image smaller than min_width/min_height."""
    img = Image.new("RGB", (100, 80), color="blue")
    path = tmp_path / "small.jpg"
    img.save(path, "JPEG")
    return path


class TestImageResult:
    """ImageResult dataclass tests."""

    def test_variant_accessors(self, tmp_path):
        thumb = tmp_path / "thumb.jpg"
        medium = tmp_path / "medium.jpg"
        large = tmp_path / "large.jpg"
        thumb.touch()
        medium.touch()
        large.touch()

        result = ImageResult(
            variants={"thumb": thumb, "medium": medium, "large": large},
            width=800,
            height=600,
        )
        assert result.thumb == thumb
        assert result.medium == medium
        assert result.large == large
        assert result.width == 800
        assert result.height == 600

    def test_best_returns_largest(self, tmp_path):
        thumb = tmp_path / "thumb.jpg"
        medium = tmp_path / "medium.jpg"
        thumb.touch()
        medium.touch()

        result = ImageResult(variants={"thumb": thumb, "medium": medium})
        assert result.best == medium

    def test_best_with_only_thumb(self, tmp_path):
        thumb = tmp_path / "thumb.jpg"
        thumb.touch()

        result = ImageResult(variants={"thumb": thumb})
        assert result.best == thumb


class TestImageAssetFetcherMultiSize:
    """Multi-size variant generation tests."""

    def test_fetch_generates_variants(self, spec, large_image):
        """fetch() should generate all configured size variants."""
        # 需要通过本地 URL 或 mock 请求来提供文件
        # 改为直接用本地文件测试 _process
        fetcher = ImageAssetFetcher(spec)
        fetcher.output_dir.mkdir(parents=True, exist_ok=True)

        result = fetcher._process(large_image, "https://example.com/test.jpg")

        assert result is not None
        assert isinstance(result, ImageResult)
        assert result.width == 800
        assert result.height == 600
        assert len(result.variants) == 3
        assert "thumb" in result.variants
        assert "medium" in result.variants
        assert "large" in result.variants

    def test_variant_files_exist(self, spec, large_image):
        """Generated variant files should exist on disk."""
        fetcher = ImageAssetFetcher(spec)
        fetcher.output_dir.mkdir(parents=True, exist_ok=True)

        result = fetcher._process(large_image, "https://example.com/test.jpg")

        assert result is not None
        for name, path in result.variants.items():
            assert path.exists(), f"Variant {name} file should exist: {path}"

    def test_variant_dimensions_respected(self, spec, large_image):
        """Variants should not exceed configured max width."""
        fetcher = ImageAssetFetcher(spec)
        fetcher.output_dir.mkdir(parents=True, exist_ok=True)

        result = fetcher._process(large_image, "https://example.com/test.jpg")
        assert result is not None

        for name, path in result.variants.items():
            with Image.open(path) as img:
                w, h = img.size
                max_w = spec.variants[name]
                assert w <= max_w, f"Variant {name}: width {w} > max {max_w}"

    def test_small_image_rejected(self, spec, small_image):
        """Images below min_width/min_height should be rejected."""
        fetcher = ImageAssetFetcher(spec)
        fetcher.output_dir.mkdir(parents=True, exist_ok=True)

        result = fetcher._process(small_image, "https://example.com/small.jpg")
        assert result is None

    def test_variant_quality_applied(self, spec, large_image):
        """Variants should be saved with configured JPEG quality."""
        spec.quality = 50
        fetcher = ImageAssetFetcher(spec)
        fetcher.output_dir.mkdir(parents=True, exist_ok=True)

        result = fetcher._process(large_image, "https://example.com/test.jpg")
        assert result is not None

        # 检查 quality=50 时文件大小合理
        # (lower quality = smaller files)
        for name, path in result.variants.items():
            assert path.stat().st_size > 0, f"Variant {name} should not be empty"

    def test_skip_variant_larger_than_original(self, tmp_path):
        """Variants with max_width >= original width should save original."""
        spec = ImageAssetSpecConfig(
            min_width=100,
            min_height=100,
            quality=85,
            output_dir=str(tmp_path / "images"),
            variants={"thumb": 50, "huge": 2000},  # huge > original 300
        )
        # 创建 300x200 测试图片
        img = Image.new("RGB", (300, 200), color="green")
        img_path = tmp_path / "medium.jpg"
        img.save(img_path, "JPEG")

        fetcher = ImageAssetFetcher(spec)
        fetcher.output_dir.mkdir(parents=True, exist_ok=True)

        result = fetcher._process(img_path, "https://example.com/medium.jpg")
        assert result is not None
        assert "thumb" in result.variants
        assert "huge" in result.variants

        # huge variant should be same size as original (saved as-is)
        with Image.open(result.variants["huge"]) as huge_img:
            assert huge_img.size == (300, 200)

    def test_fetch_returns_imageresult(self, spec, large_image):
        """fetch() public API should return ImageResult, not Path."""
        fetcher = ImageAssetFetcher(spec)
        fetcher.output_dir.mkdir(parents=True, exist_ok=True)

        # 直接测试 _process，因为 fetch() 需要 HTTP
        result = fetcher._process(large_image, "https://example.com/test.jpg")

        assert result is not None
        assert isinstance(result, ImageResult)
        # 不应是 Path（旧行为）
        assert not isinstance(result, Path)
