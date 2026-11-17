"""BTC 五信号分量(S1/S3 在 approx.py 补充)。锚点值校准自原站 2026-11-15 页面。"""


def ma(series, n):
    out = [None] * len(series)
    s = 0.0
    for i, v in enumerate(series):
        if v is None:
            continue
        s += v
        if i >= n:
            s -= series[i - n]
        if i >= n - 1:
            out[i] = s / n
    return out


def s2_f(mvrv: float) -> float:
    """S2 MVRV → 0-20。锚点: ≤0.9(历史大底)=20 · 1.22=13.0(页面锚) · 线性外推 ≥1.814=0。
    参数由 totals 全史拟合校准(见 tools/fit.py)。"""
    bot, top = 0.9, 0.9 + 20 * (1.22 - 0.9) / 7.0  # top = 1.814
    if mvrv <= bot:
        return 20.0
    if mvrv >= top:
        return 0.0
    return 20.0 * (top - mvrv) / (top - bot)


def s5_f(fng: int) -> float:
    """S5 恐慌贪婪 → 0-20。≤25 极度恐慌=20 满, ≥45 中性以上线性归零。"""
    if fng <= 25:
        return 20.0
    if fng >= 45:
        return 0.0
    return 20.0 * (45 - fng) / 20.0


def s4_extent(drawdown_pct: float) -> float:
    """S4 程度层: 资金总量较峰值回撤, 5% 起算 / 15% 满, 线性 0-20。"""
    if drawdown_pct <= 5.0:
        return 0.0
    if drawdown_pct >= 15.0:
        return 20.0
    return (drawdown_pct - 5.0) / 10.0 * 20.0


def _flow_waves(fund: list, i: int) -> tuple[float, float]:
    """近一波与前一波流出事件的 30 天净变化。波=资金创 90 天新低的事件。"""
    def net30(j):
        past = fund[max(0, j - 30)]
        return fund[j] - past if (fund[j] is not None and past is not None) else 0.0
    events = []
    for j in range(max(90, i - 365), i + 1):
        w = [v for v in fund[max(0, j - 90):j + 1] if v is not None]
        if w and fund[j] is not None and fund[j] <= min(w):
            if not events or j - events[-1] >= 14:  # 去密集重采样
                events.append(j)
    if len(events) < 2:
        return 0.0, net30(i)
    return net30(events[-2]), net30(events[-1])


def s4_series(fund: list, price: list, dd_window: int = 365,
              low_window: int = 90, at_low_window: int = 60) -> list:
    """S4 全史序列 = max(程度层, 背离层)。
    程度层: 总量脱离近 at_low_window 天低点带后, 按 365 天峰值回撤 5%起算/15%满。
    背离层(状态机): 价格创 low_window 天新低 且 本波流出浅于前波 → 进入 20 分态;
      退出: 价格收复该低点 / 资金 30 天净转正 / 二次流出(本波深于前波)。"""
    out = []
    div_on = False
    div_low = None
    for i in range(len(fund)):
        cur = fund[i]
        if cur is None:
            out.append(0.0)
            continue
        look = [v for v in fund[max(0, i - dd_window):i + 1] if v is not None]
        recent = [v for v in fund[max(0, i - at_low_window):i + 1] if v is not None]
        at_low = recent and cur <= min(recent) * 1.001
        extent = 0.0
        if look and not at_low:
            extent = s4_extent((1 - cur / max(look)) * 100)
        # 背离状态机
        if price is not None and i >= low_window and price[i] is not None:
            w = [v for v in price[i - low_window:i + 1] if v is not None]
            price_new_low = w and price[i] <= min(w)
            prev_flow, last_flow = _flow_waves(fund, i)
            net_flow = fund[i] - fund[max(0, i - 30)] if fund[max(0, i - 30)] is not None else 0.0
            if not div_on:
                if price_new_low and prev_flow < 0 and last_flow < 0 and last_flow > prev_flow:
                    div_on = True
                    div_low = price[i]
            else:
                recov = div_low is not None and price[i] > div_low * 1.03
                reflux = net_flow > 0
                second = last_flow <= prev_flow
                if recov or reflux or second:
                    div_on = False
                    div_low = None
        out.append(max(extent, 20.0 if div_on else 0.0))
    return out


def s4_signal(fund: list, i: int, price: list | None = None, **kw) -> float:
    """兼容单日调用: 全史计算取第 i 天。"""
    return s4_series(fund, price, **kw)[i]


def compose(parts: dict) -> float:
    return round(sum(parts.values()), 2)
