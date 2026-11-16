"""信号分量: 当日锚点 + 形态断言。锚点值来自原站 2026-11-15 页面文案。"""
import pytest

from lib import signals as sg


def test_s2_mvrv_anchor():
    # 页面: MVRV 1.22 → 13.0/20 「偏低估」
    assert sg.s2_f(1.22) == pytest.approx(13.0, abs=0.05)


def test_s5_fear():
    # 页面: 恐慌 10 → 20.0/20 满分; 越恐慌越高分
    assert sg.s5_f(10) == 20.0
    assert sg.s5_f(100) == 0.0
    assert sg.s5_f(50) >= 0.0
    assert sg.s5_f(20) >= sg.s5_f(40) >= sg.s5_f(60)


def test_s4_extent_layer():
    f = sg.s4_extent
    assert f(0) == 0.0 and f(5) == 0.0      # 5% 起算
    assert f(5.05) == pytest.approx(0.1, abs=0.05)
    assert f(15) == 20.0 and f(20) == 20.0  # 15% 满
    assert f(10) == pytest.approx(10.0, abs=0.1)  # 线性中点


def test_compose_and_window():
    parts = {"s1": 4.4, "s2": 13.0, "s3": 6.1, "s4": 0.1, "s5": 20.0}
    assert sg.compose(parts) == pytest.approx(43.6, abs=0.05)  # 页面显示 44
    assert sg.compose({k: 0 for k in parts}) == 0.0


def test_ma():
    out = sg.ma([1.0, 2.0, 3.0, 4.0], 2)
    assert out == [None, 1.5, 2.5, 3.5]


def test_s4_gating():
    # 持续新低(回撤中) → 程度层 0; 无价格新低 → 背离层 0 → 总 0
    down = [100, 95, 90, 85, 80, 78, 77]
    assert sg.s4_signal(down, len(down) - 1, dd_window=7) == 0.0
    # 回撤止跌(脱离30天低点) → 按深度给分: 峰值100 现85.4 → 14.6% → 19.2
    reb = [100, 95, 90, 85, 85.5, 85.2, 85.4]
    assert sg.s4_signal(reb, len(reb) - 1, dd_window=7) == pytest.approx(19.2)
    # 背离: 价格创90天新低 且 本波流出(-5)小于前波(-15)
    # 用真实黄金数据验证背离层语义:
    # 2022-11 FTX 后(价更低+本波流出比 LUNA 波浅)应有分; 2023(价格回升)应为 0
    import json
    import bisect
    from lib import fetchers
    from pathlib import Path
    ref = json.loads((Path(__file__).parent.parent / "reference_data.json").read_text(encoding="utf-8"))
    rd, price = ref["dates"], ref["prices"]
    st = fetchers.stablecoins(offline=True)
    ks = sorted(st)
    st_al, last = [], None
    for d in rd:
        if d in st: last = st[d]
        else:
            i2 = bisect.bisect_right(ks, d)
            if i2 > 0: last = st[ks[i2 - 1]]
        st_al.append(last)
    i_ftx = rd.index("2022-11-21")
    assert sg.s4_signal(st_al, i_ftx, price, low_window=90) > 0
    i_2023 = rd.index("2023-06-15")
    assert sg.s4_signal(st_al, i_2023, price, low_window=90) == 0
    i_now = rd.index("2026-11-15")
    assert sg.s4_signal(st_al, i_now, price, low_window=90) == pytest.approx(0.0, abs=0.5)
