"""Cotações ao vivo (BRAPI + yfinance) — mesma lógica do app.py original,
só com um cache simples em memória (TTL) no lugar do st.cache_data."""
import time
import functools
import requests
import yfinance as yf

BRAPI_TOKEN = "o1ikT8zCSyqQUkNYz224ho"

_cache_store: dict = {}


def clear_cache() -> None:
    _cache_store.clear()


def ttl_cache(seconds: int):
    def deco(fn):
        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            key = (fn.__name__, args, tuple(sorted(kwargs.items())))
            now = time.time()
            hit = _cache_store.get(key)
            if hit and (now - hit[0]) < seconds:
                return hit[1]
            val = fn(*args, **kwargs)
            _cache_store[key] = (now, val)
            return val
        return wrapper
    return deco


@ttl_cache(600)
def fetch_usd_brl() -> float:
    try:
        r = requests.get("https://economia.awesomeapi.com.br/json/last/USD-BRL", timeout=5)
        return float(r.json()["USDBRL"]["bid"])
    except Exception:
        pass
    try:
        t = yf.Ticker("USDBRL=X")
        h = t.history(period="1d")
        if not h.empty:
            return float(h["Close"].iloc[-1])
    except Exception:
        pass
    return 5.75


@ttl_cache(600)
def fetch_precos_br(tickers_br: tuple) -> dict:
    """Preços de ativos BR via BRAPI, com fallback para yfinance (.SA)."""
    prices: dict = {}
    if not tickers_br:
        return prices
    try:
        url = f"https://brapi.dev/api/quote/{','.join(tickers_br)}?token={BRAPI_TOKEN}"
        resp = requests.get(url, timeout=15)
        if resp.ok:
            for item in resp.json().get("results", []):
                if item and item.get("regularMarketPrice"):
                    sym = item["symbol"].replace(".SA", "")
                    prices[sym] = item["regularMarketPrice"]
                    prices[item["symbol"]] = item["regularMarketPrice"]
    except Exception:
        pass
    missing = [t for t in tickers_br if t not in prices and t.replace(".SA", "") not in prices]
    if missing:
        try:
            tks_sa = [t + ".SA" if not t.endswith(".SA") else t for t in missing]
            data_yf = yf.download(" ".join(tks_sa), period="2d", auto_adjust=True, progress=False)
            if not data_yf.empty:
                close = (data_yf["Close"] if "Close" in data_yf.columns
                         else data_yf.xs("Close", axis=1, level=0))
                if hasattr(close, "columns"):
                    for tk, tk_sa in zip(missing, tks_sa):
                        if tk_sa in close.columns:
                            v = close[tk_sa].dropna()
                            if not v.empty:
                                prices[tk] = float(v.iloc[-1])
                else:
                    v = close.dropna()
                    if not v.empty and len(missing) == 1:
                        prices[missing[0]] = float(v.iloc[-1])
        except Exception:
            pass
    return prices


@ttl_cache(600)
def fetch_precos_us(tickers_us: tuple) -> dict:
    prices: dict = {}
    if not tickers_us:
        return prices
    try:
        data = yf.download(" ".join(tickers_us), period="2d", auto_adjust=True, progress=False)
        if not data.empty:
            close = data["Close"] if "Close" in data.columns else data.xs("Close", axis=1, level=0)
            if hasattr(close, "columns"):
                for tk in tickers_us:
                    if tk in close.columns:
                        v = close[tk].dropna()
                        if not v.empty:
                            prices[tk] = float(v.iloc[-1])
            else:
                v = close.dropna()
                if not v.empty and len(tickers_us) == 1:
                    prices[tickers_us[0]] = float(v.iloc[-1])
    except Exception:
        pass
    return prices


def fetch_precos_brapi(tickers_br: tuple, tickers_us: tuple) -> tuple:
    prices = fetch_precos_br(tickers_br)
    prices.update(fetch_precos_us(tickers_us))
    usd_brl = fetch_usd_brl()
    return prices, usd_brl
