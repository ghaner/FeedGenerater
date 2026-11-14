# -*- coding: utf-8 -*-
"""
kkys14 纯 HTTP 通道验证（仅诊断用，不参与正式生成）
=====================================================
目的：若 cdndefend_js_cookie 为静态值，则纯 urllib（不带浏览器）即可拿到列表内容。
      本脚本先用浏览器取一次 cookie（打印完整值），再用 urllib 硬编码该值直连，
      确认「零浏览器」方案可行。

用法：python test/verify_kkys14_pure_http.py
"""
import os
import sys
import json
import time
import urllib.request

# ===================== 参数配置区 =====================
TARGET_URL = "https://www.kkys14.com/label/new.html"
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
COOKIE_NAME = "cdndefend_js_cookie"

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "src"))
from generate_feed import parse_generic, CHALLENGE_MARKERS  # noqa: E402


# ===================== 代码块：取一次 cookie =====================
def fetch_cookie():
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=["--disable-blink-features=AutomationControlled", "--no-sandbox"],
        )
        ctx = browser.new_context(user_agent=UA, locale="zh-CN")
        page = ctx.new_page()
        page.goto(TARGET_URL, wait_until="domcontentloaded", timeout=40000)
        time.sleep(4)
        val = ""
        for c in ctx.cookies():
            if c["name"] == COOKIE_NAME:
                val = c["value"]
        browser.close()
    return val


# ===================== 代码块：纯 urllib 直连 =====================
def http_get(cookie_val):
    req = urllib.request.Request(TARGET_URL, headers={
        "User-Agent": UA,
        "Accept-Language": "zh-CN,zh;q=0.9",
        "Cookie": "%s=%s" % (COOKIE_NAME, cookie_val),
    })
    with urllib.request.urlopen(req, timeout=30) as resp:
        return resp.status, resp.read().decode("utf-8", "replace")


# ===================== 代码块：主流程 =====================
def main():
    with open(os.path.join(HERE, "..", "src", "sources.json"), encoding="utf-8") as f:
        cfg_all = json.load(f)
    cfg = next(s for s in cfg_all["sources"] if s["name"] == "kkys14")

    print("=== 步骤 1：浏览器取一次 cookie ===")
    val = fetch_cookie()
    print("  %s = %s" % (COOKIE_NAME, val))
    print("  长度: %d" % len(val))

    print("\n=== 步骤 2：纯 urllib 直连（无浏览器）===")
    t0 = time.time()
    status, body = http_get(val)
    cost = time.time() - t0
    hit = [m for m in CHALLENGE_MARKERS if m in body.lower()]
    items = parse_generic(body, cfg) if status == 200 else []

    print("  状态码: %s  耗时: %.2f 秒  长度: %d" % (status, cost, len(body)))
    print("  挑战特征: %s" % (hit or "无"))
    print("  解析条目: %d" % len(items))
    for it in items[:3]:
        print("    - %s | %s" % (it.get("title", "")[:22], it.get("link", "")))

    print("\n=== 步骤 3：连续 2 次复核（确认非偶发）===")
    for i in range(2):
        status, body = http_get(val)
        print("  第 %d 次: %s  条目 %d" % (i + 1, status, len(parse_generic(body, cfg))))


if __name__ == "__main__":
    main()
