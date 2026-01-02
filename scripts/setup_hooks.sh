#!/bin/bash
# RoyalBot Git Hooks 安装脚本
#
# 运行此脚本安装 Git hooks: bash scripts/setup_hooks.sh

set -e

echo "🔧 安装 RoyalBot Git Hooks..."

# 复制 hooks
cp .githooks/pre-commit .git/hooks/pre-commit
chmod +x .git/hooks/pre-commit

echo "✅ Git Hooks 安装完成！"
echo ""
echo "已安装的 hooks:"
echo "  - pre-commit: 提交前运行代码检查"
echo ""
echo "跳过检查: git commit --no-verify"
