"""一次性工具: original.html → template.html (锚点区间替换为 {{token}})。"""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
html = (ROOT / "tests" / "fixtures" / "original.html").read_text(encoding="utf-8")

SPANS = [
    ('<div class="topdate">数据日期', '</div>', 'hero.date'),
    ('<div class="big">', '</div>', 'hero.price'),
    ('<div class="chg ', '24h</span></div>', 'hero.chg'),
    ('<span>距 ATH', '</span>', 'hero.ath'),
    ('<line x1="170"', 'stroke="#a5a093" stroke-width="3" stroke-linecap="round"/>', 'verdict.needle'),
    ('<circle cx="170" cy="165" r="6" fill="#a5a093"/>', None, 'verdict.hub'),
    ('<text x="170" y="127"', '</text>', 'verdict.score'),
    ('<div class="gauge-zone"', '</div>', 'verdict.zone'),
    ('<div class="gauge-dca">', '</div>', 'verdict.dca'),
    ('<div class="vlights">', '</div>', 'verdict.lights'),
    ('<div class="card" id="sig-s1"', '</div>\n  </div>\n', 'card.s1'),
    ('<div class="card" id="sig-s2"', '</div>\n  </div>\n', 'card.s2'),
    ('<div class="card" id="sig-s3"', '</div>\n  </div>\n', 'card.s3'),
    ('<div class="card" id="sig-s4"', '</div>\n  </div>\n', 'card.s4'),
    ('<div class="card" id="sig-s5"', '</div>\n  </div>\n', 'card.s5'),
    ('<div class="ma-row"><span>MA120', '</div>', 'ma.r120'),
    ('<div class="ma-row"><span>MA200', '</div>', 'ma.r200'),
    ('<div class="card-raw" style="margin-top:8px;">价格跌破两条均线(偏弱)</div>', None, 'ma.note'),
    ('<tbody><tr><td class="num"><b>≥60</b>', '</tbody>', 'matrix.body'),
    ('<p class="src">数据来源：Glassnode</p>', None, 'footer.src'),
]

expected = {}
for start, end, token in SPANS:
    assert html.count(start) == 1, f"锚点不唯一: {token}"
    i = html.index(start)
    j = html.index(end, i + len(start)) + len(end) if end else i + len(start)
    expected[token] = html[i:j]
    html = html[:i] + "{{" + token + "}}" + html[j:]

# 内嵌数据行 → 注入点
html, n = re.subn(r"const dates = \[.*?\];\n", "const dates = __DATES__;\n", html, flags=re.S)
assert n == 1
for name in ("prices", "totals"):
    html, n = re.subn(rf"const {name} = \[.*?\];\n", f"const {name} = __{name.upper()}__;\n", html, flags=re.S)
    assert n == 1
for name in ("cycleBots", "TRIG"):
    html, n = re.subn(rf"const {name} = (\[|\{{).*?\}};\n" if name == "TRIG" else rf"const {name} = \[.*?\];\n",
                      f"const {name} = __{name.upper()}__;\n", html, flags=re.S)
    assert n == 1, name

(ROOT / "template.html").write_text(html, encoding="utf-8")
(ROOT / "tests" / "fixtures" / "tokens_expected.json").write_text(
    json.dumps(expected, ensure_ascii=False, indent=1), encoding="utf-8")
print(f"template.html: {len(SPANS)} tokens + 5 数据注入点")
