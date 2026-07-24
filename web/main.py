"""
Painel Lucas — versão FastAPI + HTMX (migração em andamento).

Convive com o app Streamlit original: mesmo Supabase, mesma autenticação.
Módulos ainda não portados mostram uma tela "em construção" honesta em vez
de fingir que existem.
"""
import os
import secrets
from datetime import datetime
from zoneinfo import ZoneInfo

from fastapi import FastAPI, Request, Form, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware
from supabase import create_client

import quotes


def agora_br() -> datetime:
    """Hora atual no fuso de Brasília — o servidor (Railway) roda em UTC."""
    return datetime.now(ZoneInfo("America/Sao_Paulo"))

# ─── Config ───────────────────────────────────────────────────────────────────
def _secret(key: str) -> str | None:
    return os.environ.get(key)

SUPABASE_URL = _secret("SUPABASE_URL")
SUPABASE_KEY = _secret("SUPABASE_KEY")                  # anon — só pra validar login
SUPABASE_SERVICE_KEY = _secret("SUPABASE_SERVICE_KEY")  # service_role — todas as consultas
SESSION_SECRET = _secret("SESSION_SECRET") or secrets.token_hex(32)

VERDE = "#1A4731"
OURO  = "#B8860B"
CAPITAL_BASE = 684_160.69

# sb_auth: só usado pra validar e-mail/senha no login (chave anon).
# sb: usado em TODA consulta de dado (chave service_role) — não depende de sessão
# de usuário, então não quebra quando o processo do servidor reinicia (redeploy,
# crash, escala) enquanto o cookie de login do navegador continua válido.
sb_auth = create_client(SUPABASE_URL, SUPABASE_KEY)
sb = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY or SUPABASE_KEY)

app = FastAPI()
app.add_middleware(SessionMiddleware, secret_key=SESSION_SECRET, same_site="lax")
templates = Jinja2Templates(directory="templates")

NAV = [
    {"id": "resumo",  "icon": "📊", "label": "Resumo"},
    {"id": "acoes",   "icon": "📈", "label": "Ações BR"},
    {"id": "etfbr",   "icon": "🇧🇷", "label": "ETF BR"},
    {"id": "fiis",    "icon": "🏢", "label": "FIIs"},
    {"id": "intl",    "icon": "🌍", "label": "Internacional",
     "subs": [{"id": "etfusa", "label": "ETF USA"},
              {"id": "reits",  "label": "REITs"},
              {"id": "stocks", "label": "Stocks"}]},
    {"id": "tesouro", "icon": "🏛️", "label": "Tesouro"},
    {"id": "cricra",  "icon": "📋", "label": "CRI/CRA"},
    {"id": "fundos",  "icon": "💼", "label": "Fundos"},
    {"id": "cdb",     "icon": "🏦", "label": "CDB/LCI/LCA"},
    {"id": "evolucao","icon": "📉", "label": "Evolução"},
    {"id": "emprestimos", "icon": "💳", "label": "Empréstimos",
     "subs": [{"id": "concedidos", "label": "Empréstimos Concedidos"},
              {"id": "meus",       "label": "Meus Empréstimos"}]},
    {"id": "escritorio", "icon": "🏢", "label": "Escritório"},
]
PORTADO = {"resumo"}  # módulos já migrados de verdade

CLASS_COLORS = {
    "Ações BR": "#1A4731", "ETF BR": "#2D6A4F", "FII": "#B8860B",
    "ETF USA":  "#C9A227", "REITs":  "#7BA98C", "Stocks": "#C4B896",
    "CDB": "#A5C4B2", "LCI/LCA": "#8FA98F", "CRI/CRA": "#D9CBA0",
    "Fundos": "#5C8A6D", "Tesouro Direto": "#9B7E3A",
}


def brl(v, sign: bool = False) -> str:
    if v is None:
        return "—"
    try:
        v = float(v)
    except Exception:
        return "—"
    if v != v:  # NaN
        return "—"
    s = f"{abs(v):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    prefix = ("+" if v >= 0 else "-") if sign else ("-" if v < 0 else "")
    return f"R$ {prefix}{s}"


def usd(v, sign: bool = False) -> str:
    if v is None:
        return "—"
    try:
        v = float(v)
    except Exception:
        return "—"
    if v != v:
        return "—"
    prefix = ("+" if v >= 0 else "-") if sign else ("-" if v < 0 else "")
    return f"US$ {prefix}{abs(v):,.2f}"


def pct(v: float) -> str:
    return f"{'+' if v >= 0 else ''}{v:.2f}%".replace(".", ",")


def parse_brl(s: str) -> float:
    try:
        return float(str(s).strip().replace("R$", "").replace(" ", "")
                     .replace(".", "").replace(",", "."))
    except Exception:
        return 0.0


def brl_input(v) -> str:
    """Formata float pra string de input BRL sem prefixo: 1.234,56"""
    try:
        v = float(v or 0)
    except Exception:
        v = 0.0
    return f"{abs(v):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


# ─── Dados (Supabase) ─────────────────────────────────────────────────────────
def load_snapshot(tipo: str) -> dict:
    r = (sb.table("carteira_snapshots")
           .select("data,dados,usd_brl,total_investido,total_atual")
           .eq("tipo", tipo).order("data", desc=True).limit(1).execute())
    return r.data[0] if r.data else {}


