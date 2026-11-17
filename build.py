"""BTC 底部信号看板构建入口。

用法: python -X utf8 build.py [--force] [--offline] [--serve] [--port N]
"""
import argparse
import bisect
import json
import statistics
from datetime import datetime, timezone
from pathlib import Path

from lib import approx, fetchers, render, trig

ROOT = Path(__file__).resolve().parent
DIST = ROOT / "dist" / "index.html"
TEMPLATE = (ROOT / "template.html").read_text(encoding="utf-8")

# 历史周期底(人工维护, 来源原站)
CYCLE_BOTS = [
    {"date": "2018-12-15", "price": 3237.05708474},
    {"date": "2020-03-12", "price": 4860.35383012},
    {"date": "2022-11-21", "price": 15500.0},
    {"date": "2015-01-14", "price": 170.0},
    {"date": "2020-03-13", "price": 4900.0},
]
CYCLE_BOTS = json.loads((ROOT / "cycle_bots.json").read_text(encoding="utf-8"))


def align(points: dict, grid: list) -> list:
    out, last = [], None
    ks = sorted(points)
    for d in grid:
        if d in points:
            last = points[d]
        else:
            i = bisect.bisect_right(ks, d)
            if i > 0:
                last = points[ks[i - 1]]
        out.append(last)
    return out


def fetch_all(force=False, offline=False):
    """分源拉取, 单源失败打印明确错误后中止(便于 CI 日志定位)。"""
    out = {}
    steps = [
        ("klines", lambda: fetchers.binance_klines(since="2018-02-01", offline=offline)),
        ("coinmetrics", lambda: fetchers.coinmetrics(force=force, offline=offline)),
        ("price24h", lambda: fetchers.btc_price_now() if not offline else None),
        ("fear_greed", lambda: fetchers.fear_greed(force=force, offline=offline)),
        ("stablecoins", lambda: fetchers.stablecoins(force=force, offline=offline)),
    ]
    for name, fn in steps:
        try:
            out[name] = fn()
            print(f"[fetch] {name}: OK", flush=True)
        except Exception as e:
            print(f"[fetch] {name}: FAILED — {type(e).__name__}: {e}", flush=True)
            raise
    return {"kl": out["klines"], "cm": out["coinmetrics"],
            "px24": out["price24h"], "fng": out["fear_greed"],
            "fund": out["stablecoins"]}


def accuracy(cd):
    """12 格准确率: 可判定触发日(段内每天, 距今>180天)价格 ≤ 未来最近周期底×1.3 的比例。
    (口径黄金验证 err=0: 89/89/89 89/88/87 87/87/84)"""
    from datetime import date
    dates, prices = cd["dates"], cd["prices"]
    bots = sorted(cd["cycleBots"], key=lambda b: b["date"])
    bot_dates = [b["date"] for b in bots]
    last = date(*map(int, dates[-1].split("-")))
    out = {}
    for th in (60, 70, 80):
        out[str(th)] = {}
        for dur in (1, 3, 7):
            hit, n = 0, 0
            for seg in cd["TRIG"][str(th)][str(dur)]:
                a = dates.index(seg["startDate"])
                b = dates.index(seg["endDate"])
                j = min(bisect.bisect_left(bot_dates, seg["startDate"]), len(bots) - 1)
                bound = bots[j]["price"] * 1.3
                for k in range(a, b + 1):
                    dk = date(*map(int, dates[k].split("-")))
                    if (last - dk).days <= 180 or prices[k] is None:
                        continue
                    n += 1
                    if prices[k] <= bound:
                        hit += 1
            out[str(th)][str(dur)] = {"pct": round(hit / n * 100) if n else 0, "n": n}
    return out


