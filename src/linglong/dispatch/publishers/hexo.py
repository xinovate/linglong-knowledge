import logging
import os
import subprocess
from pathlib import Path
from typing import Any

from linglong.core.config import get_config
from linglong.dispatch.publishers.base import Publisher, PublishResult

logger = logging.getLogger(__name__)


class HexoPublisher(Publisher):
    """
    Hexo 博客发布器

    发布流程:
    1. 生成 Markdown 文件到 Hexo source/_posts 目录
    2. 执行 hexo generate
    3. 执行 hexo deploy (可选)
    """

    def __init__(self, config: dict[str, Any]):
        super().__init__(config)
        self.hexo_path = Path(config.get("hexo_path", "~/blog")).expanduser()
        self.posts_path = self.hexo_path / "source" / "_posts"
        self.auto_deploy = config.get("auto_deploy", False)
        self.use_git_workflow = config.get("use_git_workflow", False)
        self.git_remote = config.get("git_remote", "origin")
        self.git_branch = config.get("git_branch", "master")
        self.git_proxy = config.get("git_proxy")
        self.ssh_host = config.get("ssh_host")
        default_ssh = get_config().dispatch.hexo_deploy_command
        self.ssh_command = config.get("ssh_command", default_ssh)
        self.site_url = config.get("site_url", get_config().dispatch.hexo_site_url).rstrip("/")

    def publish(self, content: str, metadata: dict[str, Any]) -> PublishResult:
        """发布到 Hexo 博客"""
        try:
            self.posts_path.mkdir(parents=True, exist_ok=True)

            filename = self._generate_filename(metadata)
            file_path = self.posts_path / filename

            file_path.write_text(content, encoding="utf-8")

            if self.use_git_workflow:
                return self._git_publish(file_path, metadata, filename)
            else:
                return self._local_publish(file_path, metadata, filename)

        except Exception as e:
            return PublishResult(success=False, error=str(e))

    def health_check(self) -> bool:
        """检查 Hexo 环境"""
        if not self.hexo_path.exists():
            return False

        if self.use_git_workflow:
            result = subprocess.run(
                ["git", "-C", str(self.hexo_path), "rev-parse", "--git-dir"], capture_output=True
            )
            return result.returncode == 0
        else:
            result = subprocess.run(["hexo", "--version"], capture_output=True)
            return result.returncode == 0

    def _git_publish(
        self, file_path: Path, metadata: dict[str, Any], filename: str
    ) -> PublishResult:
        """Git 工作流：add → commit → push"""
        try:
            title = metadata.get("title", "untitled")

            env = os.environ.copy()
            if self.git_proxy:
                env["HTTP_PROXY"] = self.git_proxy
                env["HTTPS_PROXY"] = self.git_proxy

            # 1. git add
            add_result = subprocess.run(
                ["git", "-C", str(self.hexo_path), "add", str(file_path)],
                capture_output=True,
                text=True,
                env=env,
            )
            if add_result.returncode != 0:
                return PublishResult(success=False, error=f"git add 失败: {add_result.stderr}")

            # 2. git commit
            commit_msg = f"auto: {title}"
            commit_result = subprocess.run(
                ["git", "-C", str(self.hexo_path), "commit", "-m", commit_msg],
                capture_output=True,
                text=True,
                env=env,
            )
            if commit_result.returncode != 0:
                # No-op if nothing changed
                if (
                    "nothing to commit" in commit_result.stdout
                    or "nothing to commit" in commit_result.stderr
                ):
                    pass
                else:
                    return PublishResult(
                        success=False, error=f"git commit 失败: {commit_result.stderr}"
                    )

            # 3. git push
            push_result = subprocess.run(
                ["git", "-C", str(self.hexo_path), "push", self.git_remote, self.git_branch],
                capture_output=True,
                text=True,
                env=env,
            )
            if push_result.returncode != 0:
                return PublishResult(success=False, error=f"git push 失败: {push_result.stderr}")

            if self.ssh_host:
                logger.info("SSH remote trigger: %s", self.ssh_host)
                ssh_result = subprocess.run(
                    ["ssh", self.ssh_host, self.ssh_command],
                    capture_output=True,
                    text=True,
                )
                if ssh_result.returncode != 0:
                    logger.warning("SSH remote trigger failed: %s", ssh_result.stderr)
                    return PublishResult(
                        success=True,
                        url=f"{self.site_url}/{metadata.get('slug', '')}",
                        message=f"文章已提交并推送: {filename}（SSH 触发失败: {ssh_result.stderr.strip()[:100]}）",
                    )
                else:
                    logger.info("SSH remote trigger succeeded")

            return PublishResult(
                success=True,
                url=f"{self.site_url}/{metadata.get('slug', '')}",
                message=f"文章已提交并推送: {filename}",
            )

        except Exception as e:
            return PublishResult(success=False, error=str(e))

    def _local_publish(
        self, file_path: Path, metadata: dict[str, Any], filename: str
    ) -> PublishResult:
        """Local 工作流：hexo generate → deploy"""
        try:
            result = subprocess.run(
                ["hexo", "generate"], cwd=self.hexo_path, capture_output=True, text=True
            )

            if result.returncode != 0:
                return PublishResult(success=False, error=f"hexo generate 失败: {result.stderr}")

            if self.auto_deploy:
                deploy_result = subprocess.run(
                    ["hexo", "deploy"], cwd=self.hexo_path, capture_output=True, text=True
                )

                if deploy_result.returncode != 0:
                    return PublishResult(
                        success=False, error=f"hexo deploy 失败: {deploy_result.stderr}"
                    )

            return PublishResult(
                success=True,
                url=f"{self.site_url}/{metadata.get('slug', '')}",
                message=f"文章已发布: {filename}",
            )

        except Exception as e:
            return PublishResult(success=False, error=str(e))

    def _generate_filename(self, metadata: dict[str, Any]) -> str:
        """生成文件名"""
        title = metadata.get("title", "untitled")
        date = metadata.get("date", "")

        clean_title = title.replace(" ", "-").replace("/", "-").replace("\\", "-")

        if date:
            return f"{date}-{clean_title}.md"
        else:
            return f"{clean_title}.md"