def resumo_ctx() -> dict:
    snap_rv = load_snapshot("RV")
    snap_rf = load_snapshot("RF")
    dados_rv = snap_rv.get("dados", {}) if snap_rv else {}
    dados_rf = snap_rf.get("dados", {}) if snap_rf else {}
    rv_tot = float(snap_rv.get("total_atual", 0) or 0)
    rf_tot = float(snap_rf.get("total_atual", 0) or 0)
    total = rv_tot + rf_tot
    ganho = total - CAPITAL_BASE
    rentab = ganho / CAPITAL_BASE * 100 if CAPITAL_BASE else 0

    classes_vals: dict[str, float] = {}
    for cls, data in dados_rv.get("classes", {}).items():
        v = data.get("atual", 0) or 0
        if v > 0:
            classes_vals[cls] = v
    for cls, data in dados_rf.get("classes", {}).items():
        v = data.get("atual", 0) or 0
        if v > 0:
            classes_vals[cls] = round(classes_vals.get(cls, 0) + v, 2)

    ordenado = sorted(classes_vals.items(), key=lambda x: -x[1])
    fatias = []
    acumulado = 0.0
    for nome, valor in ordenado:
        pct_v = valor / total * 100 if total else 0
        fatias.append({
            "nome": nome, "valor": valor, "pct": pct_v,
            "cor": CLASS_COLORS.get(nome, "#999"),
            "de": acumulado, "ate": acumulado + pct_v,
        })
        acumulado += pct_v

    return {
        "kpi_total": brl(total),
        "kpi_capital_base": brl(CAPITAL_BASE),
        "kpi_ganho": brl(ganho, sign=True),
        "kpi_rentab": pct(rentab),
        "kpi_rv": brl(rv_tot),
        "kpi_rf": brl(rf_tot),
        "ganho_positivo": ganho >= 0,
        "data_rv": snap_rv.get("data", "—") if snap_rv else "—",
        "data_rf": snap_rf.get("data", "—") if snap_rf else "—",
        "fatias": fatias,
        "total_fmt": brl(total),
    }


def load_posicoes_rv() -> list[dict]:
    """Posições RV mais recentes (para cotações ao vivo)."""
    r = (sb.table("carteira_rv_posicoes").select("*")
           .order("data_snapshot", desc=True).limit(200).execute())
    data = r.data or []
    if not data:
        return []
    max_date = max(d["data_snapshot"] for d in data)
    return [d for d in data if d["data_snapshot"] == max_date]


def atualizar_cotacoes_ctx() -> dict:
    """Força busca ao vivo (ignora o cache de 10min) e monta um relatório de
    sucesso/falha — não recalcula o Patrimônio Total (esse vem do snapshot
    gravado), só atualiza o cache pras próximas visitas às abas RV/Internacional."""
    quotes.clear_cache()
    posicoes_rv = load_posicoes_rv()
    ok: list[str] = []
    fail: list[str] = []

    usd_val = quotes.fetch_usd_brl()

    tickers_br = [p["ticker"] for p in posicoes_rv if p.get("moeda") == "BRL"]
    tickers_us = [p["ticker"] for p in posicoes_rv if p.get("moeda") == "USD"]

    if tickers_br:
        prices_br, _ = quotes.fetch_precos_brapi(tuple(tickers_br), ())
        for tk in tickers_br:
            tk_c = tk.replace(".SA", "")
            v = prices_br.get(tk_c) or prices_br.get(tk)
            (ok.append(f"{tk_c} → R$ {v:.2f}") if v else fail.append(tk_c))

    if tickers_us:
        prices_us = quotes.fetch_precos_us(tuple(tickers_us))
        for tk in tickers_us:
            v = prices_us.get(tk)
            (ok.append(f"{tk} → US$ {v:.2f}") if v else fail.append(tk))

    n_ok, n_fail = len(ok), len(fail)
    cor = "🟢" if n_fail == 0 else ("🟡" if n_ok > 0 else "🔴")
    return {
        "ok": ok, "fail": fail, "n_ok": n_ok, "n_fail": n_fail, "cor": cor,
        "hora": agora_br().strftime("%H:%M:%S"), "usd_brl": usd_val,
    }


# ─── RV BR (Ações BR / ETF BR / FIIs) ─────────────────────────────────────────
RV_BR_CLASSES = {"acoes": "Ações BR", "etfbr": "ETF BR", "fiis": "FII"}


