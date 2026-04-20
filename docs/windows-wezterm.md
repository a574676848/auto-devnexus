# Windows WezTerm 一键安装脚本

本文档说明仓库内置的 WezTerm Windows 自动化脚本如何使用、会生成哪些文件，以及重复执行时的行为。

## 目录位置

仓库脚本位于：

```text
scripts/windows/wezterm/
├── install-wezterm.bat
├── install-wezterm.ps1
├── cleanup-wezterm.bat
├── cleanup-wezterm.ps1
├── wezterm-img-handler.ps1
└── templates/
    └── wezterm.lua
```

## 功能说明

- 自动检测 WezTerm 是否已安装。
- 已安装时跳过安装，仅重置用户侧配置文件。
- 未安装时优先使用 `winget` 安装，失败后回退到 GitHub Release 下载最新 MSI 并静默安装。
- 自动生成用户目录下的 WezTerm 配置与辅助脚本。
- 覆盖 `wezterm.lua` 前自动备份旧配置，并且只保留最近 5 份备份。
- 启动 WezTerm 时自动清理临时图片目录中的旧截图。
- `Ctrl+V` 支持优先处理剪贴板图片，保存为临时 PNG 路径后再粘贴。

## 安装与使用

在仓库根目录执行：

```powershell
.\scripts\windows\wezterm\install-wezterm.bat
```

或者直接执行 PowerShell 版本：

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\windows\wezterm\install-wezterm.ps1
```

如果要强制重新下载安装 WezTerm：

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\windows\wezterm\install-wezterm.ps1 -ForceDownload
```

## 生成文件

脚本会在当前用户目录下生成以下文件：

```text
%USERPROFILE%\.config\wezterm\wezterm.lua
%USERPROFILE%\.wezterm_cleanup.bat
%USERPROFILE%\.wezterm_cleanup.ps1
%USERPROFILE%\.wezterm_img_handler.ps1
```

## 备份与清理策略

- 如果 `%USERPROFILE%\.config\wezterm\wezterm.lua` 已存在，覆盖前会先备份为：
  `%USERPROFILE%\.config\wezterm\wezterm.lua.bak_yyyyMMdd_HHmmss`
- 备份文件只保留最近 5 份，旧备份会在本次执行中自动清理。
- 临时图片目录默认位于 `%TEMP%\WezTerm_Images`。
- 清理脚本默认删除 1 天前的 PNG 文件。

## 手动执行清理脚本

```powershell
.\scripts\windows\wezterm\cleanup-wezterm.bat
```

或者：

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\windows\wezterm\cleanup-wezterm.ps1 -RetentionDays 1
```

## 注意事项

- 当前脚本面向 Windows 本机环境，不适用于 WSL。
- 若系统没有 `winget`，脚本会自动尝试 GitHub Release MSI 安装链路。
- `wezterm.lua` 模板默认使用 `C:\Program Files\PowerShell\7\pwsh.exe` 作为默认 Shell。
- 如果你的 PowerShell 7 安装路径不同，需要手动调整模板文件 `scripts/windows/wezterm/templates/wezterm.lua`。
