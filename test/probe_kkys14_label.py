# -*- coding: utf-8 -*-
"""
kkys14 列表页接口探测脚本（仅用于推导提取方式，不参与正式生成）
=================================================================
目的：判断 /label/new.html 的内容是「服务端渲染 HTML」还是「XHR 接口渲染」。
做法：Playwright 过 cdndefend 挑战后，监听全部网络响应，
      把 JSON / XHR / 非静态资源类请求单独列出，并统计页面内影片条目数。

用法：python test/probe_kkys14_label.py
依赖：playwright + chromium 已安装
"""
import os
import sys
import json
import time

# ===================== 参数配置区 =====================
TARGET_URL = "https://www.kkys14.com/label/new.html"
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
CHALLENGE_WAIT = 60          # 等待挑战解除的最长秒数
RENDER_SETTLE = 10           # 挑战解除后再等多久，确保异步请求发完
STATIC_EXT = (".css", ".js", ".png", ".jpg", ".jpeg", ".webp", ".gif",
              ".svg", ".ico", ".woff", ".woff2", ".ttf", ".mp4", ".m3u8")

HERE = os.path.dirname(os.path.abspath(__file__))
HTML_OUT = os.path.join(HERE, "kkys14_label.html")
REC_OUT = os.path.join(HERE, "kkys14_label_responses.json")

sys.path.insert(0, os.path.join(HERE, "..", "src"))
from generate_feed import CHALLENGE_MARKERS  # noqa: E402


# ===================== 代码块：探测并落盘 =====================
def probe():
    from playwright.sync_api import sync_playwright

    records = []
    html = ""

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=["--disable-blink-features=AutomationControlled", "--no-sandbox"],
        )
        ctx = browser.new_context(user_agent=UA, locale="zh-CN",
                                  viewport={"width": 1280, "height": 800})
        page = ctx.new_page()
        page.add_init_script(
            "Object.defineProperty(navigator,'webdriver',{get:()=>undefined})")

        def on_response(resp):
            try:
                url = resp.url
                path = url.split("?")[0].lower()
                if path.endswith(STATIC_EXT):
                    return
                ct = resp.headers.get("content-type", "")
                body = resp.body() or b""
                records.append({
                    "url": url,
                    "status": resp.status,
                    "ct": ct,
                    "size": len(body),
                    "snippet": body[:1200].decode("utf-8", "replace"),
                })
            except Exception:
                pass

        page.on("response", on_response)
        page.goto(TARGET_URL, wait_until="domcontentloaded", timeout=40000)

        t0 = time.time()
        while time.time() - t0 < CHALLENGE_WAIT:
            html = page.content()
            if not any(m in html.lower() for m in CHALLENGE_MARKERS):
                break
            time.sleep(2)
        elapsed = time.time() - t0
        time.sleep(RENDER_SETTLE)
        html = page.content()
        cookies = ctx.cookies()
        browser.close()

    return html, records, elapsed, cookies


# ===================== 代码块：主流程与报告 =====================
def main():
    html, records, elapsed, cookies = probe()

    with open(HTML_OUT, "w", encoding="utf-8") as f:
        f.write(html)
    with open(REC_OUT, "w", encoding="utf-8") as f:
        json.dump(records, f, ensure_ascii=False, indent=2)

    print("挑战解除耗时: %.1f 秒" % elapsed)
    print("最终 HTML 长度: %d" % len(html))
    print("非静态资源响应数: %d" % len(records))
    for cls in ("v-item", "v-item-title", "v-item-top-left", "v-item-bottom"):
        print("  %-16s %d 次" % (cls, html.count(cls)))
    print("Cookie 名称: %s" % ", ".join(c["name"] for c in cookies))
    print()

    print("=== 非静态资源响应清单 ===")
    for r in records:
        print("[%s] %7d %-26s %s" % (r["status"], r["size"], r["ct"][:26], r["url"][:100]))

    js = [r for r in records if "json" in r["ct"].lower() or "javascript" in r["ct"].lower()]
    print("\n=== 疑似数据接口（JSON / JS 响应）%d 条 ===" % len(js))
    for r in js:
        print("URL: %s" % r["url"])
        print("SNIPPET: %s" % r["snippet"][:300].replace("\n", " "))
        print("-" * 70)

    print("\nHTML -> %s" % HTML_OUT)
    print("响应 -> %s" % REC_OUT)


if __name__ == "__main__":
    main()