def rv_br_ctx(classe: str) -> dict:
    snap_rv = load_snapshot("RV")
    posicoes_rv = load_posicoes_rv()
    dados = snap_rv.get("dados", {}) if snap_rv else {}
    posicoes = dados.get("classes", {}).get(classe, {}).get("posicoes", [])
    ctx = {
        "classe": classe, "vazio": not posicoes,
        "data_snapshot": snap_rv.get("data", "—") if snap_rv else "—",
    }
    if not posicoes:
        return ctx

    tickers_br = tuple(p["ticker"] for p in posicoes_rv if p.get("classe") == classe)
    prices = {}
    if tickers_br:
        prices, _ = quotes.fetch_precos_brapi(tickers_br, ())

    linhas = []
    tot_inv = tot_at = 0.0
    for p in posicoes:
        nome = p.get("nome", "")
        inv = float(p.get("investido") or 0)
        at_snap = float(p.get("atual") or 0)
        ticker_live = nome[:-3] if nome.endswith(".SA") else nome
        preco_live = prices.get(ticker_live) or prices.get(nome)
        qtd_val = float(p.get("qtd") or 0)
        at_live = preco_live * qtd_val if preco_live and qtd_val else at_snap
        ren = (at_live / inv - 1) * 100 if inv else 0
        tot_inv += inv
        tot_at += at_live
        pm = p.get("preco_pago_brl") or (inv / qtd_val if qtd_val else None)
        linhas.append({
            "ativo": nome, "setor": p.get("setor", ""),
            "qtd": f"{qtd_val:g}" if qtd_val else "—",
            "pm": brl(pm), "cotacao": brl(preco_live) if preco_live else "⟳",
            "investido": brl(inv), "posicao": brl(at_live),
            "ganho": brl(at_live - inv, sign=True), "pct": pct(ren), "ren": ren,
        })
    ren_tot = (tot_at / tot_inv - 1) * 100 if tot_inv else 0
    ctx.update({
        "linhas": linhas,
        "tot_investido": brl(tot_inv), "tot_posicao": brl(tot_at),
        "tot_ganho": brl(tot_at - tot_inv, sign=True), "tot_pct": pct(ren_tot),
    })
    return ctx


# ─── Internacional (ETF USA / REITs / Stocks) ────────────────────────────────
INTL_CLASSES = {"etfusa": "ETF USA", "reits": "REITs", "stocks": "Stocks"}


def internacional_ctx(sub_id: str) -> dict:
    snap_rv = load_snapshot("RV")
    posicoes_rv = load_posicoes_rv()
    dados = snap_rv.get("dados", {}) if snap_rv else {}
    usd_brl_v = float(snap_rv.get("usd_brl", 5.75) or 5.75) if snap_rv else 5.75
    classe = INTL_CLASSES.get(sub_id, "ETF USA")

    tickers_us = tuple(p["ticker"] for p in posicoes_rv if p.get("moeda") == "USD")
    prices = {}
    if tickers_us:
        prices, usd_brl_v = quotes.fetch_precos_brapi((), tickers_us)

    posicoes = dados.get("classes", {}).get(classe, {}).get("posicoes", [])
    ctx = {"classe": classe, "vazio": not posicoes, "usd_brl": usd_brl_v}
    if not posicoes:
        return ctx

    linhas = []
    tot_inv = tot_at = 0.0
    for p in posicoes:
        nome = p.get("nome", "")
        qtd = float(p.get("qtd") or 0)
        pm_usd = float(p.get("preco_pago_usd") or p.get("preco_atual_usd") or 0)
        p_live = prices.get(nome)
        cotacao_usd = p_live if p_live else float(p.get("preco_atual_usd") or 0)
        inv_usd = round(qtd * pm_usd, 2)
        at_usd = round(qtd * cotacao_usd, 2)
        ren = (at_usd / inv_usd - 1) * 100 if inv_usd else 0
        tot_inv += inv_usd
        tot_at += at_usd
        linhas.append({
            "ativo": nome, "setor": p.get("setor", ""),
            "qtd": f"{qtd:g}" if qtd else "—",
            "pm": usd(pm_usd) if pm_usd else "—",
            "cotacao": usd(cotacao_usd) if p_live else "⟳",
            "investido": usd(inv_usd), "posicao": usd(at_usd),
            "ganho": usd(at_usd - inv_usd, sign=True), "pct": pct(ren),
            "posicao_r_est": brl(at_usd * usd_brl_v),
        })
    ren_tot = (tot_at / tot_inv - 1) * 100 if tot_inv else 0
    ctx.update({
        "linhas": linhas,
        "tot_investido": usd(tot_inv), "tot_posicao": usd(tot_at),
        "tot_ganho": usd(tot_at - tot_inv, sign=True), "tot_pct": pct(ren_tot),
        "tot_posicao_r_est": brl(tot_at * usd_brl_v),
    })
    return ctx


