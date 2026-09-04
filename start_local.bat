@echo off
title AURA - local hosting
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\serve_local.ps1"
pause
