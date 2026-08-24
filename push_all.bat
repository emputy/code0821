@echo off
chcp 65001 >nul
cd /d D:\code0821
echo ==================================
echo  推送 GitHub...
echo ==================================
git push origin main
echo.
echo ==================================
echo  推送 Gitee...
echo ==================================
git push gitee main
echo.
echo ==================================
echo  全部完成！
echo ==================================
pause
