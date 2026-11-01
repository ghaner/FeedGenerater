# 说明：本脚本模拟 rsseverything.com 的通配符匹配逻辑，
# 把「项目(可重复)搜索模式」里的 {%N} / {*} 转成正则，
# 在真实抓取的 seedog.cc 页面源码上验证能否正确提取每个影片条目。
# 这不是 rsseverything 后端，仅用于交付前在真实数据上验证规则正确性。

import re
import html

# ---- 步骤1：rsseverything 的「项目(可重复)搜索模式」（单行，已用 {*} 吸收换行与不定属性）----
PATTERN = (
    '<div class="cover">{*}'
    '<a target="_blank" rel="noopener noreferrer" title="{*}" class="image" href="{*}">'
    '<img src="{%1}" alt="{*}"{*}></a>{*}'
    '<ul>{*}'
    '<li><h2><a target="_blank" rel="noopener noreferrer" href="{%2}" aria-hidden="true" class="header-anchor">#</a> {%3}</h2></li>{*}'
    '<li>{%4}</li>{*}'
    '<li>{%5}</li>{*}'
    '<li>豆瓣评分: <a target="_blank" rel="noopener noreferrer nofollow" href="{%6}">{%7}</a></li>{*}'
    '</ul>{*}'
    '</div>'
)

# ---- 步骤2：把模式转成正则 ----
# {%N} -> 具名捕获组（非贪婪，匹配任意字符含换行）
# {*}  -> 非贪婪通配（匹配任意字符含换行）
def to_regex(pattern: str) -> str:
    out = []
    i = 0
    n = len(pattern)
    while i < n:
        if pattern[i:i+3] == '{%}':
            # 兜底：单列 {%} 顺序编号（本模式统一用 {%N}，此分支不触发）
            out.append('(?P<g_unnamed>.*?)')
            i += 3
            continue
        m = re.match(r'\{%(\d+)\}', pattern[i:])
        if m:
            num = m.group(1)
            out.append(r'(?P<g%s>.*?)' % num)
            i += len(m.group(0))
            continue
        if pattern[i:i+3] == '{*}':
            out.append(r'(?P<star%s>.*?)' % len(out))
            i += 3
            continue
        # 普通字符：转义正则元字符
        ch = pattern[i]
        if ch in r'.^$*+?()[]{}|\\/':
            out.append('\\' + ch)
        else:
            out.append(ch)
        i += 1
    return ''.join(out)

regex = to_regex(PATTERN)
print("【生成的正则】")
print(regex)
print("=" * 70)

# ---- 步骤3：在真实页面源码上匹配 ----
with open(r'C:/Users/ICEBuddha/AppData/Local/Temp/seedog.html', 'r', encoding='utf-8') as f:
    page = f.read()

matches = list(re.finditer(regex, page, re.DOTALL))
print(f"【提取到的 Item 数】{len(matches)}")

# 页面可见 cover 数量（用于交叉核对）
visible_covers = page.count('<div class="cover">')
print(f"【页面源码中 <div class=\"cover\"> 出现次数】{visible_covers}")
print("=" * 70)

# ---- 步骤4：展示前 3 个与最后 1 个条目的字段，人工核对 ----
fields = ['g1','g2','g3','g4','g5','g6','g7']
for idx, m in enumerate(matches[:3] + matches[-1:]):
    print(f"\n===== Item #{idx+1} =====")
    for fld in fields:
        val = m.group(fld)
        val = html.unescape(val).strip()
        # 截断过长
        disp = val if len(val) <= 200 else val[:200] + ' ...[截断]'
        print(f"  {fld}: {disp}")

# ---- 步骤5：打印绝对化后的链接示例，确认模板可用 ----
print("\n" + "=" * 70)
print("【项链接模板预览 https://seedog.cc{%2}】")
for m in matches[:3]:
    print("  ->", "https://seedog.cc" + m.group('g2').strip())
