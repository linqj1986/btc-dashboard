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
    with pytest.raises(KeyError, match="CapMVRVCur"):
        fetchers._parse_cm("time,PriceUSD\n2020-01-01,1\n")


def test_parse_fng():
    raw = json.loads((FIX / "fng.json").read_text())
    out = fetchers._parse_fng(raw)
    assert all(isinstance(k, str) and len(k) == 10 for k in out)
    assert all(0 <= v <= 100 for v in out.values())
    assert max(out) >= "2026-11"


def test_parse_price24h():
    raw = json.loads((FIX / "binance.json").read_text())
    out = fetchers._parse_price24h(raw)
    assert out["price"] == pytest.approx(65366.78)
    assert out["chg24h_pct"] == pytest.approx(1.93)


def test_parse_snapshot():
    raw = json.loads((FIX / "snapshot.json").read_text())
    out = fetchers._parse_snapshot(raw)
    assert all(out)
    ks = sorted(out)
    assert 1000 < out[ks[0]]["sth"] < 200000


def test_parse_klines():
    raw = json.loads((FIX / "klines.json").read_text())
    out = fetchers._parse_klines(raw)
    assert out["dates"] == ["2018-02-01", "2018-02-02", "2026-11-14"]
    assert out["close"] == [9014.5, 8799.1, 65366.8]


def test_binance_klines_pagination():
    calls = []

    def fake(url, **kw):
        calls.append(url)
        ts = int(url.split("startTime=")[1].split("&")[0])
        if len(calls) == 1:
            return [[ts, "1", "1", "1", "10", "1", ts + 86399999, "0", 0, "0", "0", "0"],
                    [ts + 86400000, "1", "1", "1", "11", "1", ts + 172799999, "0", 0, "0", "0", "0"]]
        return [[ts, "1", "1", "1", "12", "1", ts + 86399999, "0", 0, "0", "0", "0"]]

    import lib.net as netmod
    import tempfile
    orig = netmod.get_json
    netmod.get_json = fake
    try:
        with pytest.MonkeyPatch.context() as mp:
            mp.setattr(netmod, "CACHE_DIR", Path(tempfile.mkdtemp()))
            out = fetchers.binance_klines(since="2018-02-01", page_size=2)
    finally:
        netmod.get_json = orig
    assert len(calls) == 2
    assert out["close"] == [10.0, 11.0, 12.0]


def test_parse_cb_candles():
    raw = [[1794700800, 61946.17, 66100, 64118.86, 65315.35, 15513.9],
           [1794614400, 63270, 68380, 68236.54, 64118.79, 16354.5]]
    out = fetchers._parse_cb_candles(raw)
    assert out["dates"] == ["2026-11-14", "2026-11-15"]
    assert out["close"] == [64118.79, 65315.35]


def test_parse_cb_stats():
    out = fetchers._parse_cb_stats({"open": "100", "last": "110"})
    assert out["price"] == 110.0 and out["chg24h_pct"] == pytest.approx(10.0)


def test_klines_fallback_to_coinbase(monkeypatch, tmp_path):
    """Binance 451(美国IP) → Coinbase 降级。"""
    import lib.net as netmod
    monkeypatch.setattr(netmod, "CACHE_DIR", tmp_path)
    monkeypatch.setattr(fetchers, "_binance_klines",
                        lambda *a, **k: (_ for _ in ()).throw(RuntimeError("451")))
    monkeypatch.setattr(fetchers, "coinbase_klines",
                        lambda since: {"dates": ["2026-01-01"], "close": [1.0]})
    assert fetchers.binance_klines()["close"] == [1.0]


@pytest.mark.network
def test_live_sources():
    cm = fetchers.coinmetrics()
    assert cm["dates"][0] <= "2018-02-01"
    assert cm["dates"][-1] >= "2026-05-23"
    fg = fetchers.fear_greed()
    assert min(fg) <= "2018-02-15" and len(fg) >= 3200
    st = fetchers.stablecoins()
    assert len(st) > 2000
    px = fetchers.btc_price_now()
    assert 1000 < px["price"] < 10_000_000
    kl = fetchers.coinbase_klines(since="2026-10-01")
    assert len(kl["close"]) > 30


def test_coinbase_klines_window(monkeypatch, tmp_path):
    """分页窗口必须 <=300 天(API 约束), 翻页到 since 为止, 去重。"""
    import lib.net as netmod
    monkeypatch.setattr(netmod, "CACHE_DIR", tmp_path)
    urls = []

    def fake(url, **kw):
        urls.append(url)
        # 返回窗口内 3 根假数据
        return [[1, 0, 0, 0, len(urls), 0]] * 1

    monkeypatch.setattr(netmod, "get_json", fake)
    out = fetchers.coinbase_klines(since="2018-02-01")
    assert len(urls) >= 10  # 2018 至今 ~3200 天 → ≥11 页
    for u in urls:
        start = u.split("start=")[1].split("&")[0]
        end = u.split("end=")[1]
        from datetime import date
        d = (date.fromisoformat(end) - date.fromisoformat(start)).days
        assert d <= 299, (start, end)
