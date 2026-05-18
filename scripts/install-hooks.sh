#!/bin/bash
# 安装 git hooks
# 用法: bash scripts/install-hooks.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
HOOKS_SRC="$SCRIPT_DIR/hooks"
HOOKS_DST="$(git rev-parse --git-dir)/hooks"

echo "Installing git hooks..."

for hook in "$HOOKS_SRC"/*; do
    hook_name=$(basename "$hook")
    dst="$HOOKS_DST/$hook_name"
    cp "$hook" "$dst"
    chmod +x "$dst"
    echo "  ✓ $hook_name"
done

echo "Done. Hooks installed to $HOOKS_DST"
