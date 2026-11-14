# 通用「网址 → RSS」生成仓库（WebFeedGitHubGenerater）

把任意「按更新排序的列表页」做成可被 **URL 订阅**的 RSS（供 Distill Web Monitor、Feedly、Fluent Reader 等只接受 URL 的阅读器使用）。
**一个仓库支持多个网址，每个网址生成一个独立的 `<name>.xml`**，新增网址只需改 `sources.json`，无需改代码。

> 背景：seedog.cc、kkys14.com 这类站点都没有原生 RSS。本仓库用 GitHub Actions 在仓库内定时抓取并生成 RSS，再由 GitHub Pages 提供公网 URL；本机脚本仅作备用刷新。

---

## 一、仓库结构
```
WebFeedGitHubGenerater/
├── .github/workflows/generate.yml   # ★ 主生成器：每日零点（北京时间）遍历所有源重新生成各自 *.xml
├── src/
│   ├── generate_feed.py             # 主程序（仅 Python 标准库，无需 pip install）
│   └── sources.json                 # ★ 站点配置：新增网址只改这里
├── *.xml                           # 生成的 RSS（seedog / yszzq / yszzq_api / yszzq_jiexi / cctv_jkzl / kkys14，已由 Pages 托管）
├── test/                           # 调试与探测脚本（推导抓取手段用，不参与正式生成）
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
| `cctv_jkzl` | https://tv.cctv.com/lm/jkzl/index.shtml（接口：`api.cntv.cn/NewVideo/getVideoListByColumn`） | `json`（已验证） | ✅ 正常，生成 `cctv_jkzl.xml`（**50 条**，含播出时间 `pubDate`、时长、节目简介、竖版海报） |
| `kkys14` | https://www.kkys14.com/label/new.html | `generic` + cookie 直连 | ✅ 正常，生成 `kkys14.xml`（**24 条**，含竖版海报） |

**kkys14 怎么通的**：该站有 cdndefend JS 算力挑战，直连会得到 HTTP 850 挑战页；但**挑战通过后发放的
`cdndefend_js_cookie` 是静态值**（多轮独立会话取值一致），带上它 `urllib` 直连即返回 200 与完整的**服务端渲染 HTML**
（实测 1.06 秒 / 24 条，且不校验 UA）。所以这个源**不需要 Playwright、也不需要等 SPA 渲染**。
站点另有反调试跳转（约 3.9 秒后跳到百度），这正是原先"取到 0 条"的真正原因；现在完全绕过 DOM，不受影响。
cookie 若被站点轮换，`cookie_recovery` 会自动用浏览器刷新一次后重连（详见第六章）。

## 三、让你的阅读器拿到 URL（两步）

### 步骤 1：开启 GitHub Pages
1. 仓库 **Settings → Pages**。
2. **Build and deployment → Source** 选 **Deploy from a branch**；**Branch** 选 `main`，目录 **`/ (root)`**，保存。
3. 稍等一两分钟，访问 `https://ghaner.github.io/WebFeedGitHubGenerater/seedog.xml` 应能见到 RSS XML。
4. 把这个 URL 填进 Distill Web Monitor 的 **Feed → GET** 输入框即可订阅。

> 每个源对应一个文件：`https://ghaner.github.io/WebFeedGitHubGenerater/<name>.xml`（name 见 sources.json）。

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
    注意：`generate.yml` **当前没有**安装 Playwright 的步骤（现有源都走 http/json），若启用 browser 源需自行加装。
- `limit`：只保留前 N 条（首页常混入推荐位/专题位，用它控制条目数）。
- 源级 `headers`：自定义请求头，如 `{"Cookie": "cdndefend_js_cookie=..."}`。用于「挑战页发放静态 cookie 后即可直连」的站点，不填则不发额外头（行为与原来一致）。
- `cookie_recovery` / `cookie_name` / `cookie_wait`：cookie 自愈开关与参数，见第六章。
- 字段级 `base`：`fields.<名>.base` 可单独指定补全域名，用于「正文在主域、图片在另一台域名」的站（kkys14 的海报就走 `vres.*`）。不填则回落到源级 `base`。
- 提交推送后，Actions 会自动开始生成 `mysite.xml`。

### 4.1 站点有 JSON 接口时用 `parser:"json"`（比解析 HTML 稳得多）

很多站点的列表是前端 XHR 拉 JSON 渲染的（CCTV 就是此类），HTML 里没有条目，正则无从下手。
此时直接抓接口，用 `parser:"json"`：

```json
{
  "name": "cctv_jkzl",
  "parser": "json",
  "url": "https://api.cntv.cn/NewVideo/getVideoListByColumn?id=TOPC1451557646802924&n=50&sort=desc&p=1&d=&mode=0&serviceId=tvcctv",
  "base": "https://tv.cctv.com",
  "feed_title": "CCTV《健康之路》最新节目",
  "feed_link": "https://tv.cctv.com/lm/jkzl/index.shtml",
  "tz": "+0800",
  "items_path": "data.list",
  "fields": {
    "link":  {"key": "url", "abs": true},
    "title": {"key": "title", "strip_tags": true},
    "date":  {"key": "time", "date": "%Y-%m-%d %H:%M:%S"}
  },
  "template": "<div><b><a href=\"{link}\">{title}</a></b><p>{date}</p></div>"
}
```

