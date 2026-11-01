@echo off
REM ============================================================
REM  SeedHub RSS —— 本机生成并推送到 GitHub（推荐的稳定更新方式）
REM  前置：1) 本机能打开 seedog.cc（IP 受 Cloudflare 信任）
REM        2) 已 git remote add origin <你的仓库URL>
REM        3) 已登录 git 凭证（或配置 SSH / PAT）
REM ============================================================
cd /d "%~dp0"

REM --- 1) 选择 python 解释器（兼容 python / py）---
where python >nul 2>nul && set "PY=python"
where py >nul 2>nul && set "PY=py"
if not defined PY (
  echo [错误] 未找到 Python，请先安装 Python 3.6+。
  pause & exit /b 1
)

REM --- 2) 生成 feed.xml（脚本内部已做 Cloudflare/空结果校验）---
echo [1/4] 生成 feed.xml ...
"%PY%" "%~dp0src\generate_feed.py"
if errorlevel 1 (
  echo [失败] 生成出错（可能本机 IP 也被 Cloudflare 质询）。未做任何改动。
  pause & exit /b 1
)

REM --- 3) 先拉取远端最新（rebase，避免冲突）---
echo [2/4] 拉取远端最新 ...
git pull --rebase --autostash || (
  echo [警告] git pull 失败，将继续尝试本地提交/推送。
)

REM --- 4) 提交并推送（仅当 feed.xml 有变化）---
echo [3/4] 提交并推送 ...
git add feed.xml
git diff --cached --quiet feed.xml
if errorlevel 1 (
  git commit -m "chore: refresh feed.xml (local)"
  git push && echo [4/4] 已推送，GitHub Pages 将自动更新。 || (
    echo [失败] 推送被拒绝，请先 git pull 解决冲突后再运行。
    pause & exit /b 1
  )
) else (
  echo [4/4] feed.xml 无变化，无需推送。
)
echo 完成。订阅地址：https://ghaner.github.io/FeedGenerater/feed.xml
pause
