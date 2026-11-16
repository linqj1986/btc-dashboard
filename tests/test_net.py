"""net.get 编排逻辑: 重试 / 代理降级 / 缓存 / JSON 校验。"""
import json
import urllib.error

import pytest

from lib import net

PROXY = "http://127.0.0.1:7890"


@pytest.fixture(autouse=True)
def no_env_proxy(monkeypatch, tmp_path):
    monkeypatch.delenv("HTTP_PROXY", raising=False)
    monkeypatch.delenv("HTTPS_PROXY", raising=False)
    monkeypatch.delenv("http_proxy", raising=False)
    monkeypatch.delenv("https_proxy", raising=False)
    monkeypatch.setattr(net, "CACHE_DIR", tmp_path / "cache")


def test_retries_then_succeeds(monkeypatch):
    calls = []

    def fake_raw(url, timeout, proxy=None):
        calls.append(proxy)
        if len(calls) < 3:
            raise urllib.error.URLError("truncated")
        return b"ok"

    monkeypatch.setattr(net, "_raw_get", fake_raw)
    assert net.get("https://x/1", tries=3, proxy_fallback=False) == b"ok"
    assert len(calls) == 3


def test_exhausts_retries_raises(monkeypatch):
    def fake_raw(url, timeout, proxy=None):
        raise urllib.error.URLError("down")

    monkeypatch.setattr(net, "_raw_get", fake_raw)
    with pytest.raises(urllib.error.URLError):
        net.get("https://x/1", tries=2, proxy_fallback=False)


def test_direct_403_falls_back_to_proxy(monkeypatch):
    seen = []

    def fake_raw(url, timeout, proxy=None):
        seen.append(proxy)
        if proxy is None:
            raise urllib.error.HTTPError(url, 403, "Forbidden", {}, None)
        return b"via-proxy"

    monkeypatch.setattr(net, "_raw_get", fake_raw)
    assert net.get("https://x/1", tries=3, proxy_fallback=True) == b"via-proxy"
    assert seen == [None, PROXY]


def test_env_proxy_tried_first(monkeypatch):
    seen = []

    def fake_raw(url, timeout, proxy=None):
        seen.append(proxy)
        if proxy != "http://env:1":
            raise urllib.error.URLError("no")
        return b"env"

    monkeypatch.setenv("HTTP_PROXY", "http://env:1")
    monkeypatch.setattr(net, "_raw_get", fake_raw)
    assert net.get("https://x/1", tries=3) == b"env"
    assert seen[0] == "http://env:1"


def test_cache_second_call_no_network(monkeypatch, tmp_path):
    calls = []

    def fake_raw(url, timeout, proxy=None):
        calls.append(url)
        return b"data-v1"

    monkeypatch.setattr(net, "_raw_get", fake_raw)
    a = net.get("https://x/1", cache_name="one.bin")
    b = net.get("https://x/1", cache_name="one.bin")
    assert a == b == b"data-v1"
    assert len(calls) == 1
    assert (tmp_path / "cache" / "one.bin").read_bytes() == b"data-v1"


def test_cache_max_age_expired_refetches(monkeypatch, tmp_path):
    """缓存过期(mtime 超过 max_age) → 重新拉取。"""
    import os
    import time
    calls = []

    def fake_raw(url, timeout, proxy=None):
        calls.append(url)
        return b"fresh"

    monkeypatch.setattr(net, "_raw_get", fake_raw)
    f = tmp_path / "cache" / "ttl.bin"
    f.parent.mkdir()
    f.write_bytes(b"stale")
    old = time.time() - 13 * 3600
    os.utime(f, (old, old))
    assert net.get("https://x/1", cache_name="ttl.bin", max_age=12 * 3600) == b"fresh"
    assert len(calls) == 1
    # 未过期 → 用缓存
    recent = time.time() - 3600
    os.utime(f, (recent, recent))
    f.write_bytes(b"cached")
    assert net.get("https://x/1", cache_name="ttl.bin", max_age=12 * 3600) == b"cached"
    assert len(calls) == 1


def test_cache_force_refetches(monkeypatch):
    calls = []

    def fake_raw(url, timeout, proxy=None):
        calls.append(url)
        return b"v%d" % len(calls)

    monkeypatch.setattr(net, "_raw_get", fake_raw)
    net.get("https://x/1", cache_name="f.bin")
    assert net.get("https://x/1", cache_name="f.bin", force=True) == b"v2"
    assert len(calls) == 2


def test_get_json_retries_on_truncated(monkeypatch):
    calls = []

    def fake_raw(url, timeout, proxy=None):
        calls.append(1)
        if len(calls) == 1:
            return b'{"a": "trunc'  # 截断的 JSON
        return b'{"a": 1}'

    monkeypatch.setattr(net, "_raw_get", fake_raw)
    assert net.get_json("https://x/1", tries=3, proxy_fallback=False) == {"a": 1}
    assert len(calls) == 2


def test_get_json_http_error_falls_back_to_proxy(monkeypatch):
    """Yahoo 实测暴露的 bug: HTTPError 不能穿透重试/代理降级。"""
    seen = []

    def fake_raw(url, timeout, proxy=None):
        seen.append(proxy)
        if proxy is None:
            raise urllib.error.HTTPError(url, 403, "Forbidden", {}, None)
        return b'{"ok": true}'

    monkeypatch.setattr(net, "_raw_get", fake_raw)
    assert net.get_json("https://x/1", tries=3) == {"ok": True}
    assert seen == [None, PROXY]


def test_invalid_json_not_cached(monkeypatch, tmp_path):
    calls = []

    def fake_raw(url, timeout, proxy=None):
        calls.append(1)
        return b'{"broken": ' if len(calls) == 1 else b'{"ok": 1}'

    monkeypatch.setattr(net, "_raw_get", fake_raw)
    with pytest.raises(Exception):
        net.get_json("https://x/1", cache_name="bad.json", tries=1, proxy_fallback=False)
    assert not (tmp_path / "cache" / "bad.json").exists()  # 坏数据不进缓存
    assert net.get_json("https://x/1", cache_name="bad.json", tries=2, proxy_fallback=False) == {"ok": 1}


def test_raw_get_passes_proxy_to_handler(monkeypatch):
    captured = {}

    class FakeOpener:
        def open(self, req, timeout=None):
            captured["url"] = req.full_url
            captured["timeout"] = timeout
            class R:
                def read(self):
                    return b"resp"
                def close(self):
                    pass
                def __enter__(self):
                    return self
                def __exit__(self, *a):
                    return False
            return R()

    def fake_build(*handlers):
        captured["handlers"] = handlers
        return FakeOpener()

    monkeypatch.setattr(urllib.request, "build_opener", fake_build)
    monkeypatch.setattr(urllib.request, "ProxyHandler", lambda m=None: ("proxy-handler", m))
    out = net._raw_get("https://x/1", timeout=7, proxy=PROXY)
    assert out == b"resp"
    assert captured["url"] == "https://x/1"
    assert captured["timeout"] == 7
    assert ("proxy-handler", {"http": PROXY, "https": PROXY}) in captured["handlers"]
