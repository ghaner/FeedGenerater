# -*- coding: utf-8 -*-
"""
kkys14 页面时序探针（仅诊断用，不参与正式生成）
=================================================
目的：cdndefend 挑战页通过后，页面疑似会二次跳转（甚至跳到百度）。
      本脚本在 goto 之后每隔 1 秒采样一次「title / 文档长度 / v-item 数 / 主域」，
      用来看清内容稳定的时间窗口，为确定抓取时机提供依据。

用法：python test/probe_kkys14_timeline.py
"""
import os
import re
import sys
import time

# ===================== 参数配置区 =====================
TARGET_URL = "https://www.kkys14.com/label/new.html"
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
SAMPLE_SECONDS = 30
INTERVAL = 1.0

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "src"))
from generate_feed import CHALLENGE_MARKERS  # noqa: E402


# ===================== 代码块：逐秒采样 =====================
def main():
    from playwright.sync_api import sync_playwright

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

        navs = []
        page.on("framenavigated",
                lambda f: navs.append((round(time.time() - t0, 1), f.url[:90])))

        t0 = time.time()
        page.goto(TARGET_URL, wait_until="domcontentloaded", timeout=40000)

        print("%-6s %-6s %-7s %-6s %-6s %s" % ("秒", "长度", "v-item", "挑战", "就绪", "title"))
        print("-" * 100)
        for i in range(int(SAMPLE_SECONDS / INTERVAL)):
            try:
                html = page.content()
            except Exception as e:
                print("%-6.1f %s" % (time.time() - t0, "content() 异常: %s" % type(e).__name__))
                time.sleep(INTERVAL)
                continue
            title = re.search(r"<title>(.*?)</title>", html, re.S)
            title = title.group(1).strip()[:34] if title else "-"
            hit = any(m in html.lower() for m in CHALLENGE_MARKERS)
            try:
                ready = page.evaluate("document.readyState")
            except Exception:
                ready = "?"
            print("%-6.1f %-6d %-7d %-6s %-6s %s" % (
                time.time() - t0, len(html), html.count('class="v-item"'),
                "是" if hit else "否", ready, title))
            time.sleep(INTERVAL)

        print("\n=== 导航事件 ===")
        for t, u in navs:
            print("  %5.1fs  %s" % (t, u))
        browser.close()


if __name__ == "__main__":
    main()
