param(
    [ValidateSet('start', 'stop', 'status')]
    [string]$Action = 'status'
)

$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
$runtimeDir = Join-Path $projectRoot '.runtime\public-sites'
$logDir = Join-Path $projectRoot 'logs'
$pythonPath = Join-Path $projectRoot 'backend\.venv\Scripts\python.exe'
$sshPath = Join-Path $env:WINDIR 'System32\OpenSSH\ssh.exe'
$sshKeygenPath = Join-Path $env:WINDIR 'System32\OpenSSH\ssh-keygen.exe'
$tunnelKeyPath = Join-Path $runtimeDir 'tunnel_ed25519'

# 三个站点各自使用独立端口，避免静态资源绝对路径彼此冲突。
$sites = @(
    [pscustomobject]@{ Name = 'smart-library'; Port = 43101; Root = (Join-Path $projectRoot 'dist'); Kind = 'vite'; RemoteSlot = 1; TunnelPattern = 'https://[a-z0-9.-]+\.srv\.us' },
    [pscustomobject]@{ Name = 'polity-lens'; Port = 43102; Root = 'D:\新建文件夹 (3)\dist'; Kind = 'vite'; RemoteSlot = 2; TunnelPattern = 'https://[a-z0-9.-]+\.srv\.us' },
    [pscustomobject]@{ Name = 'contradiction-analyzer'; Port = 43103; Root = 'D:\contradiction-analyzer'; Kind = 'python'; RemoteSlot = 3; TunnelPattern = 'https://[a-z0-9.-]+\.srv\.us' }
)

function Ensure-Directories {
    New-Item -ItemType Directory -Force -Path $runtimeDir, $logDir | Out-Null
}

function Get-PidPath([string]$name, [string]$role) {
    Join-Path $runtimeDir "$name-$role.pid"
}

function Read-LivePid([string]$path) {
    if (-not (Test-Path -LiteralPath $path)) { return $null }
    $processId = [int](Get-Content -LiteralPath $path -Raw)
    if (Get-Process -Id $processId -ErrorAction SilentlyContinue) { return $processId }
    Remove-Item -LiteralPath $path -Force
    return $null
}

function Start-LoggedProcess {
    param(
        [string]$name,
        [string]$role,
        [string]$filePath,
        [string[]]$argumentList,
        [string]$workingDirectory
    )

    $pidPath = Get-PidPath $name $role
    $existingPid = Read-LivePid $pidPath
    if ($existingPid) {
        Write-Output "[运行中] $name/$role PID=$existingPid"
        return
    }

    $stdoutPath = Join-Path $logDir "$name-$role.out.log"
    $stderrPath = Join-Path $logDir "$name-$role.err.log"
    Remove-Item -LiteralPath $stdoutPath, $stderrPath -Force -ErrorAction SilentlyContinue
    $process = Start-Process -FilePath $filePath -ArgumentList $argumentList `
        -WorkingDirectory $workingDirectory -WindowStyle Hidden -PassThru `
        -RedirectStandardOutput $stdoutPath -RedirectStandardError $stderrPath
    Set-Content -LiteralPath $pidPath -Value $process.Id -NoNewline
    Write-Output "[已启动] $name/$role PID=$($process.Id)"
}

function Wait-LocalSite([int]$port) {
    $url = "http://127.0.0.1:$port/"
    foreach ($attempt in 1..30) {
        try {
            $response = Invoke-WebRequest -Uri $url -UseBasicParsing -TimeoutSec 2
            if ($response.StatusCode -eq 200) { return }
        } catch {
            Start-Sleep -Milliseconds 500
        }
    }
    throw "本地站点启动失败：$url"
}

