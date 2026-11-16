"""黄金基线完整性。"""


def test_ref_schema(ref):
    assert len(ref["dates"]) == 3210
    assert ref["dates"][0] == "2018-02-01" and ref["dates"][-1] == "2026-11-15"
    assert len(ref["prices"]) == 3210 and len(ref["totals"]) == 3210
    nn = [v for v in ref["totals"] if v is not None]
    assert len(nn) == 3176
    first = next(i for i, v in enumerate(ref["totals"]) if v is not None)
    assert first == 30  # 30 天回看窗口
    assert ref["totals"][-1] == 43.64  # 页面显示 44
    assert 0 <= min(nn) and max(nn) <= 100
    assert len(ref["cycleBots"]) == 5
    assert ref["cycleBots"][0] == {"date": "2018-12-15", "price": 3237.05708474}


def test_ref_trig_structure(ref):
    trig = ref["TRIG"]
    assert sorted(trig.keys()) == ["60", "70", "80", "90"]
    for th in trig.values():
        assert sorted(th.keys()) == ["1", "3", "7"]
    # 页面文案锚点: ≥60 当日触发 = 11 段 · 89%
    assert len(trig["60"]["1"]) == 11
    seg = trig["60"]["1"][0]
    for k in ("startDate", "endDate", "days", "minPrice", "maxPrice", "avgPrice",
              "priceStart", "priceEnd", "after30", "after90", "after180"):
        assert k in seg
    # 准确率矩阵文案锚点: ≥70 当日 25 段 / ≥80 连7天 5 段
    assert len(trig["70"]["1"]) == 25
    assert len(trig["80"]["7"]) == 5


def test_orig_html(orig_html):
    assert "plotly" in orig_html.lower()
    assert orig_html.count("<html") == 1
    assert "数据来源：Glassnode" in orig_html
