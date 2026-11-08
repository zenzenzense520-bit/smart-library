#!/usr/bin/env bash
set -euo pipefail

# 只停止由公网演示脚本记录的进程。
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "$(cygpath -w "$PWD/scripts/public-sites.ps1")" stop
