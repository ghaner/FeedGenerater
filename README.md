# SeedHub「最近更新」RSS —— GitHub 仓库自动生成版

把 `https://seedog.cc/?order=update` 做成可被 **URL 订阅**的 RSS（供 Distill Web Monitor、Feedly、Fluent Reader 等只接受 URL 的阅读器使用）。

> 背景：seedog.cc 有 **Cloudflare** 且无原生 RSS。rsseverything 的服务器/代理 IP 被 Cloudflare 拦成「Just a moment…」挑战页，且无法粘贴源码，路线被墙死。
> 本仓库的解法：**由 GitHub Actions 在仓库内定时抓取 seedog.cc 生成 `feed.xml`，再由 GitHub Pages 提供公网 URL**；本机脚本仅作为备用刷新手段。

---

## 一、仓库结构
```
seedog-rss/
├── .github/workflows/generate.yml   # ★ 主生成器：每 6 小时（UTC）定时抓取并重新生成 feed.xml
├── src/generate_feed.py             # 主程序（仅 Python 标准库，无需 pip install）
├── feed.xml                         # 生成的 RSS（由 GitHub Pages 托管，订阅地址即它）
├── seedog_rss.bat                   # 本机一键生成并打开 feed.xml（备用）
├── publish.bat                     # 本机生成 + git 提交 + 推送（备用刷新）
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
3. 推送后，`feed.xml` 已随仓库提交；GitHub Actions 之后会自动定时刷新它。

### 步骤 2：开启 GitHub Pages
1. 进入仓库 **Settings → Pages**（或 Settings → Code and automation → Pages）。
2. **Build and deployment → Source** 选 **Deploy from a branch**。
3. **Branch** 选 `main`，目录选 **`/ (root)`**，保存。
4. 稍等一两分钟，访问 `https://<你的用户名>.github.io/seedog-rss/feed.xml` 应能见到 RSS XML。
5. 把这个 URL 填进 Distill Web Monitor 的 **Feed → GET** 输入框即可订阅。

> 若访问后是下载文件而非网页，属正常——RSS 阅读器/Distill 会按 XML 解析。

## 三、如何保持更新（★ GitHub Action 自动完成）

**无需任何手动操作**：仓库内的 `.github/workflows/generate.yml` 会**每 6 小时（UTC）**自动：
1. 在 GitHub 运行环境抓取 `seedog.cc`（携带完整浏览器 UA、跟随跳转）；
2. 解析出 20 条影片、重新生成 `feed.xml`；
3. 仅在「提取到条目」时提交并推送；若被 Cloudflare 拦截（0 条目），则**跳过提交、保留上一次成功的 feed**，订阅不中断。

- 首次启用后，Actions 页面可看到运行记录；也可在 **Actions → Generate SeedHub RSS → Run workflow** 手动触发一次立即刷新。
- 周期可在 `generate.yml` 的 `cron: "0 */6 * * *"` 自行调整（标准 cron 表达式，UTC 时区）。

### 备用：本机手动刷新（当云端被拦时）
双击 **`publish.bat`** 即可：生成 `feed.xml` → `git commit` → `git push`，Pages 自动更新。

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
- 站点改版（如 cover 块标签变化）会使提取失效；云端 Action 会因此 0 条目并跳过，此时需同步更新 `generate_feed.py` 里的正则后重新推送。
- 若 GitHub 运行环境的 IP 也被 Cloudflare 持续拦截（罕见，但可能），云端将无法刷新，可改用本机 `publish.bat` 兜底。
- `.workbuddy/` 含本地记忆，**已被 .gitignore 排除，不会上传到公开仓库**。
- 豆瓣评分为 0 表示站点尚未收录评分，已统一显示为「暂无」。
