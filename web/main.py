"""
Painel Lucas — versão FastAPI + HTMX (migração em andamento).

Convive com o app Streamlit original: mesmo Supabase, mesma autenticação.
Módulos ainda não portados mostram uma tela "em construção" honesta em vez
de fingir que existem.
"""
import os
import secrets

from fastapi import FastAPI, Request, Form, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware
from supabase import create_client

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


def brl(v: float, sign: bool = False) -> str:
    s = f"{abs(v):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    prefix = ("+" if v >= 0 else "-") if sign else ("-" if v < 0 else "")
    return f"R$ {prefix}{s}"


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
