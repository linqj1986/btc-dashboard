"""带 缓存 / 代理降级 / 重试 的 HTTP GET。

代理尝试顺序: 环境变量 HTTP_PROXY/HTTPS_PROXY → 直连 → http://127.0.0.1:7890
(Yahoo/财政部直连 403/超时，DefiLlama 直连可达 —— 顺序保证能直连的源不多绕路。)
validate 回调: 网络成功但校验失败(如截断的 JSON)同样计入重试, 坏数据不写缓存。
"""
import os
import time
import urllib.error
import urllib.request
from pathlib import Path

FALLBACK_PROXY = "http://127.0.0.1:7890"
CACHE_DIR = Path(__file__).resolve().parent.parent / "cache"

_HEADERS = {
    "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                   "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"),
    "Accept": "application/json,text/plain,*/*",
}

_RETRYABLE = (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, OSError,
              ValueError)  # json.JSONDecodeError 是 ValueError 子类


def _proxy_strategies(use_fallback: bool) -> list:
    strategies = []
    env = os.environ.get("HTTPS_PROXY") or os.environ.get("HTTP_PROXY") \
        or os.environ.get("https_proxy") or os.environ.get("http_proxy")
    if env:
        strategies.append(env)
    strategies.append(None)  # 直连
    if use_fallback:
        strategies.append(FALLBACK_PROXY)
    return strategies


def _raw_get(url: str, timeout: float, proxy: str | None = None) -> bytes:
    """单次请求。proxy=None 走直连(空 ProxyHandler 绕过系统代理)。"""
    handlers = [urllib.request.ProxyHandler({"http": proxy, "https": proxy} if proxy else {})]
    opener = urllib.request.build_opener(*handlers)
    req = urllib.request.Request(url, headers=_HEADERS)
    with opener.open(req, timeout=timeout) as resp:
        return resp.read()


def get(url: str, *, cache_name: str | None = None, timeout: float = 60,
        tries: int = 3, proxy_fallback: bool = True, force: bool = False,
        validate=None, max_age: float | None = None) -> bytes:
    """GET url。cache_name 命中且未过期则不发网络; 否则按代理顺序轮转重试 tries 次。
    max_age: 缓存新鲜期(秒), None = 永不过期, 超期视为 miss 重拉。"""
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache_file = CACHE_DIR / cache_name if cache_name else None
    if cache_file and cache_file.exists() and not force:
        fresh = (max_age is None
                 or (time.time() - cache_file.stat().st_mtime) <= max_age)
        if fresh:
            return cache_file.read_bytes()

    strategies = _proxy_strategies(proxy_fallback)
    last_err = None
    for attempt in range(tries):
        # 轮转: 先按顺序试完所有策略(env→直连→7890), 再从头轮转直到 tries 用尽
        proxy = strategies[attempt % len(strategies)]
        try:
            data = _raw_get(url, timeout=timeout, proxy=proxy)
            if validate is not None:
                validate(data)
            if cache_file:
                cache_file.write_bytes(data)
            return data
        except _RETRYABLE as e:
            last_err = e
    raise last_err


def get_json(url: str, *, tries: int = 3, **kw) -> dict:
    """GET 并解析 JSON; 网络错误与截断的 JSON 都计入重试(轮换代理)。"""
    import json

    def validate(b: bytes) -> None:
        json.loads(b)  # 解析失败抛 JSONDecodeError(ValueError 子类) → 计入重试

    return json.loads(get(url, validate=validate, tries=tries, **kw))