# ─── Renda Fixa (Tesouro / CRI-CRA / Fundos / CDB-LCI-LCA) ───────────────────
RF_CONFIG = {
    "tesouro": {
        "titulo": "🏛️ Tesouro", "classes": ["Tesouro Direto"],
        "colunas": [("Título", "nome"), ("Qtd", "qtd"), ("Vencimento", "vencimento"),
                    ("Taxa", "tipo_taxa"), ("Investido", "investido"),
                    ("Rentab.", "rentab_liquida"), ("Valor Líq.", "valor_liquido")],
        "total_field": "valor_liquido",
        "nota": "IR regressivo já descontado no Valor Líquido.",
    },
    "cricra": {
        "titulo": "📋 CRI/CRA", "classes": ["CRI/CRA"],
        "colunas": [("Título", "nome"), ("Taxa Mercado", "taxa_mercado"),
                    ("Investido", "investido"), ("Valor Atual", "atual"), ("Rentab.", "rentab")],
        "total_field": "atual",
        "nota": "CRI/CRA: isentos de IR para pessoa física.",
    },
    "fundos": {
        "titulo": "💼 Fundos", "classes": ["Fundos"],
        "colunas": [("Fundo", "nome"), ("Investido", "investido"),
                    ("Valor Liq.", "valor_liquido"), ("Rent. Líq.", "rentab_liquida")],
        "total_field": "valor_liquido", "nota": None,
    },
    "cdb": {
        "titulo": "🏦 CDB/LCI/LCA", "classes": ["CDB", "LCI/LCA"],
        "colunas": [("Título", "nome"), ("Investido", "investido"),
                    ("Atual", "atual"), ("Ganho", "ganho"), ("Rentab.", "rentab")],
        "total_field": "atual",
        "nota": "LCI/LCA: isentos de IR. CDB: valor bruto (IR no resgate).",
    },
}
_MONEY_KEYS = {"atual", "investido", "ganho", "valor_liquido", "posicao_mercado"}
_PCT_KEYS = {"rentab", "rentab_liquida", "rentab_bruta"}


def rf_ctx(section_id: str) -> dict:
    snap_rf = load_snapshot("RF")
    cfg = RF_CONFIG[section_id]
    dados = snap_rf.get("dados", {}) if snap_rf else {}
    posicoes = []
    for cls in cfg["classes"]:
        posicoes += dados.get("classes", {}).get(cls, {}).get("posicoes", [])

    linhas = []
    tot = 0.0
    for p in posicoes:
        linha = {}
        for label, key in cfg["colunas"]:
            v = p.get(key)
            if key in _MONEY_KEYS:
                linha[label] = brl(v)
            elif key in _PCT_KEYS:
                linha[label] = pct((v or 0) * 100) if v is not None else "—"
            else:
                linha[label] = str(v) if v is not None else "—"
        linhas.append(linha)
        tot += float(p.get(cfg["total_field"]) or 0)

    return {
        "titulo": cfg["titulo"], "colunas": [c[0] for c in cfg["colunas"]],
        "linhas": linhas, "vazio": not posicoes, "total": brl(tot), "nota": cfg["nota"],
    }


# ─── Evolução ─────────────────────────────────────────────────────────────────
def evolucao_ctx() -> dict:
    r = sb.table("carteira_historico").select("*").order("data").execute()
    rows = r.data or []
    if not rows:
        return {"vazio": True}

    for row in rows:
        row["_data_dt"] = datetime.fromisoformat(row["data"])
    ultimo = rows[-1]
    valores = [float(row["total_atual"]) for row in rows]
    vmin, vmax = min(valores + [CAPITAL_BASE]), max(valores + [CAPITAL_BASE])
    pad = (vmax - vmin) * 0.08 or 1000
    vmin -= pad
    vmax += pad
    largura, altura = 760, 260
    n = len(rows)

    def x_of(i):
        return 0 if n == 1 else round(i / (n - 1) * largura, 1)

    def y_of(v):
        return round(altura - (v - vmin) / (vmax - vmin) * altura, 1)

    pontos_patrimonio = " ".join(f"{x_of(i)},{y_of(v)}" for i, v in enumerate(valores))
    y_base = y_of(CAPITAL_BASE)

    tabela = []
    for row in reversed(rows):
        tabela.append({
            "data": row["_data_dt"].strftime("%d/%m/%Y"),
            "patrimonio": brl(float(row["total_atual"])),
            "ganho": brl(float(row["total_ganho"]), sign=True),
            "rentab": pct(float(row["total_rentab"])),
        })

    return {
        "vazio": False,
        "kpi_ultimo": brl(float(ultimo["total_atual"])),
        "kpi_ganho": brl(float(ultimo["total_ganho"]), sign=True),
        "kpi_rentab": pct(float(ultimo["total_rentab"])),
        "svg_w": largura, "svg_h": altura,
        "pontos_patrimonio": pontos_patrimonio, "y_base": y_base,
        "tabela": tabela,
    }


# ─── Escritório ───────────────────────────────────────────────────────────────
TAXA_ESCRITORIO = 0.01  # rendimento = sempre 1% do saldo do mês anterior
TIPOS_ESCRITORIO = ["Honorários", "Êxito", "Consultoria",
                     "Aporte de Sócio", "Retirada / Pró-labore", "Outro"]


def load_investimentos() -> list[dict]:
    r = sb.table("investimentos_escritorio").select("*").order("mes").execute()
    return r.data or []


def _ultimo_saldo_escritorio(inv_plot: list[dict]) -> float:
    return float(inv_plot[-1]["saldo_final"]) if inv_plot else 0.0


