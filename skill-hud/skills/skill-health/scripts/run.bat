@echo off
chcp 65001 >nul
cd /d "%~dp0"
python skill_health.py
pause
