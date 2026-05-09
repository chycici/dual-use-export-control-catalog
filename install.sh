#!/usr/bin/env bash
# dual-use-export-control-catalog — 一键安装 Hermes Agent Skill
set -euo pipefail

REPO_OWNER="${REPO_OWNER:-chycici}"
REPO_NAME="${REPO_NAME:-dual-use-export-control-catalog}"
BRANCH="${BRANCH:-main}"
SKILL_NAME="dual-use-export-control-catalog"
HERMES_HOME="${HERMES_HOME:-$HOME/.hermes}"
SKILL_DIR="$HERMES_HOME/skills/$SKILL_NAME"

echo "📦 安装 $SKILL_NAME ..."
mkdir -p "$SKILL_DIR/data"

BASE_URL="https://raw.githubusercontent.com/$REPO_OWNER/$REPO_NAME/$BRANCH/skills/$SKILL_NAME"

echo "  下载 SKILL.md ..."
curl -fsSL "$BASE_URL/SKILL.md" -o "$SKILL_DIR/SKILL.md"

echo "  下载搜索脚本 ..."
curl -fsSL "$BASE_URL/search.py" -o "$SKILL_DIR/search.py"

echo "  下载检索索引（524KB）..."
curl -fsSL "$BASE_URL/data/2026年度两用物项进出口许可证检索索引.json" -o "$SKILL_DIR/data/2026年度两用物项进出口许可证检索索引.json"

echo "  下载完整知识库（1.3MB）..."
curl -fsSL "$BASE_URL/data/2026年度两用物项进出口许可证统一知识库.json" -o "$SKILL_DIR/data/2026年度两用物项进出口许可证统一知识库.json"

# 完整性校验
if [ -f "$SKILL_DIR/SKILL.md" ] && [ -f "$SKILL_DIR/search.py" ] && [ -f "$SKILL_DIR/data/2026年度两用物项进出口许可证检索索引.json" ]; then
  chmod +x "$SKILL_DIR/search.py"
  echo "✅ $SKILL_NAME 安装完成 → $SKILL_DIR"
else
  echo "❌ 下载失败，请检查网络连接"
  exit 1
fi
