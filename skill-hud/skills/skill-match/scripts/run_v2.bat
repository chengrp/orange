@echo off
REM Skill-Match v2.0 运行脚本
echo ============================================
echo    Skill-Match 数据收集工具 v2.0
echo    优化版 - 支持缓存、重试、YAML
echo ============================================
echo.

cd /d "%~dp0"
python skill_match_v2.py

pause
