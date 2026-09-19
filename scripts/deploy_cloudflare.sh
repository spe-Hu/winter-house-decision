#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════════════════════════
# 嘉定买房决策参谋系统 - Cloudflare Pages 一键全自动部署脚本 (免翻墙极速 CDN)
# ═══════════════════════════════════════════════════════════════════════════════

set -e

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${PROJECT_ROOT}"

echo "🚀 开始构建并推送项目至 Cloudflare Pages 全球 CDN 网络..."

# 1. 构建干净的部署分发目录
rm -rf dist
mkdir -p dist
cp -r index.html assets data dist/

# 2. 执行 wrangler pages deploy
echo "📦 正在上传静态资源至 Cloudflare Pages (winter-house-decision)..."
npx wrangler pages deploy dist --project-name winter-house-decision --branch main --commit-dirty=true

echo "✅ 部署完成！全球直连访问地址: https://winter-house-decision.pages.dev/"
