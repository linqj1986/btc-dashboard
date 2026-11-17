"""S1/S3 近似分量 + 全史合成。

近似口径(台账 Ruling):
- STH 成本 ≈ 120 日 SMA(当日锚校准: 75525 vs 页面 74667, +1.2%)
- LTH 成本 ≈ 平均成本 × 0.906(当日单点锚, 无历史真值)
- RNL ≈ max(0,(sth-price)/sth) × 1.342(校准当日=16.7%)
- S1 = 带内线性: [sth,∞)=0; [avg,sth)=10×(sth-p)/(sth-avg); [lth,avg)=10+10×(avg-p)/(avg-lth); <lth=20
- S3 = 20×(0.868-z)/1.868, z 为 RNL 的 expanding 标准分
"""
from . import signals as sg

STH_WINDOW = 120
LTH_RATIO = 0.906
RNL_K = 1.342
S3_TOP, S3_BOT = 0.9096, 2.9096  # 4年滚动σ, 当日锚 6.1


def sth_series(price: list) -> list:
    return sg.ma(price, STH_WINDOW)


def lth_series(avg_cost: list) -> list:
    return [a * LTH_RATIO if a is not None else None for a in avg_cost]


def s1_f(price: float, avg_cost: float, sth: float, lth: float) -> float:
    if price >= sth:
        return 0.0
    if price >= avg_cost:
        span = max(sth - avg_cost, 1e-9)
        return 10.0 * (sth - price) / span
    if price >= lth:
        span = max(avg_cost - lth, 1e-9)
        return 10.0 + 10.0 * (avg_cost - price) / span
    return 20.0


def rnl_series(price: list, sth: list) -> list:
    out = []
    for p, s in zip(price, sth):
        if p is None or s is None or s <= 0:
            out.append(None)
        else:
            out.append(max(0.0, (s - p) / s) * RNL_K)
    return out


def s3_series(rnl: list, dates: list | None = None) -> list:
    """4 年滚动标准分(不偷看未来) → 0-20。"""
    import statistics
    out = [None] * len(rnl)
    hist = []
    for i, v in enumerate(rnl):
        if v is not None and dates is not None:
            hist.append((dates[i], v))
        if v is None or len(hist) < 60 or dates is None:
            continue
        y0 = str(int(dates[i][:4]) - 4) + dates[i][4:]
        sample = [x[1] for x in hist if x[0] >= y0]
        if len(sample) < 60:
            continue
        mu = statistics.mean(sample)
        sd = statistics.stdev(sample) or 1e-9
        z = (v - mu) / sd
        out[i] = min(20.0, max(0.0, 20.0 * (z - S3_TOP) / (S3_BOT - S3_TOP)))
    return out


def hist_score(dates, price, avg_cost, fund, fng):
    """合成每日总分与分量。返回 (totals, parts: dict[str, list])。
    MVRV = price / avg_cost(CoinMetrics 平均成本, 停更后前向冻结)。"""
    mvrv = [p / a if (p is not None and a) else None for p, a in zip(price, avg_cost)]
    sth = sth_series(price)
    lth = lth_series(avg_cost)
    rnl = rnl_series(price, sth)
    s3 = s3_series(rnl, dates)
    n = len(dates)
    s4_all = sg.s4_series(fund, price)
    parts = {"s1": [], "s2": [], "s3": [], "s4": [], "s5": []}
    totals = [None] * n
    for i in range(n):
        if i < 30 or price[i] is None:
            for k in parts:
                parts[k].append(None)
            continue
        p1 = s1_f(price[i], avg_cost[i], sth[i], lth[i]) \
            if (avg_cost[i] and sth[i] and lth[i]) else 0.0
        p2 = sg.s2_f(mvrv[i]) if mvrv[i] else 0.0
        p3 = s3[i] if s3[i] is not None else 0.0
        p4 = s4_all[i]
        p5 = sg.s5_f(fng[i]) if fng[i] is not None else 0.0
        for k, v in (("s1", p1), ("s2", p2), ("s3", p3), ("s4", p4), ("s5", p5)):
            parts[k].append(v)
        totals[i] = sg.compose({k: parts[k][i] for k in parts})
    return totals, parts
