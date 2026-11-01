# -*- coding: utf-8 -*-
"""
kkys14 调试抓取器（仅用于推导提取方式，不参与正式生成）
=========================================================
kkys14 是 SPA：静态 HTML 只是空壳，影片列表由 JS 异步调用接口渲染。
本脚本用 Playwright 通过 cdndefend 挑战后，监听所有 XHR/API 响应，
把疑似数据接口的 url / content-type / 响应体落盘，供定位真实数据源。
同时保存最终渲染后的整页 HTML。

用法：python test/capture_kkys14.py
依赖：playwright + chromium 已安装
"""
import os
import sys
import json

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))
from generate_feed import fetch_browser, CHALLENGE_MARKERS

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
URL = "https://www.kkys14.com/"

HERE = os.path.dirname(os.path.abspath(__file__))
HTML_OUT = os.path.join(HERE, "kkys14_capture.html")
RESP_OUT = os.path.join(HERE, "kkys14_responses.txt")


def main():
    from playwright.sync_api import sync_playwright
    import time

    collected = []
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
                ct = resp.headers.get("content-type", "")
                body = resp.body() or b""
                # 只记录疑似数据接口的响应（JSON / 含中文 / 较大文本）
                if ("json" in ct) or ("text" in ct and len(body) > 200) or ("javascript" in ct):
                    collected.append({
                        "url": resp.url,
                        "status": resp.status,
                        "ct": ct,
                        "size": len(body),
                        "snippet": body[:1500].decode("utf-8", "replace"),
                    })
            except Exception:
                pass

        page.on("response", on_response)
        page.goto(URL, wait_until="domcontentloaded", timeout=40000)

        # 等待挑战解除 + SPA 渲染
        deadline = time.time() + 60
        while time.time() < deadline:
            html = page.content()
            low = html.lower()
            if not any(m in low for m in CHALLENGE_MARKERS):
                break
            time.sleep(2)
        # 再给 SPA 一点时间发请求
        time.sleep(8)
        html = page.content()
        browser.close()

    with open(HTML_OUT, "w", encoding="utf-8") as f:
        f.write(html)

    lines = []
    lines.append("=== 最终渲染 HTML 长度: %d ===" % len(html))
    lines.append("=== 收集到 %d 个响应 ===\n" % len(collected))
    for i, r in enumerate(collected):
        lines.append("#%d status=%s size=%d ct=%s" % (i, r["status"], r["size"], r["ct"]))
        lines.append("URL: %s" % r["url"])
        lines.append("SNIPPET:\n%s\n" % r["snippet"])
        lines.append("-" * 80)

    with open(RESP_OUT, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    print("最终 HTML 长度: %d" % len(html))
    print("收集响应数: %d" % len(collected))
    print("HTML -> %s" % HTML_OUT)
    print("响应 -> %s" % RESP_OUT)


if __name__ == "__main__":
    main()
