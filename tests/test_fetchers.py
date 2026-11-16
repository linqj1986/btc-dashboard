"""fetchers è§£æé€»è¾‘: çœŸå®å“åº”çš„å°æ ·æœ¬ fixture, ä¸å‘ç½‘ç»œã€‚"""
import json
from pathlib import Path

import pytest

from lib import fetchers

FIX = Path(__file__).parent / "fixtures" / "samples"


def test_parse_coinmetrics():
    rows = fetchers._parse_cm((FIX / "cm.csv").read_text())
    assert "2018-02-01" in rows["dates"][:5]  # æ ·æœ¬å«1æœˆæœ«è¡Œ
    assert rows["dates"][-1].startswith("2026-11")  # CoinMetrics æœ€åè¡Œ(æ”¶ç›˜å£å¾„)
    for k in ("price", "mvrv", "mcap", "supply"):
        assert k in rows and rows[k][0] > 0
    # å¿…éœ€åˆ—ç¼ºå¤±æ—¶æŠ¥æ¸…æ™°é”™è¯¯
    with pytest.raises(KeyError, match="CapMVRVCur"):
        fetchers._parse_cm("time,PriceUSD\n2020-01-01,1\n")


def test_parse_fng():
    raw = json.loads((FIX / "fng.json").read_text())
    out = fetchers._parse_fng(raw)
    assert all(isinstance(k, str) and len(k) == 10 for k in out)
    assert all(0 <= v <= 100 for v in out.values())
    assert max(out) >= "2026-11"  # æ ·æœ¬å«å°¾è®°å½•


def test_parse_price24h():
    raw = json.loads((FIX / "binance.json").read_text())
    out = fetchers._parse_price24h(raw)
    assert out["price"] == pytest.approx(65366.78)
    assert out["chg24h_pct"] == pytest.approx(1.93)


def test_parse_snapshot():
    raw = json.loads((FIX / "snapshot.json").read_text())
    out = fetchers._parse_snapshot(raw)
    # åªä¿ç•™æœ‰ sth çœŸå€¼çš„æ—¥æœŸ
    assert all(out), "è‡³å°‘ä¸€å¤©æœ‰ sth"
    ks = sorted(out)
    sth = out[ks[0]]["sth"]
    assert 1000 < sth < 200000


@pytest.mark.network
def test_live_sources():
    cm = fetchers.coinmetrics()
    assert cm["dates"][0] <= "2018-02-01"
    assert cm["dates"][-1] >= "2026-11-14"
    assert len(cm["dates"]) > 3200
    fg = fetchers.fear_greed()
    assert min(fg) <= "2018-02-15" and len(fg) >= 3200
    st = fetchers.stablecoins()
    assert len(st) > 2000
    px = fetchers.btc_price_now()
    assert 1000 < px["price"] < 10_000_000
††
]ñ»@»®Ïæ÷@®J‚@ÀåÁ†ññññ÷æÙñ6ñ©@A‚Aæ
@ÀÀab3ñíñùJ‚@©@A‚ùå÷æ
®»,»Àåå†ññññA=»ñ6ñ]»ƒ÷@®Ïæ÷@®J‚@À÷æÙå†ññññæ@@÷»ñA=»^ù
æ»@ùÿñ66ñ^ùc¢×;E¢cE¢×ù¡ñùc¢×;E¢cE¢cù¡ñùc¢c[E¢øE××ùÿ†ññññæ@@÷»ñA=»^ùƒA@ùÿñ66ñ^¢×ó¡ñ;ø×¡ñ[5[[;ÿ†††
]ñ»@»®á‚æ‚ƒ®J‚@®Ïæ.‚æ»A‚ÀåÁ†ññññùùùÔ³§1İ{X¶ÔI	ÁñÚA‚J™Ïæ»ƒñ‚».»®©@A‚ñB­Ô_ûH˜|1İ{¡ñ	›9:ğBò1İ{˜˜’²7:eùùù†ññññ]÷AÚñ
æ»»ÚñÚÏA÷»ñ
æ»»Ú¡ñ»ÚVA‚†ññññƒæ@ñ6ñ^ÿ††ññññ
]ñ]æJÀ=÷¡ñööJÙåÁ†ññññññññƒæ@æÏÏ‚
À=÷å†ññññññññ»@ñ6ñ‚»À=÷@Ï»Àù@»æ÷» Ú6ùå^×ÿ@Ï»Àùgùå^¢ÿå†ññññññññmñâI1İ{ñcñ’¡ñğ““H0u1İ{B­Ô_ûñ×ñ’ÎoÔIÔv`›à†ññññññññ]ñ‚Àƒæ@åñ66ñ×Á†ññññññññññññ÷»=÷‚ñ^^»@ñöñ×¢¢¢¡ñù×ù¡ñù×ù¡ñù×ù¡ñù×¢ù¡ñù×ù¡ñ»@ñöñ×¢¢¢ñhñ;[5¡ñù¢ù¡ñ¢¡ñù¢ù¡ñù¢ù¡ñù¢ùÿ¡†ññññññññññññññññññññ^»@ñöñ×¢¢¢ñhñ;[ó¢¢¢¢¢¡ñù×ù¡ñù×ù¡ñù×ù¡ñù××ù¡ñù×ù¡ñ»@ñöñ×¢¢¢ñhñ×øcø¡ñù¢ù¡ñ¢¡ñù¢ù¡ñù¢ù¡ñù¢ùÿÿ†ññññññññ÷»=÷‚ñ^^»@ñöñ×¢¢¢¡ñù×ù¡ñù×ù¡ñù×ù¡ñù×cù¡ñù×ù¡ñ»@ñöñ×¢¢¢ñhñ;[5¡ñù¢ù¡ñ¢¡ñù¢ù¡ñù¢ù¡ñù¢ùÿÿ††ññññÚÏA÷»ñá‚»ñæ@ñ‚»ÚA
†ññññA÷.ñ6ñ‚»ÚA
.»®©@A‚†ññññ‚»ÚA
.»®©@A‚ñ6ñ]æJ†ññññ»÷™Á†ññññññññA=»ñ6ñ]»ƒ÷@á‚æ‚ƒ®J‚@À@‚ƒ6ùc¢×;E¢cE¢×ùå†ññññ]‚æ™Á†ññññññññ‚»ÚA
.»®©@A‚ñ6ñA÷.†ññññæ@@÷»ñ‚Àƒæ@åñ66ñcñæ‚
ñù@»æ÷» Ú6××øóó5c¢¢¢¢¢ùñ‚ñƒæ@^¢ÿ†ññññæ@@÷»ñA=»^ùƒA@ùÿñ66ñ^×¢¢¡ñ××¢¡ñ×c¢ÿ†