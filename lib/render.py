"""BTC 看板渲染: 动态数字注入 + spark/指针 JS 填充器。"""
import json


def usd(x):
    return f"${x:,.0f}"


def pct1(x, sign=True):
    v = round(x + 0.0, 1)
    if v == 0:
        v = 0.0
    return f"{'+' if (sign and v >= 0) else ''}{v}%"


def zone_of(total):
    if total < 60:
        return "观望区", "暂不便宜，继续观察", "#a5a093"
    if total < 70:
        return "偏低估", "开始小额分批", "#10b981"
    if total < 80:
        return "低估", "加倍投入", "#eab308"
    return "极度低估", "重手分批", "#ef4444"


def s1_zone(p, avg, lth):
    if p >= avg:
        return "相对高估", "#a5a093"
    if p >= lth:
        return "成本区间内", "#eab308"
    return "跌破长期成本", "#3b82f6"


def s2_zone(m):
    if m < 1.0:
        return "低估", "#10b981"
    if m < 1.5:
        return "偏低估", "#10b981"
    if m < 2.5:
        return "中性", "#eab308"
    return "高估", "#ef4444"


def s3_zone(s):
    if s < 5:
        return "中性偏低估", "#34d399"
    if s < 12:
        return "偏低估", "#34d399"
    return "接近抄底区", "#10b981"


def s5_zone(v):
    if v <= 24:
        return "极度恐慌", "#fbbf24"
    if v <= 44:
        return "恐慌", "#fbbf24"
    if v <= 55:
        return "中性", "#a5a093"
    if v <= 75:
        return "贪婪", "#ef4444"
    return "极度贪婪", "#ef4444"


def _bar(score, color):
    w = score / 20 * 100
    return (f'<div class="card-bar"><div class="card-bar-fill" '
            f'style="width:{w}%;background:{color};"></div></div>')


def _spark(color, sid):
    return (f'<div class="card-spark"><div class="spark-wrap">'
            f'<svg viewBox="0 0 150 36" preserveAspectRatio="none" '
            f'style="display:block;width:100%;height:36px;" data-spark="{sid}" data-color="{color}">'
            f'<defs><linearGradient id="sg-{sid}" x1="0" y1="0" x2="0" y2="1">'
            f'<stop offset="0" stop-color="{color}" stop-opacity="0.20"/>'
            f'<stop offset="1" stop-color="{color}" stop-opacity="0"/>'
            f'</linearGradient></defs>'
            f'<polygon points="" fill="url(#sg-{sid})"/>'
            f'<polyline points="" fill="none" stroke="{color}" stroke-width="1.5" '
            f'stroke-linejoin="round" vector-effect="non-scaling-stroke"/></svg></div></div>')


def _card(sid, num, title, zone, color, sub, score, now_html, raw, dist, extra="", spark=True):
    spark_html = _spark(color, sid) if spark else ""
    return (f'<div class="card" id="sig-{sid}" style="border-color:{color}33;">\n'
            f'  <div class="card-spine" style="background:{color};"></div>\n'
            f'  <div class="card-head">\n'
            f'    <span class="card-title">{num} · {title}</span>\n'
            f'    <span class="card-status" style="color:{color};background:{color}1a;'
            f'border:1px solid {color}40;">{zone}</span>\n'
            f'  </div>\n'
            f'  <div class="card-sub">{sub}</div>\n'
            f'  <div class="card-score" style="color:{color};">{score:.1f}'
            f'<span class="card-score-max">/20</span></div>\n'
            f'  {_bar(score, color)}\n'
            f'  <div class="card-now">{now_html}</div>\n'
            f'{extra}'
            f'  <div class="card-raw">{raw}</div>\n'
            f'  <div class="card-dist">{dist}</div>\n'
            f'  {spark_html}\n'
            f'</div>\n  </div>\n')