def escritorio_ctx() -> dict:
    inv = load_investimentos()
    inv_plot = [i for i in inv if float(i.get("saldo_final") or 0) > 0]
    ctx = {
        "vazio": not inv_plot, "tipos": TIPOS_ESCRITORIO,
        "ultimo_saldo": _ultimo_saldo_escritorio(inv_plot), "taxa": TAXA_ESCRITORIO,
    }
    if not inv_plot:
        return ctx

    ultimo = inv_plot[-1]
    primeiro = inv_plot[0]
    saldo_v = float(ultimo["saldo_final"])
    rend_v = float(ultimo["rendimento"])
    saldo_ini = float(primeiro["saldo_final"])
    rentab_total = (saldo_v / saldo_ini - 1) * 100 if saldo_ini else 0
    total_rend = sum(float(i.get("rendimento") or 0) for i in inv)

    # Gráfico combinado (rendimento em barra + saldo em linha), mesma escala,
    # igual ao original em Plotly.
    valores_saldo = [float(i["saldo_final"]) for i in inv_plot]
    valores_rend = [float(i["rendimento"] or 0) for i in inv_plot]
    todos_valores = valores_saldo + valores_rend + [0]
    vmin, vmax = min(todos_valores), max(todos_valores)
    pad = (vmax - vmin) * 0.06 or 1000
    vmax += pad
    largura, altura = 760, 260
    n = len(inv_plot)
    barw = min(28, largura / max(n, 1) * 0.5)

    def x_of(i):
        return 40 if n == 1 else round(40 + i / (n - 1) * (largura - 80), 1)

    def y_of(v):
        return round(altura - (v - vmin) / (vmax - vmin) * altura, 1)

    barras = []
    for i, v in enumerate(valores_rend):
        x = x_of(i)
        y_topo = y_of(v)
        barras.append({"x": round(x - barw / 2, 1), "y": y_topo, "w": round(barw, 1),
                        "h": round(altura - y_topo, 1)})
    pontos_saldo = " ".join(f"{x_of(i)},{y_of(v)}" for i, v in enumerate(valores_saldo))

    linhas = []
    for i in reversed(inv_plot):
        linhas.append({
            "mes": datetime.fromisoformat(i["mes"]).strftime("%b/%Y"),
            "tipo": i["tipo"],
            "aporte": brl(float(i["valor"] or 0), sign=True),
            "rendimento": brl(float(i["rendimento"] or 0)),
            "saldo_final": brl(float(i["saldo_final"] or 0)),
        })

    ctx.update({
        "kpi_saldo": brl(saldo_v), "kpi_rend_ultimo": brl(rend_v),
        "kpi_rend_acum": brl(total_rend), "kpi_rentab": pct(rentab_total),
        "rentab_positiva": rentab_total >= 0,
        "desde": primeiro["mes"] and datetime.fromisoformat(primeiro["mes"]).strftime("%b/%Y"),
        "svg_w": largura, "svg_h": altura, "barras": barras, "pontos_saldo": pontos_saldo,
        "linhas": linhas,
        "ultimo_mes_fmt": datetime.fromisoformat(ultimo["mes"]).strftime("%b/%Y"),
        "ultimo_tipo": ultimo["tipo"], "ultimo_saldo_fmt": brl(saldo_v),
        "ultimo_mes_iso": ultimo["mes"],
    })
    return ctx


# ─── Meus Empréstimos (Lucas é o devedor) ─────────────────────────────────────
CORES_CREDOR = [VERDE, "#3A7D5A", OURO, "#D4A017", "#7BA98C", "#C9A227"]


def load_emprestimos_meus() -> list[dict]:
    r = sb.table("emprestimos").select("*").eq("status", "ativo").order("credor").execute()
    return r.data or []


def _fmt_data_me(v) -> str:
    try:
        return datetime.strptime(str(v), "%Y-%m-%d").strftime("%d/%m/%Y")
    except Exception:
        return str(v or "—")


def historico_meus_ctx() -> dict:
    r = sb.table("emprestimos").select(
        "id,titulo,credor,status,saldo_devedor,taxa_juros,historico_pagamentos").execute()
    contratos = []
    for r_h in (r.data or []):
        hist = r_h.get("historico_pagamentos") or []
        if not hist:
            continue
        is_quitado = (r_h.get("status") == "quitado") or (float(r_h.get("saldo_devedor") or 0) <= 0)
        ultimo_idx = -1 if is_quitado else (len(hist) - 1)
        indexed = list(enumerate(hist))[::-1]
        pagamentos = []
        for idx, hp in indexed:
            pagamentos.append({
                "idx": idx, "is_ultimo": (idx == ultimo_idx),
                "data": _fmt_data_me(hp.get("data")),
                "valor_pago": brl(hp.get("valor_pago")),
                "juros": brl(hp.get("juros")),
                "amortizacao": brl(hp.get("amortizacao")),
                "saldo_depois": brl(hp.get("saldo_depois")),
                "obs": str(hp.get("obs") or ""),
            })
        contratos.append({
            "eid": r_h["id"], "titulo": r_h["titulo"], "credor": r_h.get("credor", ""),
            "is_quitado": is_quitado,
            "total_pago": brl(sum(float(h.get("valor_pago") or 0) for h in hist)),
            "saldo_atual": brl(float(r_h.get("saldo_devedor") or 0)),
            "n_pagamentos": len(hist),
            "pagamentos": pagamentos,
        })
    return {"contratos": contratos, "vazio": not contratos}


