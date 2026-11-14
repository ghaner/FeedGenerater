# -*- coding: utf-8 -*-
"""
kkys14 服务端原始 HTML + Cookie 复用探测（仅诊断用，不参与正式生成）
=====================================================================
背景：页面加载 2.9s 时是真实内容（24 条 v-item），3.9s 被 JS 自动跳转到百度，
      因此 page.content() 极不稳定。但服务端返回的主文档响应体本身是干净的 HTML。
本脚本验证两条更稳的通道：
  通道 A：拦截主文档 200 响应体（不依赖 DOM，不受后续跳转影响）
  通道 B：拿到 cdndefend_js_cookie 后用 urllib 直连（若可复用则彻底脱离浏览器）

用法：python test/probe_kkys14_cookie.py
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

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "src"))
from generate_feed import parse_generic, CHALLENGE_MARKERS  # noqa: E402


# ===================== 代码块：通道 A —— 拦截主文档响应体 =====================
def grab_document_body():
    """用 Playwright 过挑战，直接从 response 里取主文档原始 HTML。"""
    from playwright.sync_api import sync_playwright

    grabbed = {"html": "", "cookies": []}

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
                if resp.request.resource_type != "document":
                    return
                if resp.status != 200 or grabbed["html"]:
                    return
                body = resp.body() or b""
                text = body.decode("utf-8", "replace")
                if "v-item" in text:
                    grabbed["html"] = text
            except Exception:
                pass

        page.on("response", on_response)
        page.goto(TARGET_URL, wait_until="domcontentloaded", timeout=40000)
        time.sleep(5)
        grabbed["cookies"] = ctx.cookies()
        browser.close()

    return grabbed["html"], grabbed["cookies"]


# ===================== 代码块：通道 B —— Cookie 直连 =====================
def try_cookie_direct(cookies):
    cookie_hdr = "; ".join("%s=%s" % (c["name"], c["value"]) for c in cookies)
    req = urllib.request.Request(TARGET_URL, headers={
        "User-Agent": UA,
        "Accept-Language": "zh-CN,zh;q=0.9",
        "Cookie": cookie_hdr,
    })
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            raw = resp.read()
            return resp.status, raw.decode("utf-8", "replace")
    except Exception as e:
        return None, "异常：%r" % e


# ===================== 代码块：主流程 =====================
def main():
    with open(os.path.join(HERE, "..", "src", "sources.json"), encoding="utf-8") as f:
        cfg_all = json.load(f)
    cfg = next(s for s in cfg_all["sources"] if s["name"] == "kkys14")

    t0 = time.time()
    html_a, cookies = grab_document_body()
    cost_a = time.time() - t0

    print("=== 通道 A：拦截主文档响应体 ===")
    print("  耗时: %.1f 秒" % cost_a)
    print("  拿到 HTML: %d 字节" % len(html_a))
    if html_a:
        items = parse_generic(html_a, cfg)
        print("  解析条目: %d" % len(items))
        for it in items[:3]:
            print("    - %s | %s" % (it.get("title", "")[:22], it.get("link", "")))
        with open(os.path.join(HERE, "kkys14_docbody.html"), "w", encoding="utf-8") as f:
            f.write(html_a)

    print("\n  Cookie 清单:")
    for c in cookies:
        print("    %-24s 域=%-20s 值长=%d" % (c["name"], c["domain"], len(c["value"])))

    print("\n=== 通道 B：Cookie 直连（urllib）===")
    if not cookies:
        print("  无 cookie，跳过")
        return
    status, body = try_cookie_direct(cookies)
    print("  状态码: %s" % status)
    print("  长度: %d" % len(body))
    hit = [m for m in CHALLENGE_MARKERS if m in body.lower()]
    print("  挑战特征命中: %s" % (hit or "无"))
    if status == 200 and not hit:
        items = parse_generic(body, cfg)
        print("  解析条目: %d" % len(items))
        for it in items[:3]:
            print("    - %s | %s" % (it.get("title", "")[:22], it.get("link", "")))
    else:
        print("  片段: %s" % body[:160].replace("\n", " "))


if __name__ == "__main__":
    main()