def tokens(cd):
    m = cd["meta"]
    p = cd["parts"]
    i = len(cd["dates"]) - 1
    price = m["price_now"]
    t = {}

    t["hero.date"] = f'<div class="topdate">数据日期 {m["last_date"]}</div>'
    cls = "pos" if m["chg24h"] >= 0 else "neg"
    t["hero.price"] = f'<div class="big">{usd(price)}</div>'
    t["hero.chg"] = (f'<div class="chg {cls}">{pct1(m["chg24h"])} '
                     f'<span style="color:var(--muted);font-size:13px;font-weight:400;">24h</span></div>')
    t["hero.ath"] = (f'<span>距 ATH {usd(m["ath"])}: '
                     f'<b class="neg">{pct1(m["ath_dd"], sign=False)}</b></span>')

    zname, dca, zcolor = zone_of(cd["totals"][-1])
    t["verdict.needle"] = ('<line x1="170" y1="165" data-needle="1" '
                           f'stroke="{zcolor}" stroke-width="3" stroke-linecap="round"/>')
    t["verdict.hub"] = f'<circle cx="170" cy="165" r="6" fill="{zcolor}" data-hub="1"/>'
    t["verdict.score"] = (f'<text x="170" y="127" fill="{zcolor}" font-size="46" '
                          f'font-weight="700" font-family="SF Mono,Menlo,monospace" '
                          f'text-anchor="middle">{round(cd["totals"][-1])}</text>')
    t["verdict.zone"] = (f'<div class="gauge-zone" style="background:{zcolor}22;'
                         f'color:{zcolor};">{zname}</div>')
    t["verdict.dca"] = (f'<div class="gauge-dca"><b style="color:{zcolor};'
                        f'font-size:16px;">{dca}</b></div>')
    lights = []
    for sid, col in (("s1", "#a5a093"), ("s2", "#10b981"), ("s3", "#34d399"),
                     ("s4", "#a5a093"), ("s5", "#fbbf24")):
        lights.append(f'<a class="vlight" href="#sig-{sid}">'
                      f'<span class="dot" style="background:{col};"></span>'
                      f'{sid.upper()}<b>{p[sid][i]:.1f}</b></a>')
    t["verdict.lights"] = f'<div class="vlights">{"".join(lights)}</div>'

    # S1
    s1v = p["s1"][i]
    avg, lth, sth = m["avg_cost"], m["lth"], m["sth"]
    s1z, s1c = s1_zone(price, avg, lth)
    rel = lambda x: pct1((price / x - 1) * 100)
    s1_extra = (
        '  <div class="scale">\n'
        '    <div class="scale-flag" style="left:25%;" title="抄底信号阈值"></div>'
        '<div class="scale-bar"><div style="width:25%;background:#3b82f6;height:100%;"></div>'
        '<div style="width:25%;background:#10b981;height:100%;"></div>'
        '<div style="width:25%;background:#eab308;height:100%;"></div>'
        '<div style="width:25%;background:#ef4444;height:100%;"></div>'
        f'<div class="scale-marker" style="left:{(sth-price)/(sth-lth)*100:.1f}%;"></div></div>\n'
        '    <div class="scale-labels"><span>← 跌破长期成本(底)</span><span></span>'
        '<span>站上短期成本(顶) →</span></div>\n'
        '  </div>\n'
        '  <div class="s1-lines">\n'
        f'    <div class="s1-line"><span class="s1-name"><span style="color:#ef4444;">●</span> '
        f'短期持有者成本</span><b>{usd(sth)}</b><span class="{"neg" if price < sth else "muted"}">'
        f'现价{"低于" if price < sth else "高于"} {abs(sth/price-1)*100:.1f}%</span></div>\n'
        f'    <div class="s1-line"><span class="s1-name"><span style="color:#eab308;">●</span> '
        f'平均持有者成本</span><b>{usd(avg)}</b><span class="muted">'
        f'现价高于 {(price/avg-1)*100:.1f}%</span></div>\n'
        f'    <div class="s1-line"><span class="s1-name"><span style="color:#3b82f6;">●</span> '
        f'长期持有者成本</span><b>{usd(lth)}</b><span class="muted">'
        f'现价高于 {(price/lth-1)*100:.1f}%</span></div>\n'
        '  </div>\n')
    t["card.s1"] = _card("s1", "S1", "持有者成本", s1z, s1c,
                         "价格相对三条持有者成本线的位置", s1v,
                         f'当前 BTC <b>{usd(price)}</b> · 落在「{s1z}」',
                         "跌破平均成本 = 多数人浮亏 · 跌破长期成本 = 进入低估区",
                         "跌破平均成本 = 多数人浮亏 · 跌破长期成本 = 进入低估区",
                         extra=s1_extra)

    # S2
    s2v = p["s2"][i]
    mvrv = price / avg
    s2z, s2c = s2_zone(mvrv)
    z2 = m["z_mvrv"]
    t["card.s2"] = _card("s2", "S2", "MVRV 偏差", s2z, s2c, "市值相对链上成本的高低",
                         s2v, f'当前 MVRV <b>{mvrv:.2f}</b> · 落在「{s2z}」',
                         f'偏离历史均值 {z2:+.2f}σ · 越往左越接近底部',
                         "已进入抄底区" if z2 < -0.5 else "未到抄底区")

    # S3
    s3v = p["s3"][i]
    rnl = m["rnl_pct"]
    s3z, s3c = s3_zone(s3v)
    z3 = m["z_rnl"]
    gap = max(0.0, 0.5 - z3)
    t["card.s3"] = _card("s3", "S3", "相对未实现损失", s3z, s3c,
                         "全市场有多少钱正亏着(越多越接近底)",
                         s3v, f'当前浮亏占比 <b>{rnl:.1f}%</b> · 落在「{s3z}」',
                         f'全市场约 {rnl:.1f}% 市值在账面亏损 · 牛市顶≈2% / 熊市底可达 50%+',
                         f'越往左越接近底 · 距抄底信号(+0.5σ)还差 {gap:.2f}σ')

    # S4
    s4v = p["s4"][i]
    flow = m["flow30"]
    flow_html = (f'净流出 <b>-${abs(flow)/1e9:.1f}B</b>' if flow < 0
                 else f'净流入 <b>+{flow/1e9:.1f}B</b>')
    ext, div = m["s4_extent"], m["s4_div"]
    t["card.s4"] = _card("s4", "S4", "资金净变化", "资金流出" if flow < 0 else "资金流入",
                         "#a5a093" if flow < 0 else "#10b981",
                         "近 30 天资金在进场还是离场", s4v,
                         f'近 30 天 <b>{flow_html}</b>',
                         f'程度层 {ext:.1f}(总量较一年峰值回撤,5%起算/15%满) · '
                         f'背离层 {div:.1f}(流出比上波少而价更低)',
                         ("资金回撤中(0 分) · " if ext < 0.5 else "") +
                         "两层取高,当天可判 · 背离退出:价格收复/资金回流/二次流出")

    # S5
    s5v = p["s5"][i]
    fng = m["fng"]
    s5z, s5c = s5_zone(fng)
    t["card.s5"] = _card("s5", "S5", "恐慌贪婪指数", s5z, s5c, "市场情绪冷不冷",
                         s5v, f'当前恐慌指数 <b>{fng}</b> · 落在「{s5z}」',
                         "0 = 极度恐慌(底部) / 100 = 极度贪婪(顶部) · 越往左越该买",
                         "已进入恐慌抄底区" if fng <= 25 else "未到恐慌抄底区")

    # MA
    ma120, ma200 = m["ma120"], m["ma200"]
    def ma_row(name, v):
        d = (price / v - 1) * 100
        return (f'<div class="ma-row"><span>{name}</span><b>{usd(v)}</b>'
                f'<span class="{"neg" if d < 0 else "pos"}">{pct1(d)}</span></div>')
    t["ma.r120"] = ma_row("MA120", ma120)
    t["ma.r200"] = ma_row("MA200", ma200)
    below = price < ma120 and price < ma200
    t["ma.note"] = ('<div class="card-raw" style="margin-top:8px;">'
                    + ("价格跌破两条均线(偏弱)" if below else "价格站上均线(转强)")
                    + "</div>")

    # matrix
    rows = []
    for th in (60, 70, 80):
        cells = []
        for dur in (1, 3, 7):
            seg = cd["TRIG"][str(th)][str(dur)]
            info = cd["matrix"][f"{th}"][f"{dur}"]
            bg = 0.12 - (info["pct"] / 100) * 0.004
            cells.append(f'<td class="num" style="background:rgba(251,191,36,{bg:.3f});">'
                         f'<b>{len(seg)}</b> 段 · <span class="mid">{info["pct"]:.0f}%</span></td>')
        rows.append(f'<tr><td class="num"><b>≥{th}</b></td>{"".join(cells)}</tr>')
    t["matrix.body"] = "<tbody>" + "".join(rows) + "</tbody>"

    t["footer.src"] = ('<p class="src">数据来源：CoinMetrics · alternative.me · DefiLlama · '
                       'Binance(近似复刻自 Glassnode 口径；S1/S3 为近似算法，'
                       f'评分与原版或有偏差；MVRV 基础数据截至 {m["cm_stale_since"]}，'
                       '之后为价格推算)</p>')
    return t


