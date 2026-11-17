"""触发段提取: 段 = totals ≥ th 的连续游程; dur 只过滤 days ≥ dur 的段。"""


def _after(prices, i_end, n):
    w = [p for p in prices[i_end + 1:i_end + 1 + n] if p is not None]
    if not w:
        return None
    return {"min": min(w), "max": max(w)}


def segments(dates, prices, totals, threshold, dur):
    """一个 (th, dur) 组合的触发段列表。"""
    segs = []
    run = None
    for i in range(len(dates)):
        t = totals[i]
        hit = t is not None and t >= threshold
        if hit:
            run = [i, i] if run is None else [run[0], i]
        elif run is not None:
            segs.append(_mk(dates, prices, run))
            run = None
    if run is not None:
        segs.append(_mk(dates, prices, run))
    return [s for s in segs if s["days"] >= dur]


def _mk(dates, prices, run):
    a, b = run
    w = [p for p in prices[a:b + 1] if p is not None]
    return {
        "startDate": dates[a], "endDate": dates[b], "days": b - a + 1,
        "minPrice": min(w), "maxPrice": max(w),
        "avgPrice": sum(w) / len(w),
        "priceStart": prices[a], "priceEnd": prices[b],
        "after30": _after(prices, b, 30),
        "after90": _after(prices, b, 90),
        "after180": _after(prices, b, 180),
    }


def build_trig(dates, prices, totals):
    return {str(th): {str(d): segments(dates, prices, totals, th, d)
                      for d in (1, 3, 7)}
            for th in (60, 70, 80, 90)}