| 配置项 | 含义 |
|---|---|
| `items_path` | 条目数组在 JSON 中的点号路径（如 `data.list`），取到非数组则视为 0 条并跳过该源 |
| `fields.*.key` | 该字段对应的 JSON 键（支持 `data.list.0.title` 这类点号路径） |
| `fields.*.strip_tags` / `abs` | 同 `generic`：去 HTML 标签 / 用 `base` 补全相对链接 |
| `fields.*.date` | 时间格式（`strptime` 语法）。命中后自动生成 `<pubDate>`，阅读器可按发布时间排序 |
| `tz` | 上述时间所在时区，默认 `+0800`（北京时间），直接写入 RSS 的 `pubDate` |
| `feed_link` | `<channel><link>` 指向的人类可读页面（不填则用 `url`，接口型源建议填） |

**CCTV 栏目页怎么找接口与栏目 ID**：打开栏目页 → 查看源码里 `var topicID = 'TOPC…'`（如《健康之路》=`TOPC1451557646802924`）
→ 接口模板 `https://api.cntv.cn/NewVideo/getVideoListByColumn?id=<topicID>&n=50&sort=desc&p=<页码>&d=&mode=0&serviceId=tvcctv`。
换栏目只改 `id`；`n` 控制条数（实测 50 可用），`sort=desc` 保证最新在前。该接口普通 `urllib` 直连即可，无需 Referer/浏览器。

## 五、本机使用
- **预览**：双击 `seedog_rss.bat` → 生成并打开所有 `*.xml`。
- **推送刷新**：双击 `publish.bat` → 生成 → `git commit` → `git push`，Pages 自动更新。

## 六、kkys14 的 cookie 通道（原理与维护）

### 原理（2026-11-14 实测结论）
- `/label/new.html` 是**服务端渲染**，不是 SPA：挑战通过后主文档直接返回完整 HTML（约 87KB、24 条 `a.v-item`）。
  监听全部网络请求只有 2 个 JSON（站点公告、广告位配置），**没有任何影片数据接口**。
- 静态直连 → HTTP 850 挑战页；挑战通过后浏览器拿到 `cdndefend_js_cookie`，该值是**静态的**
  （3 轮独立会话取值完全一致，`expires=-1`），带上它直连即 200，且换任意 UA 都有效。
- 站点有反调试跳转：约 **3.9 秒后页面自动跳往 `www.baidu.com`**。所以「等渲染后取 DOM」只有约 1 秒窗口，
  极易拿到百度页；走 cookie 直连则完全不受影响。这也是原先"提取 0 条"的真正原因（不是 SPA 未渲染）。

### 当前配置（sources.json 对应片段）
```json
"headers": {"Cookie": "${KKYS14_COOKIE}"},
"cookie_recovery": true,
"cookie_name": "cdndefend_js_cookie",
"cookie_wait": 4
```

cookie **不写进仓库**，通过环境变量 `KKYS14_COOKIE` 注入（值形如 `cdndefend_js_cookie=<45位值>`）：

| 运行环境 | 注入方式 |
|---|---|
| 本机 | `src/local_secrets.json`（已加入 `.gitignore`）：`{"KKYS14_COOKIE": "cdndefend_js_cookie=..."}`，生成器启动时自动载入 |
| GitHub Actions | 仓库 **Settings → Secrets and variables → Actions → New repository secret**，名称 `KKYS14_COOKIE`；`generate.yml` 已把它作为同名环境变量传入 |

> 环境变量缺失时日志会打印 `⚠️ 环境变量未设置：KKYS14_COOKIE`，并尝试用浏览器刷新 cookie；CI 未装 playwright 时该源被跳过、旧 feed 保留。

### cookie 失效了怎么换
现象：日志出现 `⚠️ 直连结果无效（HTTP Error 850）`，随后自动刷新重连。若刷新也失败（例如未装 playwright），
该源会被跳过、旧 `kkys14.xml` 保留，订阅不中断。更新只需两步：
1. 浏览器打开 `https://www.kkys14.com/label/new.html`，等页面加载完；
2. F12 → Application → Cookies → `https://www.kkys14.com` → 复制 `cdndefend_js_cookie` 的值，拼成
   `cdndefend_js_cookie=<值>`，写进本机 `src/local_secrets.json` 的 `KKYS14_COOKIE`；
   云端则到 **Settings → Secrets → KKYS14_COOKIE** 更新为同一字符串。

> 辅助脚本：`test/probe_kkys14_cookie_stability.py`（批量取 cookie 并校验一致性与可用性）、
> `test/probe_kkys14_timeline.py`（复现页面跳转时序）、`test/verify_kkys14_pure_http.py`（验证纯 HTTP 通道）。

### 为什么不再用 fetch:"browser"
浏览器通道要与「3.9 秒跳百度」抢时间，站点一改跳转时机就失效；cookie 通道 1 秒完成，CI 也不必装 chromium。
`fetch:"browser"` 能力仍保留在生成器中，供其他 SPA 站点使用。

## 七、配置项与注意事项
- `sources.json` 顶层 `ua` / `timeout` 为全局抓取参数。
- 站点改版（条目标签变化）会使提取失效；脚本会因此跳过该源、保留旧 feed，需同步更新对应正则。
- `.workbuddy/` 含本地记忆，已被 `.gitignore` 排除，不会上传到公开仓库。
- 豆瓣评分为 0 表示站点尚未收录，已统一显示为「暂无」。
