#!/usr/bin/env python3
"""Pre-commit hook: 检查代码改动是否需要同步更新文档。

读取 docs/doc-map.yaml 中的代码→文档映射，
对比 git diff --staged 的文件列表，
如果改了代码但没改对应文档，输出警告提醒。

退出码始终为 0，不阻塞提交。
仅使用标准库，无需虚拟环境。
"""

import re
import subprocess
import sys
from pathlib import Path


def get_staged_files() -> list[str]:
    result = subprocess.run(
        ["git", "diff", "--staged", "--name-only"],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return []
    return [f.strip() for f in result.stdout.strip().split("\n") if f.strip()]


def parse_yaml_mappings(text: str) -> list[dict]:
    """简易 YAML 解析，只处理 doc-map.yaml 的 flat 结构，避免依赖 PyYAML。"""
    mappings = []
    current = None

    for line in text.split("\n"):
        stripped = line.strip()
        if stripped.startswith("#") or not stripped:
            continue

        # 匹配 "- code: value" 或 "code: value"
        m = re.match(r"[- ]*code:\s*(.*)", stripped)
        if m:
            current = {"code": m.group(1).strip(), "docs": []}
            mappings.append(current)
            continue

        if current is not None:
            # 匹配 "- docs/path"
            m = re.match(r"-\s*(.+)", stripped)
            if m and not stripped.startswith("code:") and not stripped.startswith("docs:"):
                val = m.group(1).strip()
                current["docs"].append(val)

    return mappings


def load_doc_map() -> list[dict]:
    map_path = Path("docs/doc-map.yaml")
    if not map_path.exists():
        return []
    text = map_path.read_text()
    return parse_yaml_mappings(text)


def check(staged: list[str], mappings: list[dict]) -> list[str]:
    warnings = []
    staged_set = set(staged)

    for mapping in mappings:
        code_prefix = mapping["code"]
        doc_paths = mapping["docs"]

        if not code_prefix:
            continue

        code_hits = [f for f in staged if f.startswith(code_prefix)]
        if not code_hits:
            continue

        doc_staged = False
        for doc_path in doc_paths:
            if doc_path.endswith("/"):
                if any(f.startswith(doc_path) for f in staged_set):
                    doc_staged = True
                    break
            else:
                if doc_path in staged_set:
                    doc_staged = True
                    break

        if not doc_staged:
            code_files = ", ".join(code_hits[:3])
            if len(code_hits) > 3:
                code_files += f" (+{len(code_hits) - 3} more)"
            doc_list = ", ".join(doc_paths)
            warnings.append(
                f"  code changed: {code_files}\n"
                f"  → suggest checking: {doc_list}"
            )

    return warnings


def main():
    staged = get_staged_files()
    if not staged:
        sys.exit(0)

    code_extensions = {".py", ".ts", ".js", ".go", ".rs"}
    has_code = any(
        Path(f).suffix in code_extensions for f in staged
    )
    if not has_code:
        sys.exit(0)

    mappings = load_doc_map()
    if not mappings:
        sys.exit(0)

    warnings = check(staged, mappings)
    if warnings:
        YELLOW = "\033[33m"
        RESET = "\033[0m"
        print(f"{YELLOW}⚠️  doc-check: code changed without doc updates{RESET}")
        for w in warnings:
            print(f"{YELLOW}{w}{RESET}")

    sys.exit(0)


if __name__ == "__main__":
    main()
