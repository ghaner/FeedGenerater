# -*- coding: utf-8 -*-
"""
SeedHub「最近更新」RSS 生成器（本地版，绕开 Cloudflare）
========================================================
适用场景：
  rsseverything 因 Cloudflare 墙（其服务器/代理 IP 被拦、且站点无原生 RSS）无法直接抓取
  seedog.cc。本脚本在你【自己机器】上运行——你的 IP 被 Cloudflare 信任，能正常拉到 20 条，
  再用与 rsseverything 验证过的同款提取逻辑生成标准 RSS 2.0 XML。

依赖：仅 Python 标准库（urllib + re + xml），无需 pip install。
用法：python generate_feed.py
输出：仓库根目录 <域名>.xml（文件名由站点域名自动推导，如 seedog.cc → seedog.xml；由 GitHub Pages 以
      https://<用户名>.github.io/<仓库>/seedog.xml 提供公网订阅 URL）

提取逻辑（与 rsseverything 项目可重复搜索模式一一对应）：
  {%1} 海报图URL(绝对) | {%2} 详情相对链接 | {%3} 片名
  {%4} 年份/类型/地区/语言/主演 | {%5} 分类(不定数量链接) | {%6} 豆瓣链接(绝对) | {%7} 豆瓣评分
"""

import os
import re
import sys
import datetime
from urllib.request import Request, urlopen
from urllib.parse import urlparse
from xml.sax.saxutils import escape

# ===================== 参数配置区（按需修改） =====================
# 输出路径一律基于脚本所在目录解析，无论从哪个工作目录调用都正确
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(SCRIPT_DIR)


def domain_to_filename(base_url):
    """由站点域名推导 feed 文件名，作为唯一数据源：
       seedog.cc       -> seedog.xml
       www.example.com -> example.xml
    取主机名的二级域名（倒数第二段）作文件名，避免硬编码 feed.xml。"""
    host = (urlparse(base_url).hostname or "").lower()
    labels = [p for p in host.split(".") if p]
    slug = labels[-2] if len(labels) >= 2 else (labels[0] if labels else "feed")
    return slug + ".xml"


CONFIG = {
    "url": "https://seedog.cc/?order=update",   # 目标页（按最近更新排序）
    "base": "https://seedog.cc",                 # 站点域名：用于补全绝对链接，并推导 feed 文件名
    "ua": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
          "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "timeout": 40,                               # 请求超时（秒）
    # 生成的 RSS 文件路径（仓库根，供 Pages 服务）；文件名由 base 域名自动推导（seedog.cc → seedog.xml）
    "output": os.path.join(REPO_ROOT, domain_to_filename("https://seedog.cc")),
    "feed_title": "SeedHub 最近更新（影视&动漫）",
    "feed_desc": "SeedHub 影视&动漫分享站，按「最近更新」排序的影片 RSS 订阅源（本地生成，绕开 Cloudflare）。",
    "ttl": 60,                                   # 阅读器缓存分钟数
}
# ===============================================================

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


def fetch(url, ua, timeout):
    req = Request(url, headers={"User-Agent": ua, "Accept-Language": "zh-CN,zh;q=0.9"})
    with urlopen(req, timeout=timeout) as resp:
        raw = resp.read()
    # 优先按声明编码解码，失败回退 utf-8
    enc = resp.headers.get_content_charset() or "utf-8"
    try:
        return raw.decode(enc, errors="replace")
    except LookupError:
        return raw.decode("utf-8", errors="replace")


def parse_items(html):
    items = []
    for block in COVER_RE.findall(html):
        poster = IMG_RE.search(block)
        poster = poster.group(1) if poster else ""

        detail = IMAGE_HREF_RE.search(block)
        detail_rel = detail.group(1) if detail else ""
        detail_abs = detail_rel if detail_rel.startswith("http") else CONFIG["base"] + detail_rel

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
                cats = strip_tags(lis[2])  # 分类可能含 <a> 链接，这里取纯文字
            if len(lis) > 3:
                douban = lis[3]
                dm = HREF_RE.search(douban)
                douban_link = dm.group(1) if dm else ""
                rm = re.search(r'>([^<]*)</a>', douban)
                douban_rate = rm.group(1).strip() if rm else ""

        items.append({
            "poster": poster,
            "link": detail_abs,
            "title": title,
            "meta": meta,
            "cats": cats,
            "douban_link": douban_link,
            "douban_rate": douban_rate,
        })
    return items


