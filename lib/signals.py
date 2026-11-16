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


def s4_signal(fund: list, i: int, price: list | None = None,
              dd_window: int = 365, low_window: int = 90) -> float:
    """S4 = max(程度层, 背离层), 各 0-20。
    程度层: 资金总量不在近 dd_window 新低(回撤已止)时, 按 365 天峰值回撤 5%起算/15%满。
    背离层: 价格创 90 天新低 且 本波资金净流出 < 前一波(抛压衰竭) → 20;
            背离退出(价格收复90天低点/资金回流) → 0。
    页面锚: 2026-11 净流出中且总量新低 → 程度0/背离0 → S4≈0.1≈0。"""
    cur = fund[i]
    if cur is None:
        return 0.0
    look = [v for v in fund[max(0, i - dd_window):i + 1] if v is not None]
    if not look:
        return 0.0
    # 程度层
    recent = [v for v in fund[max(0, i - 30):i + 1] if v is not None]
    at_low = recent and cur <= min(recent) * 1.001
    extent = 0.0 if at_low else s4_extent((1 - cur / max(look)) * 100)
    # 背离层
    divergence = 0.0
    if price is not None and i >= low_window and price[i] is not None:
        w = [v for v in price[i - low_window:i + 1] if v is not None]
        price_new_low = w and price[i] <= min(w)
        if price_new_low:
            prev_flow, last_flow = _flow_waves(fund, i)
            if prev_flow < 0 and last_flow < 0 and last_flow > prev_flow:
                divergence = 20.0
    return max(extent, divergence)


def compose(parts: dict) -> float:
    return round(sum(parts.values()), 2)
