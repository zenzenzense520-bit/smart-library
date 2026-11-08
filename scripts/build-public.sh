#!/usr/bin/env bash
set -euo pipefail

# 公网版本使用同源 /api，避免访问者浏览器请求自己的 localhost。
export VITE_API_BASE_URL=/api
npm run build