def build_rss(items):
    now = datetime.datetime.now(datetime.timezone.utc).strftime("%a, %d %b %Y %H:%M:%S +0000")
    parts = []
    parts.append('<?xml version="1.0" encoding="UTF-8"?>')
    parts.append('<rss version="2.0">')
    parts.append('  <channel>')
    parts.append('    <title>%s</title>' % escape(CONFIG["feed_title"]))
    parts.append('    <link>%s</link>' % escape(CONFIG["url"]))
    parts.append('    <description>%s</description>' % escape(CONFIG["feed_desc"]))
    parts.append('    <language>zh-CN</language>')
    parts.append('    <lastBuildDate>%s</lastBuildDate>' % now)
    parts.append('    <ttl>%d</ttl>' % CONFIG["ttl"])

    for it in items:
        # 内容卡片（HTML），用 CDATA 包裹避免转义冲突
        rate = it["douban_rate"] if (it["douban_rate"] and it["douban_rate"] != "0") else "暂无"
        desc_html = (
            '<div style="font-family:sans-serif;line-height:1.6;">'
            '<a href="{link}" target="_blank">'
            '<img src="{poster}" alt="{title}" '
            'style="max-width:120px;float:left;margin:0 12px 8px 0;border-radius:6px;"></a>'
            '<p style="margin:0 0 6px;"><b>'
            '<a href="{link}" target="_blank">{title}</a></b></p>'
            '<p style="margin:0 0 6px;color:#555;">{meta}</p>'
            '<p style="margin:0 0 6px;color:#555;">{cats}</p>'
            '<p style="margin:0;color:#888;">豆瓣评分: '
            '<a href="{douban}" target="_blank">{rate}</a></p>'
            '<div style="clear:both;"></div></div>'
        ).format(
            link=escape(it["link"]),
            poster=escape(it["poster"]),
            title=escape(it["title"]),
            meta=escape(it["meta"]),
            cats=escape(it["cats"]),
            douban=escape(it["douban_link"]),
            rate=escape(rate),
        )
        parts.append('    <item>')
        parts.append('      <title>%s</title>' % escape(it["title"]))
        parts.append('      <link>%s</link>' % escape(it["link"]))
        parts.append('      <guid>%s</guid>' % escape(it["link"]))
        parts.append('      <description><![CDATA[%s]]></description>' % desc_html)
        parts.append('    </item>')

    parts.append('  </channel>')
    parts.append('</rss>')
    return "\n".join(parts)


def main():
    print("[1/4] 抓取 %s ..." % CONFIG["url"])
    html = fetch(CONFIG["url"], CONFIG["ua"], CONFIG["timeout"])
    print("      源码大小 %d 字节" % len(html))

    print("[2/4] 解析影片条目 ...")
    items = parse_items(html)
    print("      提取到 %d 条（预期 20）" % len(items))
    if not items:
        print("❌ 未提取到任何条目，可能页面结构已变或被 Cloudflare 拦截。", file=sys.stderr)
        sys.exit(1)

    print("[3/4] 生成 RSS 2.0 ...")
    rss = build_rss(items)

    out_path = CONFIG["output"]
    os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(rss)
    print("      已写入 %s" % os.path.abspath(out_path))

    print("[4/4] 样例校验（前 3 条）:")
    for it in items[:3]:
        print("      · %s | %s | 豆瓣:%s" % (it["title"], it["meta"], it["douban_rate"] or "暂无"))
    print("✅ 完成。把 %s 拖进 RSS 阅读器即可订阅；重跑本脚本可刷新。" % os.path.basename(CONFIG["output"]))


if __name__ == "__main__":
    main()