def meus_emprestimos_ctx() -> dict:
    emp = load_emprestimos_meus()
    ctx: dict = {"vazio": not emp}
    if emp:
        total_divida = sum(float(e["saldo_devedor"] or 0) for e in emp)
        total_juros = sum(float(e["parcela_juros"] or 0) for e in emp)
        grp: dict[str, float] = {}
        for e in emp:
            grp[e["credor"]] = grp.get(e["credor"], 0) + float(e["saldo_devedor"] or 0)
        fatias = []
        acumulado = 0.0
        for i, (credor, valor) in enumerate(sorted(grp.items(), key=lambda x: -x[1])):
            pct_v = valor / total_divida * 100 if total_divida else 0
            fatias.append({
                "credor": credor, "valor_fmt": brl(valor), "pct": pct_v,
                "cor": CORES_CREDOR[i % len(CORES_CREDOR)],
                "de": round(acumulado, 4), "ate": round(acumulado + pct_v, 4),
            })
            acumulado += pct_v
        ctx.update({
            "kpi_total_divida": brl(total_divida), "kpi_total_juros": brl(total_juros),
            "kpi_n_contratos": len(emp), "fatias": fatias,
            "contratos": [{
                "id": e["id"], "credor": e["credor"], "titulo": e["titulo"],
                "saldo": brl(float(e["saldo_devedor"] or 0)),
                "taxa": f"{float(e['taxa_juros'] or 0) * 100:.2f}%".replace(".", ","),
                "juros_mes": brl(float(e["parcela_juros"] or 0)),
            } for e in emp],
        })
    ctx["historico"] = historico_meus_ctx()
    return ctx


# ─── Auth ─────────────────────────────────────────────────────────────────────
def current_user(request: Request):
    return request.session.get("user_email")


def require_login(request: Request):
    if not current_user(request):
        return None
    return current_user(request)


@app.get("/login", response_class=HTMLResponse)
def login_page(request: Request, erro: str | None = None):
    if current_user(request):
        return RedirectResponse("/", status_code=303)
    return templates.TemplateResponse(request, "login.html", {"erro": erro})


@app.post("/login")
def login_submit(request: Request, email: str = Form(...), senha: str = Form(...)):
    try:
        r = sb_auth.auth.sign_in_with_password({"email": email, "password": senha})
        request.session["user_email"] = r.user.email
        return RedirectResponse("/", status_code=303)
    except Exception:
        return RedirectResponse("/login?erro=1", status_code=303)


@app.get("/logout")
def logout(request: Request):
    request.session.clear()
    return RedirectResponse("/login", status_code=303)


# ─── Navegação / conteúdo ─────────────────────────────────────────────────────
def content_for(section: str, sub: str | None) -> tuple[str, dict]:
    if section == "resumo":
        return "content_resumo.html", resumo_ctx()
    if section in RV_BR_CLASSES:
        return "content_rv_br.html", rv_br_ctx(RV_BR_CLASSES[section])
    if section == "intl":
        return "content_internacional.html", internacional_ctx(sub or "etfusa")
    if section in RF_CONFIG:
        return "content_rf.html", rf_ctx(section)
    if section == "evolucao":
        return "content_evolucao.html", evolucao_ctx()
    if section == "escritorio":
        return "content_escritorio.html", escritorio_ctx()
    if section == "emprestimos" and sub == "meus":
        return "content_meus_emprestimos.html", meus_emprestimos_ctx()
    item = next((n for n in NAV if n["id"] == section), NAV[0])
    label = item["label"]
    if item.get("subs") and sub:
        sub_label = next((s["label"] for s in item["subs"] if s["id"] == sub), "")
        label = f"{label} — {sub_label}"
    return "content_em_construcao.html", {"titulo": f"{item['icon']} {label}"}


@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    user = current_user(request)
    if not user:
        return RedirectResponse("/login", status_code=303)
    tmpl, ctx = content_for("resumo", None)
    content_html = templates.get_template(tmpl).render(request=request, user_email=user, **ctx)
    return templates.TemplateResponse(request, "layout.html", {
        "nav": NAV, "active": "resumo", "active_sub": None,
        "content_html": content_html, "user_email": user,
    })


@app.get("/nav/{section}", response_class=HTMLResponse)
def nav(request: Request, section: str, sub: str | None = None):
    user = current_user(request)
    if not user:
        return RedirectResponse("/login", status_code=303)
    item = next((n for n in NAV if n["id"] == section), None)
    if item and item.get("subs") and not sub:
        sub = item["subs"][0]["id"]
    tmpl, ctx = content_for(section, sub)
    content_html = templates.get_template(tmpl).render(request=request, user_email=user, **ctx)
    return templates.TemplateResponse(request, "nav_response.html", {
        "nav": NAV, "active": section, "active_sub": sub,
        "content_html": content_html,
    })


@app.post("/atualizar-cotacoes", response_class=HTMLResponse)
def atualizar_cotacoes(request: Request):
    if not current_user(request):
        return RedirectResponse("/login", status_code=303)
    return templates.TemplateResponse(request, "atualizacao_resultado.html",
                                       atualizar_cotacoes_ctx())


