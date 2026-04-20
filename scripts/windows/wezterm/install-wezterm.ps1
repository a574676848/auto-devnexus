$OutputEncoding = [Console]::InputEncoding = [Console]::OutputEncoding = [System.Text.Encoding]::UTF8

param(
    [switch]$ForceDownload,
    [string]$TargetUserProfile = [Environment]::GetFolderPath('UserProfile')
)

$ErrorActionPreference = 'Stop'

$scriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$templateDir = Join-Path $scriptRoot 'templates'
$weztermTemplatePath = Join-Path $templateDir 'wezterm.lua'
$cleanupBatSourcePath = Join-Path $scriptRoot 'cleanup-wezterm.bat'
$cleanupPs1SourcePath = Join-Path $scriptRoot 'cleanup-wezterm.ps1'
$imageHandlerSourcePath = Join-Path $scriptRoot 'wezterm-img-handler.ps1'

$configDir = Join-Path $TargetUserProfile '.config\wezterm'
$configPath = Join-Path $configDir 'wezterm.lua'
$cleanupBatPath = Join-Path $TargetUserProfile '.wezterm_cleanup.bat'
$cleanupPs1Path = Join-Path $TargetUserProfile '.wezterm_cleanup.ps1'
$imageHandlerPath = Join-Path $TargetUserProfile '.wezterm_img_handler.ps1'
$tempRoot = Join-Path $env:TEMP 'WezTermInstaller'
$downloadPath = Join-Path $tempRoot 'WezTerm-Setup.msi'

function Write-Utf8File {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Path,

        [Parameter(Mandatory = $true)]
        [string]$Content
    )

    $directory = Split-Path -Parent $Path
    if ($directory -and -not (Test-Path -LiteralPath $directory)) {
        New-Item -ItemType Directory -Path $directory -Force | Out-Null
    }

    $utf8NoBom = New-Object System.Text.UTF8Encoding($false)
    [System.IO.File]::WriteAllText($Path, $Content, $utf8NoBom)
}

function Write-Utf8FileFromSource {
    param(
        [Parameter(Mandatory = $true)]
        [string]$SourcePath,

        [Parameter(Mandatory = $true)]
        [string]$TargetPath
    )

    $content = Get-Content -LiteralPath $SourcePath -Encoding utf8 -Raw
    Write-Utf8File -Path $TargetPath -Content $content
}

function Backup-FileIfExists {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Path,

        [int]$KeepCount = 5
    )

    if (-not (Test-Path -LiteralPath $Path)) {
        return $null
    }

    $timestamp = Get-Date -Format 'yyyyMMdd_HHmmss'
    $backupPath = '{0}.bak_{1}' -f $Path, $timestamp
    Copy-Item -LiteralPath $Path -Destination $backupPath -Force

    $fileName = Split-Path -Leaf $Path
    $backupPattern = '{0}.bak_*' -f $fileName
    $backupFiles = Get-ChildItem -LiteralPath (Split-Path -Parent $Path) -File -Filter $backupPattern |
        Sort-Object LastWriteTime -Descending

    if ($backupFiles.Count -gt $KeepCount) {
        $expiredBackups = $backupFiles | Select-Object -Skip $KeepCount
        $expiredBackups | Remove-Item -Force
    }

    return $backupPath
}

function Test-WezTermInstalled {
    $commands = @(
        'wezterm.exe',
        (Join-Path $env:LOCALAPPDATA 'Programs\WezTerm\wezterm.exe'),
        (Join-Path ${env:ProgramFiles} 'WezTerm\wezterm.exe')
    )

    foreach ($candidate in $commands) {
        if ($candidate -eq 'wezterm.exe') {
            $command = Get-Command $candidate -ErrorAction SilentlyContinue
            if ($command) {
                return $true
            }

            continue
        }

        if (Test-Path -LiteralPath $candidate) {
            return $true
        }
    }

    return $false
}

