$OutputEncoding = [Console]::InputEncoding = [Console]::OutputEncoding = [System.Text.Encoding]::UTF8

param(
    [int]$RetentionDays = 1
)

$ErrorActionPreference = 'Stop'

function Remove-StaleFiles {
    param(
        [Parameter(Mandatory = $true)]
        [string]$TargetPath,

        [Parameter(Mandatory = $true)]
        [int]$Days
    )

    if (-not (Test-Path -LiteralPath $TargetPath)) {
        Write-Host "目录不存在，无需清理：$TargetPath"
        return
    }

    $expiredAt = (Get-Date).AddDays(-$Days)
    $removedFiles = Get-ChildItem -LiteralPath $TargetPath -File -Filter '*.png' |
        Where-Object { $_.LastWriteTime -lt $expiredAt }

    if (-not $removedFiles) {
        Write-Host '没有需要清理的旧图片。'
        return
    }

    $removedFiles | Remove-Item -Force
    Write-Host "已清理 $($removedFiles.Count) 个超过 $Days 天的图片文件。"
}

$imageCachePath = Join-Path $env:TEMP 'WezTerm_Images'
Remove-StaleFiles -TargetPath $imageCachePath -Days $RetentionDays
