"""BTC 数据源: CoinMetrics(代理) / alternative.me(代理) / DefiLlama(直连) / Binance(实时价)。"""
import csv
import io
import json
from datetime import datetime, timezone

from . import net

CM_URL = "https://raw.githubusercontent.com/coinmetrics/data/master/csv/btc.csv"
FNG_URL = "https://api.alternative.me/fng/?limit=0"
FRESH = 12 * 3600

_NEED = ("PriceUSD", "CapMVRVCur", "CapMrktCurUSD", "SplyCur")


def _ckw(force=False, offline=False):
    if offline:
        return {"force": False, "max_age": None}
    return {"force": force, "max_age": FRESH}


def _parse_cm(text: str) -> dict:
    """CoinMetrics btc.csv → 2018-01 起的日线(自然日, UTC)。"""
    r = csv.DictReader(io.StringIO(text))
    missing = [c for c in _NEED if c not in (r.fieldnames or [])]
    if missing:
        raise KeyError(f"CoinMetrics 缺列: {missing}")
    dates, price, mvrv, mcap, supply = [], [], [], [], []
    for row in r:
        d = row["time"][:10]
        if d < "2018-01-01":
            continue
        p = row["PriceUSD"]
        if not p:
            continue
        dates.append(d)
        price.append(float(p))
        mvrv.append(float(row["CapMVRVCur"]) if row["CapMVRVCur"] else None)
        mcap.append(float(row["CapMrktCurUSD"]) if row["CapMrktCurUSD"] else None)
        supply.append(float(row["SplyCur"]) if row["SplyCur"] else None)
    return {"dates": dates, "price": price, "mvrv": mvrv, "mcap": mcap, "supply": supply}


def coinmetrics(*, force: bool = False, offline: bool = False) -> dict:
    text = net.get(CM_URL, cache_name="cm_btc.csv", timeout=120,
                   **_ckw(force, offline)).decode("utf-8-sig")
    return _parse_cm(text)


def _parse_fng(raw: dict) -> dict[str, int]:
    out = {}
    for item in raw["data"]:
        d = datetime.fromtimestamp(int(item["timestamp"]), timezone.utc).date().isoformat()
        out[d] = int(item["value"])
    return out


def fear_greed(*, force: bool = False, offline: bool = False) -> dict[str, int]:
    raw = net.get_json(FNG_URL, cache_name="fng.json", timeout=60, **_ckw(force, offline))
    return _parse_fng(raw)


def _parse_total_llama(raw: list) -> dict[str, float]:
    out = {}
    for pt in raw:
        tc = pt.get("totalCirculating") or {}
        v = tc.get("peggedUSD") if isinstance(tc, dict) else None
        if v:
            out[datetime.fromtimestamp(int(pt["date"]), timezone.utc).date().isoformat()] = float(v)
    return out


def stablecoins(*, force: bool = False, offline: bool = False) -> dict[str, float]:
    raw = net.get_json("https://stablecoins.llama.fi/stablecoincharts/all",
                       cache_name="llama_total.json", timeout=120, **_ckw(force, offline))
    return _parse_total_llama(raw)


def _parse_price24h(raw: dict) -> dict:
    return {"price": float(raw["lastPrice"]), "chg24h_pct": float(raw["priceChangePercent"])}


def btc_price_now() -> dict:
    """Binance 24h 行情; 失败降级 CoinGecko。"""
    try:
        raw = net.get_json("https://api.binance.com/api/v3/ticker/24hr?symbol=BTCUSDT",
                           cache_name=None, timeout=20)
        return _parse_price24h(raw)
    except Exception:
        raw = net.get_json("https://api.coingecko.com/api/v3/simple/price"
                           "?ids=bitcoin&vs_currencies=usd&include_24hr_change=true",
                           cache_name=None, timeout=20)
        usd = raw["bitcoin"]
        return {"price": float(usd["usd"]), "chg24h_pct": float(usd["usd_24h_change"])}


def _parse_snapshot(raw: dict) -> dict[str, dict]:
    """btc-data.pages.dev 365 天快照 → {date: {'sth': x, ...}}(仅有 sth 真值的日期)。"""
    out = {}
    for rec in raw.get("data", []):
        sth = rec.get("sth_short_term_holder_realized_price")
        if sth:
            out[rec["date"]] = {"sth": float(sth),
                                "lth_supply": rec.get("lth_long_term_holder_supply"),
                                "nupl": rec.get("nupl")}
    return out


def holder_costs_snapshot(*, force: bool = False, offline: bool = False) -> dict | None:
    """社区快照(365 天, 可能停更)。不可得返回 None。"""
    try:
        raw = net.get_json("https://btc-data.pages.dev/btc_metrics.json",
                           cache_name="snapshot.json", timeout=60, **_ckw(force, offline))
        return _parse_snapshot(raw)
    except Exception:
        return None


def _parse_klines(raw: list) -> dict:
    from datetime import datetime, timezone
    dates, close = [], []
    for k in raw:
        dates.append(datetime.fromtimestamp(int(k[0] / 1000), timezone.utc).date().isoformat())
        close.append(float(k[4]))
    return {"dates": dates, "close": close}


def binance_klines(since: str = "2018-02-01", page_size: int = 1000,
                   offline: bool = False) -> dict:
    """Binance BTCUSDT 日线(UTC 自然日), startTime 游标分页拉全史; 结果整体缓存 12h。"""
    cache = net.CACHE_DIR / "binance_klines.json"
    import time
    if cache.exists() and (offline or time.time() - cache.stat().st_mtime <= 12 * 3600):
        return json.loads(cache.read_text(encoding="utf-8"))
    from datetime import datetime, timezone
    ts = int(datetime(*map(int, since.split("-")),
                      tzinfo=timezone.utc).timestamp() * 1000)
    dates, close = [], []
    while True:
        url = (f"https://api.binance.com/api/v3/klines?symbol=BTCUSDT&interval=1d"
               f"&startTime={ts}&limit={page_size}")
        raw = net.get_json(url, cache_name=None, timeout=30)
        if not raw:
            break
        page = _parse_klines(raw)
        dates += page["dates"]
        close += page["close"]
        if len(raw) < page_size:
            break
        ts = int(raw[-1][0]) + 86400000
    out = {"dates": dates, "close": close}
    net.CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache.write_text(json.dumps(out), encoding="utf-8")
    return out