@app.post("/escritorio/lancar", response_class=HTMLResponse)
def escritorio_lancar(request: Request, mes: str = Form(...), tipo: str = Form(...),
                       valor: str = Form(...)):
    if not current_user(request):
        return RedirectResponse("/login", status_code=303)
    inv = load_investimentos()
    inv_plot = [i for i in inv if float(i.get("saldo_final") or 0) > 0]
    ultimo_saldo = _ultimo_saldo_escritorio(inv_plot)
    valor_v = parse_brl(valor)
    eh_retirada = (tipo == "Retirada / Pró-labore")
    valor_efet = -valor_v if eh_retirada else valor_v
    rend_v = round(ultimo_saldo * TAXA_ESCRITORIO, 2)
    saldo_calc = round(ultimo_saldo + valor_efet + rend_v, 2)
    try:
        sb.table("investimentos_escritorio").upsert({
            "mes": f"{mes}-01", "tipo": tipo, "valor": round(valor_efet, 2),
            "rendimento": rend_v, "saldo_final": saldo_calc,
            "taxa_mensal": TAXA_ESCRITORIO,
        }, on_conflict="mes").execute()
    except Exception:
        pass
    ctx = escritorio_ctx()
    return templates.TemplateResponse(request, "content_escritorio.html",
                                       {**ctx, "user_email": current_user(request)})


@app.post("/escritorio/excluir", response_class=HTMLResponse)
def escritorio_excluir(request: Request):
    if not current_user(request):
        return RedirectResponse("/login", status_code=303)
    inv = load_investimentos()
    inv_plot = [i for i in inv if float(i.get("saldo_final") or 0) > 0]
    if inv_plot:
        try:
            sb.table("investimentos_escritorio").delete().eq("mes", inv_plot[-1]["mes"]).execute()
        except Exception:
            pass
    ctx = escritorio_ctx()
    return templates.TemplateResponse(request, "content_escritorio.html",
                                       {**ctx, "user_email": current_user(request)})


def _meus_emprestimos_response(request: Request) -> HTMLResponse:
    ctx = meus_emprestimos_ctx()
    return templates.TemplateResponse(request, "content_meus_emprestimos.html",
                                       {**ctx, "user_email": current_user(request)})


@app.post("/meus-emprestimos/novo", response_class=HTMLResponse)
def meus_emprestimos_novo(request: Request, credor: str = Form(...), titulo: str = Form(...),
                           saldo: str = Form(...), taxa: str = Form(...)):
    if not current_user(request):
        return RedirectResponse("/login", status_code=303)
    saldo_v = parse_brl(saldo)
    try:
        taxa_pct = float(taxa)
    except Exception:
        taxa_pct = 0.0
    if credor and titulo and saldo_v > 0:
        parcela = round(saldo_v * taxa_pct / 100, 2)
        try:
            sb.table("emprestimos").insert({
                "credor": credor, "titulo": titulo,
                "valor_originario": round(saldo_v, 2), "saldo_devedor": round(saldo_v, 2),
                "taxa_juros": round(taxa_pct / 100, 6), "parcela_juros": parcela, "status": "ativo",
            }).execute()
        except Exception:
            pass
    return _meus_emprestimos_response(request)


@app.post("/meus-emprestimos/pagamento", response_class=HTMLResponse)
def meus_emprestimos_pagamento(request: Request, emprestimo_id: str = Form(...),
                                valor: str = Form(...), data: str = Form(...),
                                obs: str = Form("")):
    if not current_user(request):
        return RedirectResponse("/login", status_code=303)
    emp = load_emprestimos_meus()
    row = next((e for e in emp if str(e["id"]) == emprestimo_id), None)
    if row:
        saldo_at = float(row["saldo_devedor"] or 0)
        juros_mes_v = float(row["parcela_juros"] or 0)
        valor_pago_v = parse_brl(valor)
        juros_no_pag = min(valor_pago_v, juros_mes_v)
        amort_v = max(0.0, valor_pago_v - juros_no_pag)
        novo_saldo_v = max(0.0, saldo_at - amort_v)
        try:
            res_h = sb.table("emprestimos").select("historico_pagamentos").eq("id", emprestimo_id).execute()
            hist_v = (res_h.data[0].get("historico_pagamentos") or []) if res_h.data else []
            hist_v.append({
                "data": data, "valor_pago": round(valor_pago_v, 2),
                "juros": round(juros_no_pag, 2), "amortizacao": round(amort_v, 2),
                "saldo_antes": round(saldo_at, 2), "saldo_depois": round(novo_saldo_v, 2),
                "obs": obs,
            })
            upd = {"saldo_devedor": round(novo_saldo_v, 2),
                   "parcela_juros": round(novo_saldo_v * float(row["taxa_juros"] or 0), 2),
                   "historico_pagamentos": hist_v}
            if novo_saldo_v == 0:
                upd["status"] = "quitado"
            sb.table("emprestimos").update(upd).eq("id", emprestimo_id).execute()
        except Exception:
            pass
    return _meus_emprestimos_response(request)


@app.post("/meus-emprestimos/quitar", response_class=HTMLResponse)
def meus_emprestimos_quitar(request: Request, emprestimo_id: str = Form(...)):
    if not current_user(request):
        return RedirectResponse("/login", status_code=303)
    try:
        sb.table("emprestimos").update(
            {"status": "quitado", "saldo_devedor": 0.0, "parcela_juros": 0.0}
        ).eq("id", emprestimo_id).execute()
    except Exception:
        pass
    return _meus_emprestimos_response(request)


