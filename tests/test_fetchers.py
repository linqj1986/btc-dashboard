"""fetchers 解析逻辑: 真实响应的小样本 fixture, 不发网络。"""

import json

from pathlib import Path



import pytest



from lib import fetchers



FIX = Path(__file__).parent / "fixtures" / "samples"





def test_parse_coinmetrics():

    rows = fetchers._parse_cm((FIX / "cm.csv").read_text())

    assert "2018-02-01" in rows["dates"][:5]  # 样本含1月末行

    assert rows["dates"][-1].startswith("2026-05")  # CoinMetrics 免费数据停更于 2026-05

    for k in ("price", "mvrv", "mcap", "supply"):

        assert k in rows and rows[k][0] > 0

    # 必需列缺失时报清晰错误

    with pytest.raises(KeyError, match="CapMVRVCur"):

        fetchers._parse_cm("time,PriceUSD\n2020-01-01,1\n")





def test_parse_fng():

    raw = json.loads((FIX / "fng.json").read_text())

    out = fetchers._parse_fng(raw)

    assert all(isinstance(k, str) and len(k) == 10 for k in out)

    assert all(0 <= v <= 100 for v in out.values())

    assert max(out) >= "2026-11"  # 样本含尾记录





def test_parse_price24h():

    raw = json.loads((FIX / "binance.json").read_text())

    out = fetchers._parse_price24h(raw)

    assert out["price"] == pytest.approx(65366.78)

    assert out["chg24h_pct"] == pytest.approx(1.93)





def test_parse_snapshot():

    raw = json.loads((FIX / "snapshot.json").read_text())

    out = fetchers._parse_snapshot(raw)

    # 只保留有 sth 真值的日期

    assert all(out), "至少一天有 sth"

    ks = sorted(out)

    sth = out[ks[0]]["sth"]

    assert 1000 < sth < 200000





@pytest.mark.network

def test_live_sources():

    cm = fetchers.coinmetrics()

    assert cm["dates"][0] <= "2018-02-01"

    assert cm["dates"][-1] >= "2026-05-23"  # CoinMetrics 停更日

    assert len(cm["dates"]) > 3200

    fg = fetchers.fear_greed()

    assert min(fg) <= "2018-02-15" and len(fg) >= 3200

    st = fetchers.stablecoins()

    assert len(st) > 2000

    px = fetchers.btc_price_now()

    assert 1000 < px["price"] < 10_000_000

def test_parse_klines():
    raw = json.loads((FIX / "klines.json").read_text())
    out = fetchers._parse_klines(raw)
    assert out["dates"] == ["2018-02-01", "2018-02-02", "2026-11-14"]
    assert out["close"] == [9014.5, 8799.1, 65366.8]


def test_binance_klines_pagination():
    """分页拉取: monkeypatch net.get_json, 断言翻页游标与停止条件。"""
    calls = []

    def fake(url, **kw):
        calls.append(url)
        ts = int(url.split("startTime=")[1].split("&")[0])
        if len(calls) == 1:
            return [[ts, "1", "1", "1", "10", "1", ts + 86399999, "0", 0, "0", "0", "0"],
                    [ts + 86400000, "1", "1", "1", "11", "1", ts + 172799999, "0", 0, "0", "0", "0"]]
        return [[ts, "1", "1", "1", "12", "1", ts + 86399999, "0", 0, "0", "0", "0"]]

    import lib.net as netmod
    import pytest
    from pathlib import Path
    orig = netmod.get_json
    netmod.get_json = fake
    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(netmod, "CACHE_DIR", Path(tmp_dir) if (tmp_dir := __import__("tempfile").mkdtemp()) else None)
        out = fetchers.binance_klines(since="2018-02-01", page_size=2)
    netmod.get_json = orig
    assert len(calls) == 2
    assert out["close"] == [10.0, 11.0, 12.0]
