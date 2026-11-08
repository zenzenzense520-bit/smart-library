#!/usr/bin/env bash
set -euo pipefail

# 所有公网演示服务统一从该脚本启动，日志写入项目 logs/。
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "$(cygpath -w "$PWD/scripts/public-sites.ps1")" start
