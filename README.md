# 通用「网址 → RSS」生成仓库（FeedGenerater）

把任意「按更新排序的列表页」做成可被 **URL 订阅**的 RSS（供 Distill Web Monitor、Feedly、Fluent Reader 等只接受 URL 的阅读器使用）。
**一个仓库支持多个网址，每个网址生成一个独立的 `<name>.xml`**，新增网址只需改 `sources.json`，无需改代码。

> 背景：seedog.cc、kkys14.com 这类站点都没有原生 RSS。本仓库用 GitHub Actions 在仓库内定时抓取并生成 RSS，再由 GitHub Pages 提供公网 URL；本机脚本仅作备用刷新。

---

## 一、仓库结构
```
FeedGenerater/
├── .github/workflows/generate.yml   # ★ 主生成器：每 6 小时（UTC）遍历所有源重新生成各自 *.xml
├── src/
│   ├── generate_feed.py             # 主程序（仅 Python 标准库，无需 pip install）
│   └── sources.json                 # ★ 站点配置：新增网址只改这里
├── seedog.xml                      # 生成的 RSS（seedog.cc，已由 Pages 托管）
├── kkys14.xml                      # （待启用：受 cdndefend 保护，暂未生成）
├── seedog_rss.bat                  # 本机一键生成并打开所有 *.xml（备用预览）
├── publish.bat                     # 本机生成 + git 提交 + 推送（备用刷新）
├── .gitignore
└── README.md
```

## 二、当前已配置的源（sources.json）
| name | 网址 | parser | 状态 |
|---|---|---|---|
| `seedog` | https://seedog.cc/?order=update | `seedog`（专用，已验证） | ✅ 正常，生成 `seedog.xml` |
| `kkys14` | https://www.kkys14.com/ | `generic` | ⏸️ 已禁用（`enabled:false`），原因见下 |

**kkys14 为何暂未启用**：该站受 **cdndefend JS 算力挑战**保护（HTTP 850 + “verifying your browser…”），
`urllib`/`curl` 无法解出真实页面（必须真实浏览器跑 JS 拿放行 cookie）。因此无法在本仓库用纯 Python 抓取，
其 `item_block` / `fields` 在 `sources.json` 里是**占位 TODO，未经验证**。要启用需先解决抓取（见第六节）。

## 三、让你的阅读器拿到 URL（两步）

### 步骤 1：开启 GitHub Pages
1. 仓库 **Settings → Pages**。
2. **Build and deployment → Source** 选 **Deploy from a branch**；**Branch** 选 `main`，目录 **`/ (root)`**，保存。
3. 稍等一两分钟，访问 `https://ghaner.github.io/FeedGenerater/seedog.xml` 应能见到 RSS XML。
4. 把这个 URL 填进 Distill Web Monitor 的 **Feed → GET** 输入框即可订阅。

> 每个源对应一个文件：`https://ghaner.github.io/FeedGenerater/<name>.xml`（name 见 sources.json）。

### 步骤 2：保持更新（★ GitHub Action 自动完成）
无需任何手动操作：`generate.yml` 每 **6 小时（UTC）** 自动遍历所有启用源 → 抓取 → 重新生成各自 `*.xml` → 提交推送。
- 若某次被反爬拦截（命中挑战页或提取 0 条），脚本**不覆盖**该 feed，保留上一次成功结果，订阅不中断。
- 周期在 `generate.yml` 的 `cron: "0 */6 * * *"` 调整（标准 cron，UTC）。
- 可在 **Actions → Generate RSS Feeds → Run workflow** 手动立即刷新。

## 四、如何新增一个网址（核心用法）
编辑 `src/sources.json`，在 `sources` 数组里加一条：
```json
{
  "name": "mysite",                       // 生成的文件名将是 mysite.xml
  "parser": "generic",                    // 规整站点用 generic；复杂站点可加专用 parser
  "url": "https://example.com/?order=new",
  "base": "https://example.com",
  "feed_title": "我的站点 最近更新",
  "feed_desc": "……",
  "ttl": 60,
  "item_block": "<div class=\"vod\">(.*?)</div>",   // 一个捕获组 = 一个条目块
  "fields": {                                       // 各字段正则
    "poster": {"pattern": "<img src=\"([^\"]+)\"", "group": 1, "abs": true},
    "link":   {"pattern": "href=\"([^\"]+)\"", "group": 1, "abs": true},
    "title":  {"pattern": "<h3>(.*?)</h3>", "group": 1, "strip_tags": true},
    "meta":   {"pattern": "<span>(.*?)</span>", "group": 1, "strip_tags": true}
  },
  "template": "<div><a href=\"{link}\"><img src=\"{poster}\"></a><b>{title}</b><p>{meta}</p></div>"
}
```
- 字段 `abs:true` 会把相对链接用 `base` 补成绝对地址；`strip_tags:true` 去掉 HTML 标签。
- `template` 是每条 `<description>` 的 HTML 卡片，`{字段名}` 会替换为提取结果。
- 提交推送后，Actions 会自动开始生成 `mysite.xml`。

## 五、本机使用
- **预览**：双击 `seedog_rss.bat` → 生成并打开所有 `*.xml`。
- **推送刷新**：双击 `publish.bat` → 生成 → `git commit` → `git push`，Pages 自动更新。

## 六、启用 kkys14（需先突破 cdndefend）
1. 用无头浏览器（Playwright / Selenium）携带真实 UA 打开 `https://www.kkys14.com/`，等 JS 挑战通过；
2. 取回渲染后的 HTML，定位影片条目块与字段，把 `sources.json` 里 kkys14 的 `item_block` / `fields` 填为真实正则；
3. 把 `"enabled": false` 改为 `true`（或删除该键），提交推送即可。

> 注意：GitHub Actions 的运行环境 IP 同样大概率被 cdndefend 拦，因此即使填好规则，云端也可能需改用「浏览器抓取」步骤（超出当前纯 Python 方案范围）。

## 七、配置项与注意事项
- `sources.json` 顶层 `ua` / `timeout` 为全局抓取参数。
- 站点改版（条目标签变化）会使提取失效；脚本会因此跳过该源、保留旧 feed，需同步更新对应正则。
- `.workbuddy/` 含本地记忆，已被 `.gitignore` 排除，不会上传到公开仓库。
- 豆瓣评分为 0 表示站点尚未收录，已统一显示为「暂无」。
