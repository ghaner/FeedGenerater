# -*- coding: utf-8 -*-
"""
kkys14 在线抓取验证脚本（仅用于推导提取方式，不参与正式生成）
=================================================================
目的：用生成器自身的 fetch_browser()，按 sources.json 里 kkys14 的实际参数
      真实跑一遍抓取 + 解析，确认「浏览器通道能否稳定拿回条目」。
      同时对比两种 wait_selector（现有 div.v-item 与实际的 a.v-item）。

用法：python test/verify_kkys14_live.py
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
SELECTOR_CASES = ["div.v-item", "a.v-item"]

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "src"))
from generate_feed import fetch_browser, parse_generic, CHALLENGE_MARKERS  # noqa: E402


# ===================== 代码块：读取源配置 =====================
def load_cfg():
    with open(os.path.join(HERE, "..", "src", "sources.json"), encoding="utf-8") as f:
        cfg_all = json.load(f)
    for s in cfg_all["sources"]:
        if s["name"] == "kkys14":
            return s, cfg_all["ua"]
    raise SystemExit("sources.json 中找不到 kkys14 配置")


# ===================== 代码块：逐选择器实测 =====================
def main():
    cfg, ua = load_cfg()

    for sel in SELECTOR_CASES:
        print("=== wait_selector = %r ===" % sel)
        t0 = time.time()
        try:
            html = fetch_browser(TARGET_URL, ua, TIMEOUT,
                                 max_wait=MAX_WAIT, wait_selector=sel, settle=SETTLE)
        except Exception as e:
            print("  抓取异常：%r" % e)
            continue
        cost = time.time() - t0

        low = html.lower()
        hit = [m for m in CHALLENGE_MARKERS if m in low]
        items = parse_generic(html, cfg)
        print("  耗时: %.1f 秒" % cost)
        print("  HTML 长度: %d" % len(html))
        print("  挑战特征命中: %s" % (hit or "无"))
        print("  解析条目: %d" % len(items))
        if items:
            print("  首条: %s | %s" % (items[0].get("title", "")[:20], items[0].get("link", "")[:50]))
        print()


if __name__ == "__main__":
    main()
