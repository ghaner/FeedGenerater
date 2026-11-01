# SeedHub「最近更新」RSS —— GitHub Pages 版

把 `https://seedog.cc/?order=update` 做成可被 **URL 订阅**的 RSS（供 Distill Web Monitor、Feedly、Fluent Reader 等只接受 URL 的阅读器使用）。

> 背景：seedog.cc 有 **Cloudflare** 且无原生 RSS。rsseverything 的服务器/代理 IP 被 Cloudflare 拦成「Just a moment…」挑战页，且无法粘贴源码，路线被墙死。
> 本仓库的解法：**在你本机（IP 受 Cloudflare 信任）抓取生成 `feed.xml`，推到 GitHub，由 GitHub Pages 提供公网 URL**。

---

## 一、仓库结构
```
seedog-rss/
├── .github/workflows/generate.yml   # 云端自动生成（可选实验，Cloudflare 拦则跳过，不破坏已有 feed）
├── src/generate_feed.py             # 主程序（仅 Python 标准库，无需 pip install）
├── feed.xml                         # 生成的 RSS（由 GitHub Pages 托管，订阅地址即它）
├── seedog_rss.bat                   # 本机一键生成并打开 feed.xml
├── publish.bat                     # 本机生成 + git 提交 + 推送（推荐的稳定刷新方式）
├── .gitignore                      # 已忽略 .workbuddy/ 与 build/
└── README.md
```

## 二、让你的阅读器拿到 URL（两步）

### 步骤 1：创建 GitHub 仓库并推送本仓库
1. 在 GitHub 新建一个**公开（Public）**仓库，命名为 `seedog-rss`（名字随意，记住它）。
2. 在本机仓库目录执行：
   ```bash
   git remote add origin https://github.com/<你的用户名>/seedog-rss.git
   git push -u origin main
   ```
3. 推送后，`feed.xml` 即进入仓库（首次已生成并随仓库提交）。

### 步骤 2：开启 GitHub Pages
1. 进入仓库 **Settings → Pages**（或 Settings → Code and automation → Pages）。
2. **Build and deployment → Source** 选 **Deploy from a branch**。
3. **Branch** 选 `main`，目录选 **`/ (root)`**，保存。
4. 稍等一两分钟，访问 `https://<你的用户名>.github.io/seedog-rss/feed.xml` 应能见到 RSS XML。
5. 把这个 URL 填进 Distill Web Monitor 的 **Feed → GET** 输入框即可订阅。

> 若访问后是下载文件而非网页，属正常——RSS 阅读器/Distill 会按 XML 解析。

## 三、如何保持更新

### 推荐：本机定时推（最稳，因为你的 IP 被 Cloudflare 信任）
双击 **`publish.bat`** 即可：生成 `feed.xml` → `git commit` → `git push`，Pages 自动更新。
要全自动，可在 Windows 任务计划程序里每天跑一次 `publish.bat`：
```bat
schtasks /create /tn "SeedHubRSS" /tr "F:\Informatics\RSS\RssEverything\2026-11-01_seedog_rss\publish.bat" /sc daily /st 08:00
```
（把路径换成你的实际路径；建议 `python`/`py` 在 PATH 中，且已配置 git 凭证。）

### 可选：GitHub Actions 云端自动生成
仓库里的 `.github/workflows/generate.yml` 会每 6 小时（UTC）尝试云端抓取并刷新 feed.xml。
**但云端 IP 大概率被 Cloudflare 拦截**——此时脚本提取不到条目、不改写 `feed.xml`，Action 自动跳过提交，**不会破坏已发布内容**。若某次云端成功（罕见），即自动更新。该 Action 是「有则更好」的实验项，不必强依赖。

## 四、提取字段
| 字段 | 含义 |
|---|---|
| 海报 | 影片封面图（绝对 URL） |
| 详情链接 | 补全为 `https://seedog.cc/movies/xxx/` 的绝对地址 |
| 片名 | 影片名 |
| 年份/类型/地区/语言/主演 | 如 `2026 / 剧集 / 中国大陆 / 汉语普通话 / 肖战 倪大红` |
| 分类 | 类型标签（如 `类型: 剧情`） |
| 豆瓣 | 豆瓣链接 + 评分（评分为 0 时显示「暂无」） |

## 五、配置项
集中在 `src/generate_feed.py` 顶部 `CONFIG`：`url` / `base` / `ua` / `timeout` / `output` / `feed_title` / `feed_desc` / `ttl`，一般无需改动。

## 六、注意事项
- 站点改版（如 cover 块标签变化）会使提取失效，需同步更新 `generate_feed.py` 里的正则；本机跑 `seedog_rss.bat` 可见报错。
- 若你本机也打不开 seedog.cc（被 Cloudflare 质询），说明本机 IP 也未被信任，本方案同样失效，需改用带可信住宅 IP 的中转抓取。
- `.workbuddy/` 含本地记忆，**已被 .gitignore 排除，不会上传到公开仓库**。
- 豆瓣评分为 0 表示站点尚未收录评分，已统一显示为「暂无」。
