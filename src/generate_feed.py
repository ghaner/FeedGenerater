# -*- coding: utf-8 -*-
"""
通用「网址 → RSS」生成器（本地版，绕开反爬）
==========================================
把任意「按更新排序的列表页」做成标准 RSS 2.0，每个网址一个 <域名>.xml。
全部逻辑由仓库根目录的 sources.json 驱动：新增一个网址 = 在 sources 里加一条配置，
无需改代码（简单站点用 parser:"generic" + 正则；复杂站点可加一个专用 parser 函数）。

依赖：仅 Python 标准库（urllib + re + xml），无需 pip install。
用法：python src/generate_feed.py
输出：仓库根目录 <name>.xml（由 GitHub Pages 以 https://<用户>.github.io/<仓库>/<name>.xml 提供公网订阅 URL）

字段说明（seedog 示例，与 rsseverything 项目可重复搜索模式一一对应）：
  poster 海报图URL(绝对) | link 详情绝对链接 | title 片名
  meta 年份/类型/地区/语言/主演 | cats 分类 | douban 豆瓣链接(绝对) | douban_rate 豆瓣评分
"""

import os
import re
import sys
import json
import datetime
from urllib.request import Request, urlopen
from urllib.parse import urlparse
from xml.sax.saxutils import escape

# ===================== 路径解析（无论从哪个工作目录调用都正确） =====================
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(SCRIPT_DIR)
CONFIG_PATH = os.path.join(SCRIPT_DIR, "sources.json")

# ===================== 反爬挑战页特征（命中则跳过该源，保留旧 feed） =====================
CHALLENGE_MARKERS = [
    "cdndefend", "verifying your browser", "just a moment",
    "cf-mitigated", "challenges.cloudflare.com",
]

# ===================== seedog.cc 专用解析（已用真实页面验证） =====================
COVER_RE = re.compile(r'<div class="cover">(.*?</ul>\s*</div>)', re.S)
UL_RE = re.compile(r'<ul>(.*?)</ul>', re.S)
LI_RE = re.compile(r'<li>(.*?)</li>', re.S)
IMG_RE = re.compile(r'<img[^>]*src="([^"]+)"', re.S)
IMAGE_HREF_RE = re.compile(r'class="image"[^>]*href="([^"]+)"', re.S)
TITLE_RE = re.compile(r'header-anchor">#</a>\s*([^<]+)</h2>', re.S)
HREF_RE = re.compile(r'href="([^"]+)"', re.S)
TAG_RE = re.compile(r'<[^>]+>')


def strip_tags(html):
    if html is None:
        return ""
    return TAG_RE.sub("", html).strip()


def parse_seedog(html, cfg):
    """seedog.cc 的提取逻辑（verified）。返回 item 列表。"""
    base = cfg.get("base", "")
    items = []
    for block in COVER_RE.findall(html):
        poster = IMG_RE.search(block)
        poster = poster.group(1) if poster else ""

        detail = IMAGE_HREF_RE.search(block)
        detail_rel = detail.group(1) if detail else ""
        detail_abs = detail_rel if detail_rel.startswith("http") else base + detail_rel

        title_m = TITLE_RE.search(block)
        title = strip_tags(title_m.group(1)) if title_m else "(未知片名)"

        ul = UL_RE.search(block)
        meta = cats = douban_link = douban_rate = ""
        if ul:
            lis = LI_RE.findall(ul.group(1))
            # lis[0]=含 h2 标题; lis[1]=年份/类型/地区/语言/主演; lis[2]=分类; lis[3]=豆瓣
            if len(lis) > 1:
                meta = strip_tags(lis[1])
            if len(lis) > 2:
                cats = strip_tags(lis[2])
            if len(lis) > 3:
                douban = lis[3]
                dm = HREF_RE.search(douban)
                douban_link = dm.group(1) if dm else ""
                rm = re.search(r'>([^<]*)</a>', douban)
                douban_rate = rm.group(1).strip() if rm else ""

        rate = douban_rate if (douban_rate and douban_rate != "0") else "暂无"
        items.append({
            "poster": poster,
            "link": detail_abs,
            "title": title,
            "meta": meta,
            "cats": cats,
            "douban": douban_link,
            "douban_rate": douban_rate,
            "rate": rate,
        })
    return items


