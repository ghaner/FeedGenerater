@echo off
cd /d "%~dp0"
echo ============================================
echo   通用 RSS 生成器（本地版）
echo   读取 sources.json，生成本地 *.xml 预览
echo ============================================
echo.
where python >nul 2>nul && set PY=python || set PY=py
%PY% "%~dp0src\generate_feed.py"
if errorlevel 1 (
  echo.
  echo [失败] 请确认：1) 已安装 Python 3；2) 本机能打开 sources.json 中的站点。
  pause
  exit /b 1
)
echo.
echo [完成] 已生成以下 feed（文件名见 sources.json 的 name）：
for %%f in (*.xml) do (
  echo   - %%f
  start "" "%%~dp0%%f"
)
echo        完整 URL 订阅版请用 publish.bat 推送到 GitHub Pages。
pause
