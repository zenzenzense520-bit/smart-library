#!/usr/bin/env bash
set -euo pipefail

# 汇总三个站点和智慧图书馆 API 的当前状态。
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "$(cygpath -w "$PWD/scripts/public-sites.ps1")" status
