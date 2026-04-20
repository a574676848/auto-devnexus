@echo off
chcp 65001 > nul
set SCRIPT_DIR=%~dp0
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%SCRIPT_DIR%install-wezterm.ps1"
echo.
pause
