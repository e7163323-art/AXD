@echo off
chcp 65001 >nul
title Gaon Setup
echo.
echo   Gaon - starting setup window...
echo.
powershell.exe -NoProfile -ExecutionPolicy Bypass -STA -File "%~dp0install.ps1"
if errorlevel 1 (
  echo.
  echo   ERROR - please take a screenshot of this window.
  pause
)