FILLER_JS = """
(function fill() {
  var last = dates.length - 1;
  function sparkPts(vals, w, h, pad) {
    var vs = vals.slice(-90), mn = Math.min.apply(null, vs), mx = Math.max.apply(null, vs);
    var rng = (mx - mn) || 1, out = [];
    for (var i = 0; i < vs.length; i++)
      out.push((i * w / (vs.length - 1)).toFixed(1) + ',' +
               (h - pad - (vs[i] - mn) / rng * (h - 2 * pad)).toFixed(1));
    return out;
  }
  document.querySelectorAll('svg[data-spark]').forEach(function(svg) {
    var key = svg.dataset.spark;
    var vals = (key === 's5') ? SPARKS.fng.map(function(v){return 20 - v * 20 / 45;})
               : SPARKS[key];
    if (!vals) return;
    var pts = sparkPts(vals, 150, 36, 2);
    var poly = svg.querySelector('polygon'), line = svg.querySelector('polyline');
    var all = pts.slice();
    poly.setAttribute('points', '0,36 ' + all.join(' ') + ' 150,36');
    line.setAttribute('points', all.join(' '));
  });
  var needle = document.querySelector('[data-needle]');
  if (needle && totals[last] != null) {
    var ang = Math.PI - (Math.min(totals[last], 100) / 100) * Math.PI;
    needle.setAttribute('x2', (170 + 78 * Math.cos(ang)).toFixed(2));
    needle.setAttribute('y2', (165 - 78 * Math.sin(ang)).toFixed(2));
  }
})();
"""


def render(cd, template):
    html = template
    for k, v in tokens(cd).items():
        html = html.replace("{{" + k + "}}", v)
    html = (html.replace("__DATES__", json.dumps(cd["dates"]))
                .replace("__PRICES__", json.dumps(cd["prices"]))
                .replace("__TOTALS__", json.dumps(cd["totals"]))
                .replace("__CYCLEBOTS__", json.dumps(cd["cycleBots"]))
                .replace("__TRIG__", json.dumps(cd["TRIG"], separators=(",", ":"))))
    html = html.replace("</body>", f"<script>const SPARKS = {json.dumps(cd['sparks'], separators=(',', ':'))};\n{FILLER_JS}</script></body>")
    assert "{{" not in html and "__DATES__" not in html
    return html