function Install-WithWinget {
    $winget = Get-Command winget.exe -ErrorAction SilentlyContinue
    if (-not $winget) {
        return $false
    }

    Write-Host '检测到 winget，开始安装 WezTerm...'
    $arguments = @(
        'install',
        '--id', 'wez.wezterm',
        '--exact',
        '--accept-package-agreements',
        '--accept-source-agreements'
    )

    $process = Start-Process -FilePath $winget.Source -ArgumentList $arguments -Wait -PassThru -WindowStyle Hidden
    if ($process.ExitCode -ne 0) {
        Write-Warning "winget 安装失败，退出码：$($process.ExitCode)"
        return $false
    }

    return (Test-WezTermInstalled)
}

function Get-LatestMsiUrl {
    $releaseApi = 'https://api.github.com/repos/wezterm/wezterm/releases/latest'
    $headers = @{
        'Accept' = 'application/vnd.github+json'
        'User-Agent' = 'auto-devnexus-wezterm-installer'
    }

    $release = Invoke-RestMethod -Uri $releaseApi -Headers $headers
    $msiAsset = $release.assets | Where-Object {
        $_.name -match 'Windows.*x64.*\.msi$' -or $_.name -match 'setup.*\.msi$'
    } | Select-Object -First 1

    if (-not $msiAsset) {
        throw '未在最新 Release 中找到可用的 MSI 安装包。'
    }

    return $msiAsset.browser_download_url
}

function Install-WithDirectDownload {
    if (-not (Test-Path -LiteralPath $tempRoot)) {
        New-Item -ItemType Directory -Path $tempRoot -Force | Out-Null
    }

    $msiUrl = Get-LatestMsiUrl
    Write-Host "开始下载 WezTerm 安装包：$msiUrl"
    Invoke-WebRequest -Uri $msiUrl -OutFile $downloadPath

    Write-Host '开始执行 MSI 静默安装...'
    $msiArguments = @(
        '/i',
        ('"{0}"' -f $downloadPath),
        '/qn',
        '/norestart'
    )

    $process = Start-Process -FilePath 'msiexec.exe' -ArgumentList $msiArguments -Wait -PassThru
    if ($process.ExitCode -ne 0) {
        throw "MSI 安装失败，退出码：$($process.ExitCode)"
    }

    if (Test-Path -LiteralPath $downloadPath) {
        Remove-Item -LiteralPath $downloadPath -Force
    }
}

if (-not (Test-Path -LiteralPath $weztermTemplatePath)) {
    throw "未找到配置模板：$weztermTemplatePath"
}

Write-Host '开始写入 WezTerm 配置及辅助脚本...'
Write-Utf8FileFromSource -SourcePath $cleanupBatSourcePath -TargetPath $cleanupBatPath
Write-Utf8FileFromSource -SourcePath $cleanupPs1SourcePath -TargetPath $cleanupPs1Path
Write-Utf8FileFromSource -SourcePath $imageHandlerSourcePath -TargetPath $imageHandlerPath
$configBackupPath = Backup-FileIfExists -Path $configPath -KeepCount 5
Write-Utf8FileFromSource -SourcePath $weztermTemplatePath -TargetPath $configPath

if ($ForceDownload -or -not (Test-WezTermInstalled)) {
    $installed = Install-WithWinget
    if (-not $installed) {
        Install-WithDirectDownload
    }
}
else {
    Write-Host '检测到 WezTerm 已安装，跳过安装步骤，仅重置配置。'
}

if (-not (Test-WezTermInstalled)) {
    throw '脚本执行完成后仍未检测到 WezTerm，请手动检查安装日志。'
}

Write-Host ''
Write-Host 'WezTerm 安装与配置已完成。'
Write-Host "配置文件：$configPath"
if ($configBackupPath) {
    Write-Host "旧配置备份：$configBackupPath"
}
Write-Host "清理脚本：$cleanupBatPath"
Write-Host "清理脚本：$cleanupPs1Path"
Write-Host "图片处理：$imageHandlerPath"
