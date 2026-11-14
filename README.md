# 通用「网址 → RSS」生成仓库（FeedGenerater）

把任意「按更新排序的列表页」做成可被 **URL 订阅**的 RSS（供 Distill Web Monitor、Feedly、Fluent Reader 等只接受 URL 的阅读器使用）。
**一个仓库支持多个网址，每个网址生成一个独立的 `<name>.xml`**，新增网址只需改 `sources.json`，无需改代码。

> 背景：seedog.cc、kkys14.com 这类站点都没有原生 RSS。本仓库用 GitHub Actions 在仓库内定时抓取并生成 RSS，再由 GitHub Pages 提供公网 URL；本机脚本仅作备用刷新。

---

## 一、仓库结构
```
FeedGenerater/
├── .github/workflows/generate.yml   # ★ 主生成器：每日零点（北京时间）遍历所有源重新生成各自 *.xml
├── src/
│   ├── generate_feed.py             # 主程序（仅 Python 标准库，无需 pip install）
│   └── sources.json                 # ★ 站点配置：新增网址只改这里
├── *.xml                           # 生成的 RSS（seedog / yszzq / yszzq_api / yszzq_jiexi，已由 Pages 托管）
├── test/capture_kkys14.py          # 调试脚本：浏览器抓取（暂停中的 kkys14 后续攻坚用）
├── seedog_rss.bat                  # 本机一键生成并打开所有 *.xml（备用预览）
├── publish.bat                     # 本机生成 + git 提交 + 推送（备用刷新）
├── .gitignore
└── README.md
```

## 二、当前已配置的源（sources.json）
| name | 网址 | parser | 状态 |
|---|---|---|---|
| `seedog` | https://seedog.cc/?order=update | `seedog`（专用，已验证） | ✅ 正常，生成 `seedog.xml`（20 条） |
| `yszzq` | https://www.yszzq.com/ziyuan/web/19_0_0_0_newstime_0.html | `generic`（已验证） | ✅ 正常，生成 `yszzq.xml`（24 条，资源站官网列表） |
| `yszzq_api` | https://www.yszzq.com/ziyuan/api/20_0_0_0_newstime_0.html | `generic`（已验证） | ✅ 正常，生成 `yszzq_api.xml`（**10 条/页，已过滤「失效」接口**，标题旁以灰色小标签标「赞助」） |
| `yszzq_jiexi` | https://www.yszzq.com/ziyuan/jiexi/21_0_0_newstime_0.html | `generic`（已验证） | ✅ 正常，生成 `yszzq_jiexi.xml`（**11 条/页，已过滤「失效」接口**，含解析地址 / 收费 / 格式，标题旁标「赞助」） |
| `kkys14` | https://www.kkys14.com/label/new.html（目标页） | `generic` + `fetch:"browser"` | ⏸️ 已暂停（`enabled:false`），暂不出源，原因见下 |

**kkys14 为何暂停**：该站是 **SPA + cdndefend JS 算力挑战**。`urllib` 直连只能拿到 HTTP 850 挑战页；
生成器里已内置 `fetch:"browser"`（Playwright 跑 JS 过挑战、取渲染后 HTML，并支持 `wait_selector` / `settle` / `limit`），
本机用浏览器确实能过挑战拿到渲染结果（对首页 HTML 离线验证出 81 条影片规则），
但放进生成器流程后 `fetch_browser` 多次只返回**未渲染的空壳**（0 条），SPA 内容就绪的判定尚未调通。
因此按用户要求**先暂停该源**，其余源不受任何影响；`sources.json` 中它的 `item_block` / `fields`
仅对首页结构有效，对 `label/new.html` **未经验证**，恢复前必须重新校准。

> 说明：暂停的是「kkys14 这个源」，**多源引擎完整保留**——`sources.json` 配置驱动、`generic` 正则解析、
> `fetch:"browser"` 浏览器抓取三条能力都在，随时可给新网址加源。

## 三、让你的阅读器拿到 URL（两步）

