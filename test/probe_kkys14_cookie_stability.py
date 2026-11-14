# -*- coding: utf-8 -*-
"""
kkys14 Cookie 稳定性与同会话请求探测（仅诊断用，不参与正式生成）
=================================================================
目的：通道 B 已验证「拿 cookie 后 urllib 直连可拿到 24 条」。
      本脚本回答三个决定方案的问题：
      1. cdndefend_js_cookie 是否每次访问都相同（静态 vs 一次性）
      2. cookie 的属性（过期时间 / HttpOnly）
      3. 同一浏览器会话内用 ctx.request.get() 能否直接取到干净 HTML（绕开跳转劫持）

用法：python test/probe_kkys14_cookie_stability.py
"""
import os
import sys
import json
import time

# ===================== 参数配置区 =====================
TARGET_URL = "https://www.kkys14.com/label/new.html"
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
ROUNDS = 3

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "src"))
from generate_feed import parse_generic, CHALLENGE_MARKERS  # noqa: E402


# ===================== 代码块：单轮取 cookie + 同会话请求 =====================
def one_round(idx):
    from playwright.sync_api import sync_playwright

    result = {"cookies": [], "cookie_attrs": [], "api_html": "", "api_status": None}
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

        page.goto(TARGET_URL, wait_until="domcontentloaded", timeout=40000)
        time.sleep(4)          # 等挑战完成 + cookie 落盘

        result["cookies"] = ctx.cookies()
        for c in ctx.cookies():
            result["cookie_attrs"].append(
                "name=%s domain=%s expires=%s httpOnly=%s secure=%s sameSite=%s" % (
                    c["name"], c["domain"], c.get("expires"), c.get("httpOnly"),
                    c.get("secure"), c.get("sameSite")))

        # 同上下文 APIRequestContext：共享 cookie，但不受 DOM 跳转影响
        try:
            resp = ctx.request.get(TARGET_URL, timeout=30000)
            result["api_status"] = resp.status
            result["api_html"] = resp.text()
        except Exception as e:
            result["api_status"] = "异常 %r" % e

        browser.close()
    return result


# ===================== 代码块：主流程 =====================
def main():
    with open(os.path.join(HERE, "..", "src", "sources.json"), encoding="utf-8") as f:
        cfg_all = json.load(f)
    cfg = next(s for s in cfg_all["sources"] if s["name"] == "kkys14")

    values = []
    for i in range(ROUNDS):
        r = one_round(i)
        ck = next((c for c in r["cookies"] if c["name"] == "cdndefend_js_cookie"), None)
        val = ck["value"] if ck else ""
        values.append(val)

        api_items = parse_generic(r["api_html"], cfg) if r["api_html"] else []
        hit = [m for m in CHALLENGE_MARKERS if m in r["api_html"].lower()]

        print("=== 第 %d 轮 ===" % (i + 1))
        print("  cookie 值: %s..." % val[:32])
        if i == 0:
            for a in r["cookie_attrs"]:
                print("  属性: %s" % a)
        print("  ctx.request 状态: %s 长度: %d 挑战: %s" % (
            r["api_status"], len(r["api_html"]), hit or "无"))
        print("  解析条目: %d" % len(api_items))
        print()

    print("=== Cookie 一致性 ===")
    uniq = set(v for v in values if v)
    print("  %d 轮共得到 %d 个不同值 -> %s" % (
        len(values), len(uniq), "静态固定" if len(uniq) == 1 else "每次不同"))


if __name__ == "__main__":
    main()