def parse_generic(html, cfg):
    """通用配置驱动解析：item_block 捕获条目块，fields 定义各字段正则。
    适用结构较规整的站点；字段支持 group / strip_tags / abs(补全绝对链接)。"""
    ib = re.compile(cfg["item_block"], re.S)
    field_cfgs = cfg.get("fields", {})
    base = cfg.get("base", "")
    items = []
    for block in ib.findall(html):
        item = {}
        for fname, fc in field_cfgs.items():
            flags = re.S | (re.I if fc.get("i") else 0)
            m = re.search(fc["pattern"], block, flags)
            val = ""
            if m:
                val = m.group(fc.get("group", 1))
                if fc.get("strip_tags"):
                    val = strip_tags(val)
                if fc.get("abs"):
                    val = val if val.startswith("http") else base + val
            item[fname] = val
        if "douban_rate" in item:
            item["rate"] = item["douban_rate"] if (item["douban_rate"] and item["douban_rate"] != "0") else "暂无"
        items.append(item)
    return items


def filter_excluded(items, cfg):
    """按配置剔除条目：cfg.exclude = {"field": 字段名, "values": [命中值...]}。
    字段值包含任一 values 即丢弃（如 status 为「失效」的解析接口）。未配置则原样返回。"""
    rule = cfg.get("exclude")
    if not rule:
        return items
    field_name = rule.get("field", "")
    values = rule.get("values", [])
    kept = []
    for it in items:
        val = str(it.get(field_name, ""))
        if any(v in val for v in values):
            continue
        kept.append(it)
    return kept


PARSERS = {
    "seedog": parse_seedog,
    "generic": parse_generic,
}


# ===================== 网络与构建 =====================
def fetch(url, ua, timeout):
    req = Request(url, headers={"User-Agent": ua, "Accept-Language": "zh-CN,zh;q=0.9"})
    with urlopen(req, timeout=timeout) as resp:
        raw = resp.read()
    enc = resp.headers.get_content_charset() or "utf-8"
    try:
        return raw.decode(enc, errors="replace")
    except LookupError:
        return raw.decode("utf-8", errors="replace")


def fetch_browser(url, ua, timeout, max_wait=40, wait_selector=None, settle=5):
    """用 Playwright 无头浏览器跑 JS 通过反爬挑战（cdndefend / Cloudflare 等），返回渲染后的真实 HTML。
    仅在源配置 fetch:"browser" 时调用；playwright 未安装或抓取失败会抛异常，由上层捕获后跳过该源。

    wait_selector: 挑战解除后，再等待该 CSS 选择器出现（SPA 站点用它确认内容已渲染）。
    settle: 额外稳定等待秒数，确保异步数据写入 DOM。
    """
    import time
    from playwright.sync_api import sync_playwright

    html = ""
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=["--disable-blink-features=AutomationControlled", "--no-sandbox"],
        )
        ctx = browser.new_context(
            user_agent=ua,
            locale="zh-CN",
            viewport={"width": 1280, "height": 800},
        )
        page = ctx.new_page()
        # 抹掉 webdriver 特征，降低被识别为自动化的概率
        page.add_init_script(
            "Object.defineProperty(navigator,'webdriver',{get:()=>undefined})"
        )
        page.goto(url, wait_until="domcontentloaded", timeout=timeout * 1000)
        # 轮询等待挑战解除（JS 算力挑战通常需要几秒）
        deadline = time.time() + max_wait
        while time.time() < deadline:
            html = page.content()
            low = html.lower()
            if not any(m in low for m in CHALLENGE_MARKERS):
                break
            time.sleep(2)
        # SPA 站点：等内容选择器出现 + 稳定时间，否则拿到的是空壳
        if wait_selector:
            try:
                page.wait_for_selector(wait_selector, timeout=timeout * 1000)
            except Exception:
                pass
        if settle:
            time.sleep(settle)
        html = page.content()
        browser.close()
    return html


