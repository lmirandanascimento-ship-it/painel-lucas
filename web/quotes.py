"""Cotações ao vivo (BRAPI + yfinance) — mesma lógica do app.py original,
só com um cache simples em memória (TTL) no lugar do st.cache_data."""
import csv
import io
import time
import functools
import requests
import yfinance as yf

BRAPI_TOKEN = "o1ikT8zCSyqQUkNYz224ho"

TESOURO_CSV_URL = (
    "https://www.tesourotransparente.gov.br/ckan/dataset/"
    "df56aa42-484a-4a59-8184-7676580c81e3/resource/"
    "796d2059-14e9-44e3-80c9-2d9e30b405c1/download/precotaxatesourodireto.csv"
)

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


@ttl_cache(3600)
def fetch_dividendos(tickers: tuple, sufixo: str = "") -> dict:
    """Histórico de dividendos via yfinance (BRAPI não tem esse dado no plano
    atual). tickers sem sufixo; sufixo ex: ".SA" pra ativos BR. Retorna
    {ticker: [(data_iso, valor_por_cota), ...]} do mais recente pro mais
    antigo, só pra tickers com pagamentos registrados."""
    out: dict = {}
    for t in tickers:
        try:
            div = yf.Ticker(t + sufixo).dividends.tail(12)
            if div.empty:
                continue
            pares = [(idx.date().isoformat(), float(v)) for idx, v in div.items()]
            pares.sort(key=lambda x: x[0], reverse=True)
            out[t] = pares
        except Exception:
            continue
    return out


def _br_para_iso(data_br: str) -> str:
    d, m, a = data_br.split("/")
    return f"{a}-{m}-{d}"


def _iso_para_br(data_iso: str) -> str:
    a, m, d = data_iso.split("-")
    return f"{d}/{m}/{a}"


@ttl_cache(20 * 3600)
def fetch_pu_tesouro(vencimentos: tuple, tipo_titulo: str = "Tesouro IPCA+") -> dict:
    """PU do dia (venda) do Tesouro Direto via CSV público do Tesouro
    Transparente (gov.br), sem token, atualizado diariamente. vencimentos em
    ISO (ex: "2040-08-15"). Retorna {vencimento_iso: {"pu": float,
    "data_base": iso}} com a linha de Data Base mais recente disponível pra
    cada vencimento.

    Cache de 20h: o PU só muda uma vez por dia útil, e o download desse CSV
    (~14MB) pode levar de alguns segundos a ~20s dependendo do servidor do
    governo — cache mais longo evita pagar esse custo em toda visita à aba."""
    wanted_br = {_iso_para_br(v) for v in vencimentos}
    out: dict = {}
    if not wanted_br:
        return out
    try:
        resp = requests.get(TESOURO_CSV_URL, timeout=60)
        resp.raise_for_status()
        leitor = csv.reader(io.StringIO(resp.text), delimiter=";")
        next(leitor, None)  # cabeçalho
        for linha in leitor:
            if len(linha) < 8:
                continue
            tipo, venc_br, data_base_br = linha[0], linha[1], linha[2]
            pu_venda_str = linha[6]
            if tipo != tipo_titulo or venc_br not in wanted_br:
                continue
            venc_iso = _br_para_iso(venc_br)
            data_base_iso = _br_para_iso(data_base_br)
            atual = out.get(venc_iso)
            if atual is None or data_base_iso > atual["data_base"]:
                try:
                    pu = float(pu_venda_str.replace(",", "."))
                except ValueError:
                    continue
                out[venc_iso] = {"pu": pu, "data_base": data_base_iso}
    except Exception:
        pass
    return out


@ttl_cache(12 * 3600)
def fetch_ipca_mensal(qtd_meses: int = 60) -> list:
    """Variação mensal do IPCA (BCB SGS série 433, % ao mês) via API pública
    do Banco Central, sem token. Retorna [(data_iso_1o_dia_do_mes,
    variacao_pct), ...] dos últimos qtd_meses meses publicados."""
    url = f"https://api.bcb.gov.br/dados/serie/bcdata.sgs.433/dados/ultimos/{qtd_meses}?formato=json"
    out = []
    try:
        resp = requests.get(url, timeout=15)
        resp.raise_for_status()
        for item in resp.json():
            out.append((_br_para_iso(item["data"]), float(item["valor"])))
    except Exception:
        pass
    return out