### 步骤 1：开启 GitHub Pages
1. 仓库 **Settings → Pages**。
2. **Build and deployment → Source** 选 **Deploy from a branch**；**Branch** 选 `main`，目录 **`/ (root)`**，保存。
3. 稍等一两分钟，访问 `https://ghaner.github.io/FeedGenerater/seedog.xml` 应能见到 RSS XML。
4. 把这个 URL 填进 Distill Web Monitor 的 **Feed → GET** 输入框即可订阅。

> 每个源对应一个文件：`https://ghaner.github.io/FeedGenerater/<name>.xml`（name 见 sources.json）。

### 步骤 2：保持更新（★ GitHub Action 自动完成）
无需任何手动操作：`generate.yml` 每 **日零点（北京时间，即 UTC 16:00）** 自动遍历所有启用源 → 抓取 → 重新生成各自 `*.xml` → 提交推送。
- 若某次被反爬拦截（命中挑战页或提取 0 条），脚本**不覆盖**该 feed，保留上一次成功结果，订阅不中断。
- 周期在 `generate.yml` 的 `cron: "0 16 * * *"`（标准 cron，**UTC**）调整；若想改回 UTC 零点则写 `0 0 * * *`，想改回北京时间零点则写 `0 16 * * *`。
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
- `fetch` 可选值：
  - `"http"`（默认）：`urllib` 直连，最快，适合无 JS 挑战的站点。
  - `"browser"`：Playwright 无头浏览器，能跑 JS 过 cdndefend / Cloudflare 挑战、并等待 SPA 渲染完再取 HTML；
    较慢，需要本机或 CI 先装 `pip install playwright && python -m playwright install chromium`，
    并可配 `wait_selector`（等某元素出现）、`settle`（额外稳定秒数）、`limit`（最多取几条）。
- `limit`：只保留前 N 条（首页常混入推荐位/专题位，用它控制条目数）。
- 提交推送后，Actions 会自动开始生成 `mysite.xml`。

## 五、本机使用
- **预览**：双击 `seedog_rss.bat` → 生成并打开所有 `*.xml`。
- **推送刷新**：双击 `publish.bat` → 生成 → `git commit` → `git push`，Pages 自动更新。

## 六、kkys14（已暂停，后续恢复步骤）

现状（勿误判为「已可用」）：
- 目标页：`https://www.kkys14.com/label/new.html`；`sources.json` 里该源 `enabled:false`，**不产出任何文件**。
- 抓取能力已有：`fetch:"browser"` + `test/capture_kkys14.py`，本机能过 cdndefend 拿到渲染后 HTML。
- 卡点：在生成器流程内 `fetch_browser` 多次只取到 SPA **未渲染的空壳**（0 条目），`wait_selector` 命中过早；
  且现有正则来自**首页**快照，对 `label/new.html` 未验证。

恢复时按序做：
1. 用 `test/capture_kkys14.py`（把 url 改成 `.../label/new.html`）抓一份真实渲染 HTML，确认条目真实存在于 DOM；
2. 针对该页重新推导 `item_block` / `fields`（注意排除 `h-item` 专题块，只认 `a.v-item` 影片块）；
3. 修 `fetch_browser` 的 SPA 等待逻辑（例如等方法 `page.wait_for_function` 计数达阈值，而非仅等元素存在）；
4. 本地跑 `python src/generate_feed.py` 确认 kkys14 稳定出条目后，再把 `enabled` 改回 `true`；
5. 云端还需在 `generate.yml` 里加装 Playwright + Chromium 的步骤（CI 的 IP 同样可能被 cdndefend 拦）。

> 备选更快路线：若该站实际有隐藏的 JSON 数据接口（XHR），直接改抓接口比解析 DOM 稳得多。

## 七、配置项与注意事项
- `sources.json` 顶层 `ua` / `timeout` 为全局抓取参数。
- 站点改版（条目标签变化）会使提取失效；脚本会因此跳过该源、保留旧 feed，需同步更新对应正则。
- `.workbuddy/` 含本地记忆，已被 `.gitignore` 排除，不会上传到公开仓库。
- 豆瓣评分为 0 表示站点尚未收录，已统一显示为「暂无」。
