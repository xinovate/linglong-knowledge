"""OSS 上传器 — 将图片上传到阿里云 OSS，替换文章中的本地路径为 CDN URL。"""

import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# 可选依赖 — 仅 OSS 上传功能需要
try:
    import oss2
except ImportError:
    oss2 = None  # type: ignore[assignment]


class OSSUploader:
    """将图片上传到阿里云 OSS，将本地路径替换为 CDN URL。

    依赖: pip install oss2
    """

    def __init__(self, config: dict[str, Any]):
        self.bucket_name: str = config["bucket_name"]
        self.endpoint: str = config["endpoint"]
        self.cdn_domain: str = config["cdn_domain"]
        self.access_key_id: str = config["access_key_id"]
        self.access_key_secret: str = config["access_key_secret"]
        self.prefix: str = config.get("prefix", "images/")
        self._bucket = None

    def _get_bucket(self):
        """延迟初始化 OSS Bucket 连接。"""
        if self._bucket is None:
            if oss2 is None:
                raise ImportError(
                    "oss2 is required for OSS upload. Install with: pip install oss2"
                )
            auth = oss2.Auth(self.access_key_id, self.access_key_secret)
            self._bucket = oss2.Bucket(auth, self.endpoint, self.bucket_name)
        return self._bucket

    def upload_image(self, local_path: Path) -> str:
        """上传单个图片文件到 OSS。

        Args:
            local_path: 本地图片路径

        Returns:
            CDN URL
        """
        key = f"{self.prefix}{local_path.name}"
        bucket = self._get_bucket()

        with open(local_path, "rb") as f:
            bucket.put_object(key, f)

        cdn_url = f"https://{self.cdn_domain}/{key}"
        logger.info("Uploaded %s → %s", local_path.name, cdn_url)
        return cdn_url

    def upload_and_rewrite(
        self, content: str, metadata: dict[str, Any]
    ) -> tuple[str, dict[str, Any]]:
        """上传 metadata 中的所有图片到 OSS，并将本地路径替换为 CDN URL。

        扫描 metadata 中的图片路径（字符串或多尺寸 dict），上传到 OSS 后
        替换 content 和 metadata 中的本地路径为 CDN URL。

        Args:
            content: 文章 markdown/HTML 内容
            metadata: 可能包含图片路径的字典

        Returns:
            (替换后的 content, 更新后的 metadata)
        """
        # 收集所有本地图片路径
        path_map: dict[str, str] = {}  # local_path → cdn_url

        for key in ("background", "background_image", "article_image", "cover_image"):
            if key not in metadata:
                continue
            value = metadata[key]
            if isinstance(value, dict):
                # 多尺寸变体 dict
                for variant_name, path_str in value.items():
                    local = Path(path_str).expanduser()
                    if local.exists() and str(local) not in path_map:
                        cdn_url = self.upload_image(local)
                        path_map[str(local)] = cdn_url
            elif isinstance(value, str) and value:
                local = Path(value).expanduser()
                if local.exists() and str(local) not in path_map:
                    cdn_url = self.upload_image(local)
                    path_map[str(local)] = cdn_url

        if not path_map:
            return content, metadata

        # 替换 content 中的本地路径
        rewritten = content
        for local_path, cdn_url in path_map.items():
            rewritten = rewritten.replace(local_path, cdn_url)

        # 替换 metadata 中的本地路径
        updated_metadata = {}
        for key, value in metadata.items():
            if isinstance(value, dict):
                updated_metadata[key] = {
                    k: path_map.get(v, v) for k, v in value.items()
                }
            elif isinstance(value, str) and value in path_map:
                updated_metadata[key] = path_map[value]
            else:
                updated_metadata[key] = value

        logger.info("Rewrote %d image paths to CDN URLs", len(path_map))
        return rewritten, updated_metadata

    def health_check(self) -> bool:
        """检查 OSS Bucket 是否可访问。"""
        try:
            bucket = self._get_bucket()
            # 尝试列出少量对象验证连通性
            bucket.list_objects(max_keys=1)
            return True
        except Exception as e:
            logger.error("OSS health check failed: %s", e)
            return False