@app.get("/meus-emprestimos/linha-editar/{eid}/{idx}", response_class=HTMLResponse)
def meus_linha_editar(request: Request, eid: str, idx: int):
    if not current_user(request):
        return RedirectResponse("/login", status_code=303)
    r = sb.table("emprestimos").select("historico_pagamentos").eq("id", eid).execute()
    hist = (r.data[0].get("historico_pagamentos") or []) if r.data else []
    if idx >= len(hist):
        return HTMLResponse("")
    hp = hist[idx]
    return templates.TemplateResponse(request, "_linha_me_editar.html", {
        "eid": eid, "idx": idx,
        "data_iso": hp.get("data") or "",
        "valor_pago": brl_input(hp.get("valor_pago")),
        "juros": brl_input(hp.get("juros")),
        "obs": hp.get("obs") or "",
    })


@app.get("/meus-emprestimos/linha-normal/{eid}/{idx}", response_class=HTMLResponse)
def meus_linha_normal(request: Request, eid: str, idx: int):
    if not current_user(request):
        return RedirectResponse("/login", status_code=303)
    r = sb.table("emprestimos").select(
        "id,status,saldo_devedor,historico_pagamentos").eq("id", eid).execute()
    if not r.data:
        return HTMLResponse("")
    r_h = r.data[0]
    hist = r_h.get("historico_pagamentos") or []
    if idx >= len(hist):
        return HTMLResponse("")
    is_quitado = (r_h.get("status") == "quitado") or (float(r_h.get("saldo_devedor") or 0) <= 0)
    ultimo_idx = -1 if is_quitado else (len(hist) - 1)
    hp = hist[idx]
    pagamento = {
        "idx": idx, "is_ultimo": (idx == ultimo_idx),
        "data": _fmt_data_me(hp.get("data")), "valor_pago": brl(hp.get("valor_pago")),
        "juros": brl(hp.get("juros")), "amortizacao": brl(hp.get("amortizacao")),
        "saldo_depois": brl(hp.get("saldo_depois")), "obs": str(hp.get("obs") or ""),
    }
    return templates.TemplateResponse(request, "_linha_me_normal.html",
                                       {"eid": eid, "pagamento": pagamento})


@app.post("/meus-emprestimos/linha-salvar/{eid}/{idx}", response_class=HTMLResponse)
def meus_linha_salvar(request: Request, eid: str, idx: int, data: str = Form(...),
                       valor: str = Form(...), juros: str = Form(...), obs: str = Form("")):
    if not current_user(request):
        return RedirectResponse("/login", status_code=303)
    try:
        r = sb.table("emprestimos").select("historico_pagamentos,taxa_juros").eq("id", eid).execute()
        if r.data:
            row = r.data[0]
            hist = row.get("historico_pagamentos") or []
            taxa_c = float(row.get("taxa_juros") or 0)
            if idx < len(hist):
                hp = hist[idx]
                novo_val_pago = round(parse_brl(valor), 2)
                juros_digitado = round(parse_brl(juros), 2)
                juros_aplicado = round(min(novo_val_pago, max(0.0, juros_digitado)), 2)
                nova_amort = round(max(0.0, novo_val_pago - juros_aplicado), 2)
                saldo_antes_e = float(hp.get("saldo_antes") or 0)
                novo_saldo_e = round(max(0.0, saldo_antes_e - nova_amort), 2)
                hist[idx] = {
                    "data": data, "valor_pago": novo_val_pago, "juros": juros_aplicado,
                    "amortizacao": nova_amort, "saldo_antes": round(saldo_antes_e, 2),
                    "saldo_depois": novo_saldo_e, "obs": obs,
                }
                novo_parcela_e = round(novo_saldo_e * taxa_c, 2)
                sb.table("emprestimos").update({
                    "historico_pagamentos": hist, "saldo_devedor": novo_saldo_e,
                    "parcela_juros": novo_parcela_e,
                    "status": "quitado" if novo_saldo_e <= 0 else "ativo",
                }).eq("id", eid).execute()
    except Exception:
        pass
    return _meus_emprestimos_response(request)


@app.post("/meus-emprestimos/linha-excluir/{eid}/{idx}", response_class=HTMLResponse)
def meus_linha_excluir(request: Request, eid: str, idx: int):
    if not current_user(request):
        return RedirectResponse("/login", status_code=303)
    try:
        r = sb.table("emprestimos").select("historico_pagamentos,taxa_juros").eq("id", eid).execute()
        if r.data:
            row = r.data[0]
            hist = row.get("historico_pagamentos") or []
            taxa_c = float(row.get("taxa_juros") or 0)
            if idx < len(hist):
                removido = hist.pop(idx)
                novo_saldo_d = round(float(removido.get("saldo_antes") or 0), 2)
                novo_parcela_d = round(novo_saldo_d * taxa_c, 2)
                sb.table("emprestimos").update({
                    "historico_pagamentos": hist, "saldo_devedor": novo_saldo_d,
                    "parcela_juros": novo_parcela_d,
                    "status": "quitado" if novo_saldo_d <= 0 else "ativo",
                }).eq("id", eid).execute()
    except Exception:
        pass
    return _meus_emprestimos_response(request)
