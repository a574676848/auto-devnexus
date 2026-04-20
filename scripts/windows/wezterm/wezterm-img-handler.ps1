$OutputEncoding = [Console]::InputEncoding = [Console]::OutputEncoding = [System.Text.Encoding]::UTF8

$ErrorActionPreference = 'Stop'

try {
    Add-Type -AssemblyName System.Windows.Forms
    Add-Type -AssemblyName System.Drawing

    $clipboardImage = [System.Windows.Forms.Clipboard]::GetImage()
    if ($null -eq $clipboardImage) {
        exit 1
    }

    $tempDir = Join-Path $env:TEMP 'WezTerm_Images'
    if (-not (Test-Path -LiteralPath $tempDir)) {
        New-Item -ItemType Directory -Path $tempDir -Force | Out-Null
    }

    $fileName = 'img_{0}.png' -f (Get-Date -Format 'yyyyMMdd_HHmmssfff')
    $filePath = Join-Path $tempDir $fileName

    $clipboardImage.Save($filePath, [System.Drawing.Imaging.ImageFormat]::Png)
    Write-Output $filePath
}
catch {
    Write-Error "处理剪贴板图片失败：$($_.Exception.Message)"
    exit 1
}
