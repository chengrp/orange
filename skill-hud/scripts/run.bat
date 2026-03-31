@echo off
chcp 65001 > nul
cd /d "%~dp0"

echo ========================================
echo    Skill-HUD 综合仪表板
echo ========================================
echo.
echo 说明：
echo   整合所有子技能的数据
echo   生成综合仪表板报告
echo   一目了然查看全貌
echo.
echo ========================================
echo.

python hud_dashboard.py

echo.
echo ========================================
echo 按任意键打开报告...
pause > nul

start ..\\reports\\SKILLS_综合分析_最新.md
