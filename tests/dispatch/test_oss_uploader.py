"""OSS uploader tests — upload and URL rewriting with mocked oss2."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from linglong.dispatch.publishers.oss import OSSUploader


@pytest.fixture
def oss_config():
    """Standard OSS config for testing."""
    return {
        "bucket_name": "test-bucket",
        "endpoint": "oss-cn-hangzhou.aliyuncs.com",
        "cdn_domain": "img.test.com",
        "access_key_id": "test-key-id",
        "access_key_secret": "test-key-secret",
        "prefix": "images/",
    }


@pytest.fixture
def uploader(oss_config):
    """Create an OSSUploader with test config."""
    return OSSUploader(oss_config)


@pytest.fixture
def sample_images(tmp_path):
    """Create sample image files for testing."""
    images = {}
    for name in ["abc.thumb.jpg", "abc.medium.jpg", "abc.large.jpg"]:
        path = tmp_path / name
        path.write_bytes(b"\xff\xd8\xff\xe0" + b"\x00" * 100)  # Fake JPEG header
        images[name] = path
    return images


class TestOSSUploaderInit:
    """OSSUploader initialization tests."""

    def test_config_stored(self, uploader):
        """Config values should be stored correctly."""
        assert uploader.bucket_name == "test-bucket"
        assert uploader.endpoint == "oss-cn-hangzhou.aliyuncs.com"
        assert uploader.cdn_domain == "img.test.com"
        assert uploader.prefix == "images/"

    def test_default_prefix(self, oss_config):
        """Default prefix should be 'images/'."""
        oss_config.pop("prefix")
        uploader = OSSUploader(oss_config)
        assert uploader.prefix == "images/"


class TestUploadImage:
    """upload_image() tests."""

    def test_upload_returns_cdn_url(self, uploader, sample_images):
        """upload_image() should return a CDN URL."""
        mock_bucket = MagicMock()
        uploader._bucket = mock_bucket

        path = list(sample_images.values())[0]
        url = uploader.upload_image(path)

        assert url == f"https://img.test.com/images/{path.name}"
        mock_bucket.put_object.assert_called_once()

    def test_upload_uses_correct_key(self, uploader, sample_images):
        """Upload should use prefix + filename as OSS key."""
        mock_bucket = MagicMock()
        uploader._bucket = mock_bucket

        path = sample_images["abc.thumb.jpg"]
        uploader.upload_image(path)

        call_args = mock_bucket.put_object.call_args
        key = call_args[0][0]
        assert key == "images/abc.thumb.jpg"


class TestUploadAndRewrite:
    """upload_and_rewrite() integration tests."""

    def test_rewrites_metadata_dict_variants(self, uploader, sample_images):
        """Should rewrite paths in metadata dict variants."""
        mock_bucket = MagicMock()
        uploader._bucket = mock_bucket

        # 指向真实临时文件路径
        variants = {name.split(".")[1]: str(path) for name, path in sample_images.items()}

        content = f"![配图]({list(sample_images.values())[1]})"
        metadata = {"article_image": variants}

        new_content, new_metadata = uploader.upload_and_rewrite(content, metadata)

        # metadata 变体应被替换为 CDN URL
        for name, url in new_metadata["article_image"].items():
            assert url.startswith("https://img.test.com/images/")

    def test_rewrites_string_paths_in_content(self, uploader, sample_images):
        """Should replace local paths with CDN URLs in content string."""
        mock_bucket = MagicMock()
        uploader._bucket = mock_bucket

        path = list(sample_images.values())[1]  # medium
        content = f"![配图]({path})"
        metadata = {"article_image": str(path)}

        new_content, new_metadata = uploader.upload_and_rewrite(content, metadata)

        assert str(path) not in new_content
        assert "https://img.test.com/images/" in new_content

    def test_no_images_returns_unchanged(self, uploader):
        """If no images found, content and metadata should be unchanged."""
        mock_bucket = MagicMock()
        uploader._bucket = mock_bucket

        content = "Hello world"
        metadata = {"title": "Test"}

        new_content, new_metadata = uploader.upload_and_rewrite(content, metadata)

        assert new_content == content
        assert new_metadata == metadata
        mock_bucket.put_object.assert_not_called()

    def test_dedup_repeated_paths(self, uploader, sample_images):
        """Same path appearing multiple times should only be uploaded once."""
        mock_bucket = MagicMock()
        uploader._bucket = mock_bucket

        path = str(list(sample_images.values())[0])
        content = f"![a]({path}) ![b]({path})"
        metadata = {"article_image": path}

        uploader.upload_and_rewrite(content, metadata)

        # 应只上传一次，不重复
        assert mock_bucket.put_object.call_count == 1

    def test_rewrites_background_and_cover(self, uploader, sample_images):
        """Should handle background, background_image, and cover_image keys."""
        mock_bucket = MagicMock()
        uploader._bucket = mock_bucket

        path = str(list(sample_images.values())[0])
        metadata = {
            "background": {"thumb": path, "medium": path},
            "background_image": path,
            "cover_image": path,
        }

        _, new_metadata = uploader.upload_and_rewrite("", metadata)

        # 全部应被替换
        assert new_metadata["background"]["thumb"].startswith("https://")
        assert new_metadata["background"]["medium"].startswith("https://")
        assert new_metadata["background_image"].startswith("https://")
        assert new_metadata["cover_image"].startswith("https://")

    def test_preserves_non_image_metadata(self, uploader, sample_images):
        """Non-image metadata keys should be preserved as-is."""
        mock_bucket = MagicMock()
        uploader._bucket = mock_bucket

        path = str(list(sample_images.values())[0])
        metadata = {
            "article_image": path,
            "title": "测试标题",
            "tags": ["tag1", "tag2"],
        }

        _, new_metadata = uploader.upload_and_rewrite("", metadata)

        assert new_metadata["title"] == "测试标题"
        assert new_metadata["tags"] == ["tag1", "tag2"]


class TestHealthCheck:
    """health_check() tests."""

    def test_health_check_success(self, uploader):
        """Health check should return True when OSS is accessible."""
        mock_bucket = MagicMock()
        uploader._bucket = mock_bucket

        assert uploader.health_check() is True

    def test_health_check_failure(self, uploader):
        """Health check should return False when OSS is not accessible."""
        mock_bucket = MagicMock()
        mock_bucket.list_objects.side_effect = Exception("Connection refused")
        uploader._bucket = mock_bucket

        assert uploader.health_check() is False