def build_rss(items, cfg):
    now = datetime.datetime.now(datetime.timezone.utc).strftime("%a, %d %b %Y %H:%M:%S +0000")
    tpl = cfg.get("template", "<div>{title}<br>{link}</div>")
    parts = ['<?xml version="1.0" encoding="UTF-8"?>', '<rss version="2.0">', '  <channel>']
    parts.append('    <title>%s</title>' % escape(cfg["feed_title"]))
    parts.append('    <link>%s</link>' % escape(cfg.get("url", "")))
    parts.append('    <description>%s</description>' % escape(cfg.get("feed_desc", "")))
    parts.append('    <language>zh-CN</language>')
    parts.append('    <lastBuildDate>%s</lastBuildDate>' % now)
    parts.append('    <ttl>%d</ttl>' % cfg.get("ttl", 60))

    for it in items:
        desc = tpl.format(**{k: escape(str(v)) for k, v in it.items()})
        parts.append('    <item>')
        parts.append('      <title>%s</title>' % escape(it.get("title", "")))
        parts.append('      <link>%s</link>' % escape(it.get("link", "")))
        parts.append('      <guid>%s</guid>' % escape(it.get("link", "")))
        parts.append('      <description><![CDATA[%s]]></description>' % desc)
        parts.append('    </item>')

    parts.append('  </channel>')
    parts.append('</rss>')
    return "\n".join(parts)


def process_source(cfg, ua, timeout):
    name = cfg["name"]
    print("\n=== 处理源：%s (%s) ===" % (name, cfg.get("url", "")))
    if cfg.get("enabled") is False:
        print("  ⏭️  已在配置中禁用（enabled:false），跳过。")
        return
    parser = PARSERS.get(cfg.get("parser", "generic"))
    if parser is None:
        print("  ❌ 未知 parser: %s，跳过。" % cfg.get("parser"))
        return

    fetch_mode = cfg.get("fetch", "http")
    try:
        if fetch_mode == "browser":
            print("  🌐 使用浏览器抓取（攻克 JS 挑战）...")
            html = fetch_browser(
                cfg["url"], ua, timeout,
                max_wait=cfg.get("max_wait", 40),
                wait_selector=cfg.get("wait_selector"),
                settle=cfg.get("settle", 5),
            )
        else:
            html = fetch(cfg["url"], ua, timeout)
    except Exception as e:
        print("  ⚠️  抓取失败：%s（跳过，保留旧 feed）" % e)
        return

    low = html.lower()
    if any(m in low for m in CHALLENGE_MARKERS):
        print("  ⚠️  命中反爬挑战页（如 cdndefend/Cloudflare），无法获取真实内容，跳过。")
        return

    items = parser(html, cfg)
    raw_count = len(items)
    items = filter_excluded(items, cfg)
    if len(items) != raw_count:
        print("      已按 exclude 规则剔除 %d 条（保留 %d 条）" % (raw_count - len(items), len(items)))
    if cfg.get("limit"):
        items = items[: cfg["limit"]]
    print("      提取到 %d 条" % len(items))
    if not items:
        print("  ⚠️  未提取到条目（可能页面结构已变或被拦），跳过，保留旧 feed。")
        return

    rss = build_rss(items, cfg)
    out_path = os.path.join(REPO_ROOT, name + ".xml")
    os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(rss)
    print("  ✅ 已写入 %s（%d 条）" % (out_path, len(items)))


def main():
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        conf = json.load(f)
    ua = conf.get("ua", "Mozilla/5.0")
    timeout = conf.get("timeout", 40)
    sources = conf.get("sources", [])
    print("读取配置：%d 个源" % len(sources))
    for cfg in sources:
        process_source(cfg, ua, timeout)
    print("\n全部源处理完毕。")


if __name__ == "__main__":
    main()
