"""
Painel Lucas — versão FastAPI + HTMX (migração em andamento).

Convive com o app Streamlit original: mesmo Supabase, mesma autenticação.
Módulos ainda não portados mostram uma tela "em construção" honesta em vez
de fingir que existem.
"""
import os
import secrets
from datetime import datetime

from fastapi import FastAPI, Request, Form, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware
from supabase import create_client

import quotes

# ─── Config ───────────────────────────────────────────────────────────────────
def _secret(key: str) -> str | None:
    return os.environ.get(key)

SUPABASE_URL = _secret("SUPABASE_URL")
SUPABASE_KEY = _secret("SUPABASE_KEY")
SESSION_SECRET = _secret("SESSION_SECRET") or secrets.token_hex(32)

VERDE = "#1A4731"
OURO  = "#B8860B"
CAPITAL_BASE = 684_160.69

sb = create_client(SUPABASE_URL, SUPABASE_KEY)

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
        r = sb.auth.sign_in_with_password({"email": email, "password": senha})
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
