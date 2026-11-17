"""TRIG 黄金回归: 用原站 totals 提取的段应与原站 TRIG 逐段一致。"""
from lib import trig


def test_segments_reproduce_ref(ref):
    for th in ("60", "70", "80", "90"):
        for dur in ("1", "3", "7"):
            mine = trig.segments(ref["dates"], ref["prices"], ref["totals"],
                                 int(th), int(dur))
            theirs = ref["TRIG"][th][dur]
            assert len(mine) == len(theirs), (th, dur, len(mine), len(theirs))
            for m, t in zip(mine, theirs):
                for k in ("startDate", "endDate", "days"):
                    assert m[k] == t[k], (th, dur, k, m[k], t[k])
                for k in ("minPrice", "maxPrice", "avgPrice", "priceStart", "priceEnd"):
                    assert abs(m[k] - t[k]) < 0.01, (th, dur, t["startDate"], k)
                for k in ("after30", "after90", "after180"):
                    if t[k] is None:
                        assert m[k] is None, (th, dur, t["startDate"], k)
                    else:
                        assert abs(m[k]["min"] - t[k]["min"]) < 0.01
                        assert abs(m[k]["max"] - t[k]["max"]) < 0.01


def test_build_trig_structure(ref):
    out = trig.build_trig(ref["dates"], ref["prices"], ref["totals"])
    assert sorted(out.keys()) == ["60", "70", "80", "90"]
    assert len(out["60"]["1"]) == 11  # 页面文案锚
    assert len(out["80"]["7"]) == 5
