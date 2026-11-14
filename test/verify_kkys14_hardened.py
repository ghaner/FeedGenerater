# -*- coding: utf-8 -*-
"""
kkys14 容错抓取验证脚本（仅验证方案可行性，不修改正式生成器）
=================================================================
背景：generate_feed.fetch_browser() 在 cdndefend 挑战页通过后会遇到
      「Page.content: Unable to retrieve content because the page is navigating」
      —— 该异常一路抛出，被 process_source 当作抓取失败跳过，导致 0 条。
本脚本在 test 目录内实现一版容错逻辑（content() 重试 + 等 load 状态），
用来证明「只要容错导航瞬间，就能稳定拿回条目」，不触碰 src。

用法：python test/verify_kkys14_hardened.py
"""
import os
import sys
import json
import time

# ===================== 参数配置区 =====================
TARGET_URL = "https://www.kkys14.com/label/new.html"
TIMEOUT = 40
MAX_WAIT = 40
SETTLE = 6
WAIT_SELECTOR = "a.v-item"

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "src"))
from generate_feed import parse_generic, CHALLENGE_MARKERS  # noqa: E402


# ===================== 代码块：容错版浏览器抓取 =====================
def fetch_browser_hardened(url, ua, timeout, max_wait=40,
                           wait_selector=None, settle=5):
    """与 fetch_browser 等价，但把 content() 的导航期异常吞掉重试。"""
    from playwright.sync_api import sync_playwright

    html = ""
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=["--disable-blink-features=AutomationControlled", "--no-sandbox"],
        )
        ctx = browser.new_context(user_agent=ua, locale="zh-CN",
                                  viewport={"width": 1280, "height": 800})
        page = ctx.new_page()
        page.add_init_script(
            "Object.defineProperty(navigator,'webdriver',{get:()=>undefined})")

        page.goto(url, wait_until="domcontentloaded", timeout=timeout * 1000)

        deadline = time.time() + max_wait
        while time.time() < deadline:
            try:
                html = page.content()
            except Exception:
                time.sleep(1)
                continue
            if not any(m in html.lower() for m in CHALLENGE_MARKERS):
                break
            time.sleep(2)

        try:
            page.wait_for_load_state("load", timeout=timeout * 1000)
        except Exception:
            pass

        if wait_selector:
            try:
                page.wait_for_selector(wait_selector, timeout=timeout * 1000)
            except Exception:
                pass

        if settle:
            time.sleep(settle)

        for _ in range(5):
            try:
                html = page.content()
                break
            except Exception:
                time.sleep(1)

        browser.close()
    return html


# ===================== 代码块：主流程 =====================
def main():
    with open(os.path.join(HERE, "..", "src", "sources.json"), encoding="utf-8") as f:
        cfg_all = json.load(f)
    cfg = next(s for s in cfg_all["sources"] if s["name"] == "kkys14")
    ua = cfg_all["ua"]

    t0 = time.time()
    html = fetch_browser_hardened(TARGET_URL, ua, TIMEOUT,
                                  max_wait=MAX_WAIT,
                                  wait_selector=WAIT_SELECTOR, settle=SETTLE)
    cost = time.time() - t0

    hit = [m for m in CHALLENGE_MARKERS if m in html.lower()]
    items = parse_generic(html, cfg)

    import re
    title = re.search(r"<title>(.*?)</title>", html, re.S)
    print("耗时: %.1f 秒" % cost)
    print("HTML 长度: %d" % len(html))
    print("页面 title: %s" % (title.group(1).strip()[:60] if title else "未找到"))
    print("挑战特征命中: %s" % (hit or "无"))
    print("v-item 出现次数: %d" % html.count("v-item"))
    print("解析条目: %d" % len(items))
    for it in items[:3]:
        print("  - %s | %s" % (it.get("title", "")[:22], it.get("link", "")))

    out = os.path.join(HERE, "kkys14_hardened.html")
    with open(out, "w", encoding="utf-8") as f:
        f.write(html)
    print("HTML -> %s" % out)


if __name__ == "__main__":
    main()