def build(fetched=None, gen_utc=None, force_fetch=False, offline=False):
    if fetched is None:
        fetched = fetch_all(force=force_fetch, offline=offline)
    dates = fetched["kl"]["dates"]
    prices = [round(p, 2) for p in fetched["kl"]["close"]]
    cm = fetched["cm"]
    avg_pts = {d: mc / m / sp for d, m, mc, sp in
               zip(cm["dates"], cm["mvrv"], cm["mcap"], cm["supply"]) if m and mc and sp}
    avg_cost = align(avg_pts, dates)
    cm_last = sorted(avg_pts)[-1]
    fund = align(fetched["fund"], dates)
    fng_al = align(fetched["fng"], dates)
    totals, parts = approx.hist_score(dates, prices, avg_cost, fund, fng_al)
    TRIG = trig.build_trig(dates, prices, totals)
    px = fetched["px24"] or {"price": prices[-1], "chg24h_pct": 0.0}
    ath = max(prices)
    i = len(dates) - 1
    sth = approx.sth_series(prices)[i]
    lth = approx.lth_series(avg_cost)[i]
    avg_now = avg_cost[i]
    mvrv = prices[i] / avg_now if avg_now else None
    mvrv_series = [p / a if (p is not None and a) else None for p, a in zip(prices, avg_cost)]
    mvrv_hist = [v for v in mvrv_series if v is not None]
    z_mvrv = (mvrv - statistics.mean(mvrv_hist)) / (statistics.stdev(mvrv_hist) or 1) if mvrv else 0
    rnl_series = approx.rnl_series(prices, approx.sth_series(prices))
    rnl_now = rnl_series[i] or 0
    rnl_hist = [v for v in rnl_series[i - 365 * 4:i + 1] if v is not None]
    z_rnl = ((rnl_now - statistics.mean(rnl_hist)) / (statistics.stdev(rnl_hist) or 1)
             if rnl_hist else 0)
    s4_vals = parts["s4"]
    cd = {
        "dates": dates, "prices": prices, "totals": totals,
        "cycleBots": CYCLE_BOTS, "TRIG": TRIG,
        "parts": {k: [round(v, 2) if v is not None else None for v in vs]
                  for k, vs in parts.items()},
        "sparks": {
            "s1": [round(v, 2) for v in parts["s1"][-90:] if v is not None],
            "s2": [round(v, 2) for v in parts["s2"][-90:] if v is not None],
            "s3": [round(v, 2) for v in parts["s3"][-90:] if v is not None],
            "s4": [round(v, 2) for v in parts["s4"][-90:] if v is not None],
            "s5": [round(v, 2) for v in parts["s5"][-90:] if v is not None],
            "fng": [v for v in fng_al[-90:] if v is not None],
        },
        "meta": {
            "last_date": dates[-1], "price_now": px["price"], "chg24h": px["chg24h_pct"],
            "ath": ath, "ath_dd": (prices[i] / ath - 1) * 100,
            "avg_cost": avg_now, "sth": sth, "lth": lth,
            "z_mvrv": z_mvrv, "rnl_pct": rnl_now, "z_rnl": z_rnl,
            "flow30": (fund[i] - fund[max(0, i - 30)]) if fund[i] and fund[max(0, i - 30)] else 0,
            "s4_extent": 0.0, "s4_div": 0.0,
            "fng": fng_al[i] if fng_al[i] is not None else 50,
            "ma120": approx.sg.ma(prices, 120)[i], "ma200": approx.sg.ma(prices, 200)[i],
            "cm_stale_since": cm_last,
        },
    }
    cd["matrix"] = accuracy(cd)
    cd["meta"]["gen_utc"] = gen_utc or datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    DIST.parent.mkdir(parents=True, exist_ok=True)
    DIST.write_text(render.render(cd, TEMPLATE), encoding="utf-8", newline="\n")
    diffs = [abs(a - b) for a, b in zip(totals, _ref_totals()) if a is not None and b is not None]
    if diffs:
        dv = sorted(diffs)
        n = len(dv)
        print(f"OK {DIST} | {dates[-1]} 价 {px['price']:,.0f} 评分 {totals[-1]:.1f} | "
              f"与原站 totals 偏差: 中位 {dv[n//2]:.1f} p90 {dv[n*9//10]:.1f} "
              f"(n={n}) | MVRV数据截至 {cm_last}")
    return DIST


def _ref_totals():
    p = ROOT / "reference_data.json"
    if not p.exists():
        return []
    return json.loads(p.read_text(encoding="utf-8"))["totals"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--offline", action="store_true")
    ap.add_argument("--serve", action="store_true")
    ap.add_argument("--port", type=int, default=8124)
    a = ap.parse_args()
    build(force_fetch=a.force, offline=a.offline)
    if a.serve:
        import functools
        import http.server
        import socketserver
        handler = functools.partial(http.server.SimpleHTTPRequestHandler,
                                    directory=str(ROOT / "dist"))
        with socketserver.TCPServer(("0.0.0.0", a.port), handler) as httpd:
            print(f"http://localhost:{a.port}/index.html")
            httpd.serve_forever()


if __name__ == "__main__":
    main()
