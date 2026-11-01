@echo off
cd /d "%~dp0"
echo ============================================
echo   SeedHub「最近更新」RSS 生成器（本地版）
echo   绕过 Cloudflare：在你本机 IP 上抓取
echo ============================================
echo.
where python >nul 2>nul && set PY=python || set PY=py
%PY% "%~dp0src\generate_feed.py"
if errorlevel 1 (
  echo.
  echo [失败] 请确认：1) 已安装 Python 3（命令 python 或 py 可用）；2) 本机能打开 seedog.cc。
  pause
  exit /b 1
)
if exist "%~dp0build\feed.xml" start "" "%~dp0build\feed.xml"
echo.
echo [完成] build\feed.xml 已生成并用默认程序打开。
echo        把该文件拖进 RSS 阅读器即可订阅；重跑本脚本可刷新。
echo        窗口将在 8 秒后自动关闭...
timeout /t 8 /nobreak >nul