function Start-Sites {
    Ensure-Directories
    if (-not (Test-Path -LiteralPath $pythonPath)) { throw "缺少 Python 运行环境：$pythonPath" }
    if (-not (Test-Path -LiteralPath $sshPath)) { throw "缺少 Windows OpenSSH：$sshPath" }
    if (-not (Test-Path -LiteralPath $tunnelKeyPath)) {
        # 临时隧道密钥仅保存在被 Git 忽略的 .runtime 目录，不注册外部账户。
        $keygenProcess = Start-Process -FilePath $sshKeygenPath `
            -ArgumentList @('-q', '-t', 'ed25519', '-N', '""', '-f', "`"$tunnelKeyPath`"") `
            -WindowStyle Hidden -Wait -PassThru
        if ($keygenProcess.ExitCode -ne 0) { throw '生成临时 SSH 密钥失败。' }
    }

    # 智慧图书馆后端与前端共享一个公网入口，/api 由 Vite 转发。
    Start-LoggedProcess -name 'smart-library-api' -role 'server' -filePath $pythonPath `
        -argumentList @('manage.py', 'runserver', '127.0.0.1:43100', '--noreload') `
        -workingDirectory (Join-Path $projectRoot 'backend')

    foreach ($site in $sites) {
        if (-not (Test-Path -LiteralPath $site.Root)) { throw "站点目录不存在：$($site.Root)" }
        if ($site.Kind -eq 'vite') {
            $siteProject = if ($site.Name -eq 'smart-library') { $projectRoot } else { 'D:\新建文件夹 (3)' }
            Start-LoggedProcess -name $site.Name -role 'server' -filePath 'cmd.exe' `
                -argumentList @('/d', '/c', "npm run preview -- --host 127.0.0.1 --port $($site.Port)") `
                -workingDirectory $siteProject
        } else {
            Start-LoggedProcess -name $site.Name -role 'server' -filePath $pythonPath `
                -argumentList @('-m', 'http.server', "$($site.Port)", '--bind', '127.0.0.1', '--directory', $site.Root) `
                -workingDirectory $site.Root
        }
        Wait-LocalSite $site.Port
    }

    foreach ($site in $sites) {
        # srv.us 用同一临时密钥的不同远端槽位分配三个独立 HTTPS 地址。
        $tunnelTarget = 'srv.us'
        $tunnelPortArgs = @()
        $remoteForward = "$($site.RemoteSlot):127.0.0.1:$($site.Port)"
        $identityArgs = @('-i', $tunnelKeyPath)
        $tunnelArgs = @('-T') + $tunnelPortArgs + $identityArgs + @('-o', 'BatchMode=yes', '-o', 'StrictHostKeyChecking=accept-new', '-o', 'ServerAliveInterval=30', '-o', 'ExitOnForwardFailure=yes', '-R', $remoteForward, $tunnelTarget)
        Start-LoggedProcess -name $site.Name -role 'tunnel' -filePath $sshPath `
            -argumentList $tunnelArgs `
            -workingDirectory $projectRoot
    }

    Start-Sleep -Seconds 6
    Show-Status
}

function Stop-Sites {
    Ensure-Directories
    Get-ChildItem -LiteralPath $runtimeDir -Filter '*.pid' -File | ForEach-Object {
        $processId = Read-LivePid $_.FullName
        if ($processId) {
            # Vite 由 cmd.exe 拉起，必须结束整棵进程树，避免旧 Node 子进程继续占用端口。
            & "$env:WINDIR\System32\taskkill.exe" /PID $processId /T /F 2>$null | Out-Null
            Write-Output "[已停止] $($_.BaseName) PID=$processId"
        }
        Remove-Item -LiteralPath $_.FullName -Force -ErrorAction SilentlyContinue
    }
    foreach ($port in @(43100, 43101, 43102, 43103)) {
        Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue | ForEach-Object {
            & "$env:WINDIR\System32\taskkill.exe" /PID $_.OwningProcess /T /F 2>$null | Out-Null
        }
    }
}

function Show-Status {
    Ensure-Directories
    foreach ($site in $sites) {
        $serverPid = Read-LivePid (Get-PidPath $site.Name 'server')
        $tunnelPid = Read-LivePid (Get-PidPath $site.Name 'tunnel')
        $tunnelLog = Join-Path $logDir "$($site.Name)-tunnel.out.log"
        $publicUrl = if (Test-Path -LiteralPath $tunnelLog) {
            # 每个服务只提取其实际分配域名，排除欢迎信息中的文档链接。
            Select-String -LiteralPath $tunnelLog -Pattern $site.TunnelPattern -AllMatches | ForEach-Object { $_.Matches.Value } | Select-Object -Last 1
        }
        Write-Output ("{0}`t本地={1}`t穿透={2}`t地址={3}" -f $site.Name, $(if ($serverPid) { '运行中' } else { '停止' }), $(if ($tunnelPid) { '运行中' } else { '停止' }), $(if ($publicUrl) { $publicUrl } else { '等待生成' }))
    }
    $apiPid = Read-LivePid (Get-PidPath 'smart-library-api' 'server')
    Write-Output ("smart-library-api`t本地={0}" -f $(if ($apiPid) { '运行中' } else { '停止' }))
}

switch ($Action) {
    'start' { Start-Sites }
    'stop' { Stop-Sites }
    'status' { Show-Status }
}
