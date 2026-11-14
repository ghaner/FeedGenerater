# -*- coding: utf-8 -*-
"""
kkys14 离线正则验证脚本（仅用于推导提取方式，不参与正式生成）
=================================================================
目的：用 sources.json 中 kkys14 的现有正则，离线解析已抓到的真实 HTML，
      区分「抓取失败」与「正则失配」两种 0 条原因。

用法：python test/verify_kkys14_regex.py
输入：test/kkys14_capture.html（首页）、test/kkys14_label.html（label/new.html）
"""
import os
import sys
import json
import re

# ===================== 参数配置区 =====================
SAMPLES = [
    ("首页", "kkys14_capture.html"),
    ("label/new", "kkys14_label.html"),
]

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "src"))
from generate_feed import parse_generic  # noqa: E402


# ===================== 代码块：读取配置并逐样本解析 =====================
def load_cfg():
    with open(os.path.join(HERE, "..", "src", "sources.json"), encoding="utf-8") as f:
        cfg_all = json.load(f)
    for s in cfg_all["sources"]:
        if s["name"] == "kkys14":
            return s
    raise SystemExit("sources.json 中找不到 kkys14 配置")


def main():
    cfg = load_cfg()
    print("当前 item_block: %s" % cfg["item_block"])
    print()

    for label, fname in SAMPLES:
        path = os.path.join(HERE, fname)
        if not os.path.exists(path):
            print("[%s] 样本不存在，跳过：%s" % (label, fname))
            continue
        html = open(path, encoding="utf-8", errors="replace").read()
        blocks = re.findall(cfg["item_block"], html, re.S)
        items = parse_generic(html, cfg)

        print("=== %s (%s) 长度 %d ===" % (label, fname, len(html)))
        print("  item_block 命中块数: %d" % len(blocks))
        print("  parse_generic 条目数: %d" % len(items))
        for it in items[:3]:
            print("    - title=%r" % it.get("title", "")[:40])
            print("      link=%r poster=%r" % (it.get("link", "")[:50], it.get("poster", "")[:60]))
        miss = [k for k, v in (items[0] if items else {}).items() if not v]
        if items:
            print("  首条空字段: %s" % (miss or "无"))
        print()


if __name__ == "__main__":
    main()
