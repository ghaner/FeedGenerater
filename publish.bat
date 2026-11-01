@echo off
REM ============================================================
REM  通用 RSS 生成器 —— 本机生成并推送到 GitHub（备用刷新方式）
REM  前置：1) 本机能打开 sources.json 中配置的站点（IP 受信任）
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

REM --- 2) 生成全部 feed（脚本遍历 sources.json，内部已做反爬/空结果校验）---
echo [1/4] 生成 RSS（遍历 sources.json 中所有启用源）...
"%PY%" "%~dp0src\generate_feed.py"
if errorlevel 1 (
  echo [失败] 生成出错。未做任何改动。
  pause & exit /b 1
)

REM --- 3) 先拉取远端最新（rebase，避免冲突）---
echo [2/4] 拉取远端最新 ...
git pull --rebase --autostash || (
  echo [警告] git pull 失败，将继续尝试本地提交/推送。
)

REM --- 4) 提交并推送（仅当 *.xml 有变化）---
echo [3/4] 提交并推送 ...
git add -A "*.xml"
git diff --cached --quiet
if errorlevel 1 (
  git commit -m "chore: refresh feeds (local)"
  git push && echo [4/4] 已推送，GitHub Pages 将自动更新。 || (
    echo [失败] 推送被拒绝，请先 git pull 解决冲突后再运行。
    pause & exit /b 1
  )
) else (
  echo [4/4] 各 feed 无变化，无需推送。
)
echo 完成。订阅地址形如：https://ghaner.github.io/FeedGenerater/^<name^>.xml（name 见 sources.json）
pause
