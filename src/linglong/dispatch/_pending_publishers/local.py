"""本地文件发布器

将生成的内容（文章或图片包）输出到本地目录。
"""

import logging
import shutil
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional

from ..publishers.base import Publisher, PublishResult

logger = logging.getLogger(__name__)


class LocalPublisher(Publisher):
    """本地文件发布器

    将内容写入本地文件系统，支持：
    1. 单篇文章输出（Markdown 文件）
    2. 图片包输出（zip 文件）
    3. 目录输出（保持文件结构）
    """

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.output_dir = Path(config.get("output_dir", "~/Downloads")).expanduser()
        self.naming_template = config.get("naming", "{name}_{date}")
        self.overwrite = config.get("overwrite", False)

    def publish(self, content: str, metadata: Dict[str, Any]) -> PublishResult:
        """发布内容到本地

        Args:
            content: 内容字符串（文章 Markdown 或图片包路径）
            metadata: 元数据，包含 title, date, tags 等

        Returns:
            PublishResult: 发布结果
        """
        try:
            # 判断内容类型
            content_path = Path(content)
            if content_path.exists() and content_path.suffix == ".zip":
                # 图片包模式
                return self._publish_zip(content_path, metadata)
            else:
                # 文章模式
                return self._publish_article(content, metadata)

        except Exception as e:
            logger.exception(f"本地发布失败: {e}")
            return PublishResult(success=False, error=str(e))

    def _publish_article(self, content: str, metadata: Dict[str, Any]) -> PublishResult:
        """发布单篇文章"""
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # 生成文件名
        date_str = metadata.get("date", datetime.now().strftime("%Y-%m-%d"))
        title = metadata.get("title", "untitled")
        safe_title = title.replace(" ", "_").replace("/", "_")[:30]

        filename = f"{date_str}_{safe_title}.md"
        output_path = self.output_dir / filename

        # 检查覆盖
        if output_path.exists() and not self.overwrite:
            logger.warning(f"文件已存在，跳过: {output_path}")
            return PublishResult(
                success=False,
                error=f"文件已存在: {output_path}",
            )

        # 写入文件
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(content)

        logger.info(f"文章已输出: {output_path}")
        return PublishResult(
            success=True,
            url=str(output_path),
            message=f"文章已保存到 {output_path}",
        )

    def _publish_zip(self, zip_path: Path, metadata: Dict[str, Any]) -> PublishResult:
        """发布图片包（复制 zip 到输出目录）"""
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # 生成输出文件名
        date_str = datetime.now().strftime("%Y%m%d")
        source_name = metadata.get("source", "images")
        count = metadata.get("image_count", len(metadata.get("images", [])))

        filename = f"{source_name}_{date_str}_{count}.zip"
        output_path = self.output_dir / filename

        # 检查覆盖
        if output_path.exists() and not self.overwrite:
            # 添加序号
            for i in range(1, 100):
                alt_filename = f"{source_name}_{date_str}_{count}_{i}.zip"
                alt_path = self.output_dir / alt_filename
                if not alt_path.exists():
                    output_path = alt_path
                    break

        # 复制文件
        shutil.copy2(zip_path, output_path)

        logger.info(f"图片包已输出: {output_path}")
        return PublishResult(
            success=True,
            url=str(output_path),
            message=f"图片包已保存到 {output_path}",
        )

    def health_check(self) -> bool:
        """检查输出目录是否可写"""
        try:
            self.output_dir.mkdir(parents=True, exist_ok=True)
            test_file = self.output_dir / ".write_test"
            test_file.touch()
            test_file.unlink()
            return True
        except Exception as e:
            logger.error(f"本地发布器健康检查失败: {e}")
            return False
