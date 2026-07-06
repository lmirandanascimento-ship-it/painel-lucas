import streamlit as st
from supabase import create_client
import pandas as pd
import plotly.graph_objects as go
import requests
import yfinance as yf
from datetime import datetime

# ─── Configuração ─────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="3P Finanças | Painel Lucas",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="collapsed",
)

VERDE        = "#1A4731"
VERDE2       = "#2D6A4F"
OURO         = "#B8860B"
CAPITAL_BASE = 684_160.69
BRAPI_TOKEN  = "o1ikT8zCSyqQUkNYz224ho"

INTL_CLASSES = {"ETF USA", "REITs", "Stocks"}
CLASS_COLORS = {
    "Ações BR": "#22C55E", "ETF BR": "#16A34A", "FII": "#3B82F6",
    "ETF USA":  "#F59E0B", "REITs":  "#F97316", "Stocks": "#EF4444",
    "CDB": "#8B5CF6", "LCI/LCA": "#06B6D4", "CRI/CRA": "#0EA5E9",
    "Fundos": "#EC4899", "Tesouro Direto": "#D97706",
}

# ─── CSS ──────────────────────────────────────────────────────────────────────
st.markdown(f"""
<style>
.stApp {{ background:#FFFBEF; }}
.header-3p {{
    background:{VERDE}; padding:14px 28px; border-radius:10px;
    margin-bottom:18px; display:flex; justify-content:space-between; align-items:center;
}}
.kpi-card {{
    background:white; border:1px solid #E8E4D0;
    border-left:5px solid {VERDE}; border-radius:8px; padding:16px 18px;
}}
.kpi-card.ouro  {{ border-left-color:{OURO}; }}
.kpi-card.neg   {{ border-left-color:#B71C1C; }}
.kpi-value  {{ font-size:1.6rem; font-weight:800; color:#1A1A1A; }}
.kpi-label  {{ font-size:0.78rem; color:#777; margin-top:5px; }}
.kpi-sub    {{ font-size:0.75rem; color:#999; margin-top:3px; }}
.alerta-ouro {{
    background:#FFFBEB; border-left:4px solid {OURO};
    padding:12px 16px; border-radius:6px; margin-top:10px;
}}
.pos {{ color:#1B7A34; font-weight:700; }}
.neg {{ color:#B71C1C; font-weight:700; }}
#MainMenu {{visibility:hidden;}} footer {{visibility:hidden;}}
</style>
""", unsafe_allow_html=True)


# ─── Supabase ─────────────────────────────────────────────────────────────────
@st.cache_resource
def get_sb():
    return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])

sb = get_sb()


# ─── Utilitários ──────────────────────────────────────────────────────────────
def brl(v, sign=False):
    if v is None: return "—"
    v = float(v)
    s = f"{abs(v):,.2f}".replace(",","X").replace(".",",").replace("X",".")
    prefix = ("+" if v >= 0 else "-") if sign else ("-" if v < 0 else "")
    return f"R$ {prefix}{s}"

def pct(v, sign=True):
    if v is None: return "—"
    v = float(v)
    s = f"{abs(v):.2f}%".replace(".",",")
    prefix = ("+" if v >= 0 else "-") if sign else ""
    return f"{prefix}{s}"

def cor_pct(v):
    if v is None: return ""
    return "pos" if float(v) >= 0 else "neg"

def html_pct(v):
    if v is None: return "—"
    cls = cor_pct(v)
    return f'<span class="{cls}">{pct(v)}</span>'


# ─── Autenticação ─────────────────────────────────────────────────────────────
def pagina_login():
    _, col, _ = st.columns([1, 1.2, 1])
    with col:
        st.markdown(f"""
        <div style='text-align:center; padding:40px 0 20px'>
            <h1 style='color:{VERDE}; font-size:2rem; margin-bottom:4px'>3P FINANÇAS</h1>
            <p style='color:{OURO}; font-style:italic; font-size:.95rem; margin:0'>
                Planejar · Poupar · Prosperar
            </p>
        </div>""", unsafe_allow_html=True)
        st.markdown("<br>", unsafe_allow_html=True)
        email = st.text_input("E-mail", placeholder="seu@email.com")
        senha = st.text_input("Senha", type="password")
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("Entrar", use_container_width=True, type="primary"):
            if not email or not senha:
                st.warning("Preencha e-mail e senha.")
                return
            try:
                r = sb.auth.sign_in_with_password({"email": email, "password": senha})
                st.session_state["user"] = r.user
                st.rerun()
            except Exception:
                st.error("E-mail ou senha incorretos.")


# ─── Carga de dados ───────────────────────────────────────────────────────────
@st.cache_data(ttl=300, show_spinner=False)
def load_snapshot(tipo: str) -> dict:
    """Retorna o snapshot mais recente (RV ou RF) como dict."""
    r = (sb.table("carteira_snapshots")
           .select("data,dados,usd_brl,total_investido,total_atual")
           .eq("tipo", tipo)
           .order("data", desc=True)
           .limit(1)
           .execute())
    if r.data:
        return r.data[0]
    return {}

@st.cache_data(ttl=300, show_spinner=False)
def load_posicoes_rv() -> pd.DataFrame:
    """Posições RV mais recentes (para cotações ao vivo)."""
    r = (sb.table("carteira_rv_posicoes")
           .select("*")
           .order("data_snapshot", desc=True)
           .limit(200)
           .execute())
    if not r.data:
        return pd.DataFrame()
    df = pd.DataFrame(r.data)
    # Apenas a data mais recente
    if not df.empty:
        df = df[df["data_snapshot"] == df["data_snapshot"].max()]
    return df

@st.cache_data(ttl=300, show_spinner=False)
def load_historico() -> pd.DataFrame:
    r = (sb.table("carteira_historico")
           .select("*")
           .order("data")
           .execute())
    if not r.data:
        return pd.DataFrame()
    df = pd.DataFrame(r.data)
    df["data"] = pd.to_datetime(df["data"])
    return df

@st.cache_data(ttl=300, show_spinner=False)
def load_emprestimos() -> pd.DataFrame:
    r = sb.table("emprestimos").select("*").eq("status","ativo").order("credor").execute()
    return pd.DataFrame(r.data) if r.data else pd.DataFrame()

@st.cache_data(ttl=300, show_spinner=False)
def load_investimentos() -> pd.DataFrame:
    r = sb.table("investimentos_escritorio").select("*").order("mes").execute()
    df = pd.DataFrame(r.data) if r.data else pd.DataFrame()
    if not df.empty:
        df["mes"] = pd.to_datetime(df["mes"])
    return df

@st.cache_data(ttl=600, show_spinner=False)
def fetch_usd_brl() -> float:
    """Retorna cotação USD/BRL."""
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

@st.cache_data(ttl=600, show_spinner=False)
def fetch_precos_br(tickers_br: tuple) -> dict:
    """Retorna preços de ativos BR via BRAPI."""
    prices = {}
    if not tickers_br:
        return prices
    try:
        tks = [t + ".SA" if not t.endswith(".SA") else t for t in tickers_br]
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
    return prices

@st.cache_data(ttl=600, show_spinner=False)
def fetch_precos_us(tickers_us: tuple) -> dict:
    """Retorna preços de ativos US via yfinance."""
    prices = {}
    if not tickers_us:
        return prices
    try:
        tks_str = " ".join(tickers_us)
        data = yf.download(tks_str, period="2d", auto_adjust=True, progress=False)
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

# mantido para compatibilidade de assinatura em locais que chamam com dois args
@st.cache_data(ttl=600, show_spinner=False)
def fetch_precos_brapi(tickers_br: tuple, tickers_us: tuple) -> tuple:
    """Retorna (dict_precos_br+us, usd_brl)."""
    prices = fetch_precos_br(tickers_br)
    prices.update(fetch_precos_us(tickers_us))
    usd_brl = fetch_usd_brl()
    return prices, usd_brl


# ─── Header ───────────────────────────────────────────────────────────────────
def render_header():
    user = st.session_state.get("user")
    nome = (user.email or "").split("@")[0].capitalize()
    st.markdown(f"""
    <div class='header-3p'>
        <div>
            <span style='color:{OURO};font-size:1.2rem;font-weight:800'>3P FINANÇAS</span>
            <span style='color:#bbb;font-size:.85rem;margin-left:14px'>Planejar · Poupar · Prosperar</span>
        </div>
        <div style='color:#ddd;font-size:.82rem'>
            📅 {datetime.now().strftime("%d/%m/%Y")} &nbsp;|&nbsp; 👤 {nome}
        </div>
    </div>""", unsafe_allow_html=True)


# ─── TAB: RESUMO ──────────────────────────────────────────────────────────────
def tab_resumo(snap_rv, snap_rf, posicoes_rv):
    dados_rv = snap_rv.get("dados", {}) if snap_rv else {}
    dados_rf = snap_rf.get("dados", {}) if snap_rf else {}
    rv_tot   = float(snap_rv.get("total_atual", 0) or 0)
    rf_tot   = float(snap_rf.get("total_atual", 0) or 0)
    total    = rv_tot + rf_tot
    ganho    = total - CAPITAL_BASE
    rentab   = ganho / CAPITAL_BASE * 100 if CAPITAL_BASE else 0
    usd_brl  = float(snap_rv.get("usd_brl", 5.75) or 5.75)

    # Botão cotações ao vivo
    c_btn, c_status = st.columns([2, 6])
    with c_btn:
        if st.button("🔄 Atualizar Cotações", type="secondary"):
            st.cache_data.clear()
            st.rerun()
    with c_status:
        data_rv = snap_rv.get("data","—") if snap_rv else "—"
        st.caption(f"RV: snapshot de {data_rv} · RF: snapshot de {snap_rf.get('data','—') if snap_rf else '—'} · USD/BRL: {usd_brl:.4f}")

    # KPIs
    c1, c2, c3, c4, c5 = st.columns(5)
    def kpi(col, label, valor, sub="", cls=""):
        col.markdown(f"""
        <div class='kpi-card {cls}'>
            <div class='kpi-value'>{valor}</div>
            <div class='kpi-label'>{label}</div>
            {'<div class="kpi-sub">'+sub+'</div>' if sub else ''}
        </div>""", unsafe_allow_html=True)

    kpi(c1, "Patrimônio Total",        brl(total), "Valor de mercado atual")
    kpi(c2, "Capital Inicial (ref.)",  brl(CAPITAL_BASE), "Mar/2026", "ouro")
    cls_g = "" if ganho >= 0 else "neg"
    kpi(c3, "Lucro Acumulado",         brl(ganho, sign=True), pct(rentab), cls_g)
    kpi(c4, "Renda Variável (snapshot)",brl(rv_tot), f"Ref. {data_rv}")
    kpi(c5, "Renda Fixa (snapshot)",   brl(rf_tot))

    st.markdown("<br>", unsafe_allow_html=True)

    # Pizza composição
    st.markdown(f"#### 🍕 Composição do Patrimônio")
    classes_vals = {}
    for cls, data in dados_rv.get("classes", {}).items():
        v = data.get("atual", 0) or 0
        if v > 0: classes_vals[cls] = v
    for cls, data in dados_rf.get("classes", {}).items():
        v = data.get("atual", 0) or 0
        if v > 0: classes_vals[cls] = round(classes_vals.get(cls, 0) + v, 2)

    if classes_vals:
        labels = list(classes_vals.keys())
        values = [classes_vals[k] for k in labels]
        colors = [CLASS_COLORS.get(k, "#999") for k in labels]
        fig = go.Figure(go.Pie(
            labels=labels, values=values, hole=0.6,
            marker_colors=colors,
            textinfo="percent",
            textfont_size=12,
        ))
        fig.update_layout(
            height=340, margin=dict(l=0,r=0,t=0,b=0),
            paper_bgcolor="#FFFBEF",
            legend=dict(orientation="v", x=1.0, y=0.5),
            annotations=[dict(text=brl(total), x=0.5, y=0.5,
                              font_size=14, showarrow=False)],
        )
        c_pizza, c_leg = st.columns([1.3, 1])
        with c_pizza:
            st.plotly_chart(fig, use_container_width=True)
        with c_leg:
            st.markdown("<br>", unsafe_allow_html=True)
            sorted_cls = sorted(classes_vals.items(), key=lambda x: -x[1])
            for k, v in sorted_cls:
                pct_v = v / total * 100 if total else 0
                cor = CLASS_COLORS.get(k, "#999")
                st.markdown(
                    f'<div style="display:flex;align-items:center;gap:10px;padding:4px 0">'
                    f'<span style="width:12px;height:12px;background:{cor};border-radius:3px;flex-shrink:0;display:inline-block"></span>'
                    f'<span style="flex:1;font-size:13px">{k}</span>'
                    f'<span style="font-size:12px;color:#777">{pct_v:.1f}%</span>'
                    f'<span style="font-size:13px;font-weight:700;min-width:110px;text-align:right">{brl(v)}</span>'
                    f'</div>', unsafe_allow_html=True)


# ─── TAB: Ativos RV BR (Ações, ETF, FII) ─────────────────────────────────────
def tab_rv_br(classe: str, snap_rv, posicoes_rv):
    dados = snap_rv.get("dados", {}) if snap_rv else {}
    cls_data = dados.get("classes", {}).get(classe, {})
    posicoes = cls_data.get("posicoes", [])

    if not posicoes:
        st.info("Nenhuma posição nesta classe no snapshot atual.")
        return

    # Buscar cotações ao vivo
    tickers = [p.get("nome","") for p in posicoes if p.get("nome")]
    prices, usd_brl = {}, 5.75
    if not posicoes_rv.empty:
        pos_cls = posicoes_rv[posicoes_rv["classe"] == classe]
        tickers_br = tuple(pos_cls["ticker"].tolist())
        if tickers_br:
            with st.spinner("Buscando cotações..."):
                prices, usd_brl = fetch_precos_brapi(tickers_br, ())

    # Montar tabela
    rows = []
    tot_inv = 0.0; tot_at = 0.0
    for p in posicoes:
        nome    = p.get("nome", "")
        inv     = float(p.get("investido") or 0)
        at_snap = float(p.get("atual") or 0)

        # Preço ao vivo
        ticker_live = nome.replace(".SA","") if nome.endswith(".SA") else nome
        preco_live  = prices.get(ticker_live) or prices.get(nome)
        qtd_val     = float(p.get("qtd") or 0)
        at_live     = preco_live * qtd_val if preco_live and qtd_val else at_snap
        ren = (at_live / inv - 1) * 100 if inv else 0

        tot_inv += inv
        tot_at  += at_live

        rows.append({
            "Ativo":         nome,
            "Setor":         p.get("setor",""),
            "Qtd":           f"{qtd_val:g}" if qtd_val else "—",
            "PM (R$)":       brl(p.get("preco_pago_brl") or (inv / qtd_val if qtd_val else None)),
            "Cotação":       brl(preco_live) if preco_live else "⟳",
            "Investido":     brl(inv),
            "Posição Atual": brl(at_live),
            "Ganho":         brl(at_live - inv, sign=True),
            "%":             pct(ren),
            "_ren":          ren,
        })

    # Total
    ren_tot = (tot_at / tot_inv - 1) * 100 if tot_inv else 0
    rows.append({
        "Ativo": "TOTAL", "Setor": "", "Qtd": "", "PM (R$)": "",
        "Cotação": "", "Investido": brl(tot_inv), "Posição Atual": brl(tot_at),
        "Ganho": brl(tot_at - tot_inv, sign=True), "%": pct(ren_tot), "_ren": ren_tot,
    })

    df = pd.DataFrame(rows)
    df_show = df.drop(columns=["_ren"])

    # Destacar linhas positivas/negativas
    def highlight(row):
        if row["Ativo"] == "TOTAL":
            return ["background:#F0EDD8; font-weight:700"] * len(row)
        ren = df.loc[row.name, "_ren"]
        if ren <= -10: bg = "#FFF9C4"
        elif ren >= 10: bg = "#C8E6C9"
        else: bg = ""
        return [f"background:{bg}" if bg else ""] * len(row)

    st.dataframe(df_show.style.apply(highlight, axis=1),
                 use_container_width=True, hide_index=True, height=350)

    st.caption(f"Cotações: BRAPI ao vivo | Snapshot: {snap_rv.get('data','—')}")


# ─── TAB: Ativos Internacionais ───────────────────────────────────────────────
def tab_internacional(snap_rv, posicoes_rv):
    dados = snap_rv.get("dados", {}) if snap_rv else {}
    usd_brl = float(snap_rv.get("usd_brl", 5.75) or 5.75)

    # Buscar tickers US
    pos_us = pd.DataFrame()
    if not posicoes_rv.empty:
        pos_us = posicoes_rv[posicoes_rv["moeda"] == "USD"]
    tickers_us = tuple(pos_us["ticker"].tolist()) if not pos_us.empty else ()
    prices = {}
    if tickers_us:
        with st.spinner("Buscando cotações internacionais..."):
            prices, usd_brl = fetch_precos_brapi((), tickers_us)

    tabs_intl = st.tabs(["📊 ETF USA", "🏠 REITs", "📈 Stocks"])

    for tab_obj, classe in zip(tabs_intl, ["ETF USA", "REITs", "Stocks"]):
        with tab_obj:
            cls_data = dados.get("classes", {}).get(classe, {})
            posicoes = cls_data.get("posicoes", [])
            if not posicoes:
                st.info("Sem posições.")
                continue

            rows = []
            tot_inv = 0.0; tot_at = 0.0
            for p in posicoes:
                nome     = p.get("nome", "")
                inv_brl  = float(p.get("investido") or 0)
                at_snap  = float(p.get("atual") or 0)
                qtd      = float(p.get("qtd") or 0)
                pm_usd   = float(p.get("preco_pago_usd") or p.get("preco_atual_usd") or 0)
                p_live   = prices.get(nome)
                at_live  = p_live * qtd * usd_brl if p_live and qtd else at_snap
                ren      = (at_live / inv_brl - 1) * 100 if inv_brl else 0
                tot_inv += inv_brl; tot_at += at_live

                rows.append({
                    "Ativo":       nome,
                    "Setor":       p.get("setor",""),
                    "Qtd":         f"{qtd:g}" if qtd else "—",
                    "PM (US$)":    f"US$ {pm_usd:,.2f}" if pm_usd else "—",
                    "Cotação":     f"US$ {p_live:,.2f}" if p_live else "⟳",
                    "Inv. (R$)":   brl(inv_brl),
                    "Posição (R$)":brl(at_live),
                    "Ganho (R$)":  brl(at_live - inv_brl, sign=True),
                    "%":           pct(ren),
                })
            ren_t = (tot_at / tot_inv - 1) * 100 if tot_inv else 0
            rows.append({"Ativo":"TOTAL","Setor":"","Qtd":"","PM (US$)":"",
                         "Cotação":"","Inv. (R$)":brl(tot_inv),"Posição (R$)":brl(tot_at),
                         "Ganho (R$)":brl(tot_at-tot_inv,sign=True),"%":pct(ren_t)})
            st.dataframe(pd.DataFrame(rows), use_container_width=True,
                         hide_index=True, height=300)
    st.caption(f"USD/BRL: {usd_brl:.4f} · Cotações: BRAPI")


# ─── TAB genérica RF ─────────────────────────────────────────────────────────
def _tbl_rf(posicoes, colunas, total_field="atual"):
    if not posicoes:
        st.info("Sem dados disponíveis.")
        return
    rows = []
    tot = 0.0
    for p in posicoes:
        row = {}
        for col_label, col_key in colunas:
            v = p.get(col_key)
            if col_key in ("atual","investido","ganho","valor_liquido","posicao_mercado"):
                row[col_label] = brl(v)
            elif col_key in ("rentab","rentab_liquida","rentab_bruta"):
                row[col_label] = pct((v or 0) * 100) if v is not None else "—"
            else:
                row[col_label] = str(v) if v is not None else "—"
        rows.append(row)
        tot += float(p.get(total_field) or 0)

    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
    st.metric("Total", brl(tot))


def tab_tesouro(snap_rf):
    dados = snap_rf.get("dados", {}) if snap_rf else {}
    posicoes = dados.get("classes", {}).get("Tesouro Direto", {}).get("posicoes", [])
    colunas = [
        ("Título",    "nome"),
        ("Qtd",       "qtd"),
        ("Vencimento","vencimento"),
        ("Taxa",      "tipo_taxa"),
        ("Investido", "investido"),
        ("Rentab.",   "rentab_liquida"),
        ("Valor Líq.","valor_liquido"),
    ]
    _tbl_rf(posicoes, colunas, total_field="valor_liquido")
    st.caption("IR regressivo já descontado no Valor Líquido.")

def tab_cricra(snap_rf):
    dados = snap_rf.get("dados", {}) if snap_rf else {}
    posicoes = dados.get("classes", {}).get("CRI/CRA", {}).get("posicoes", [])
    colunas = [
        ("Título",    "nome"),
        ("Taxa Mercado","taxa_mercado"),
        ("Investido", "investido"),
        ("Valor Atual","atual"),
        ("Rentab.",   "rentab"),
    ]
    _tbl_rf(posicoes, colunas)
    st.caption("CRI/CRA: isentos de IR para pessoa física.")

def tab_fundos(snap_rf):
    dados = snap_rf.get("dados", {}) if snap_rf else {}
    posicoes = dados.get("classes", {}).get("Fundos", {}).get("posicoes", [])
    colunas = [
        ("Fundo",     "nome"),
        ("Investido", "investido"),
        ("Valor Liq.","valor_liquido"),
        ("Rent. Líq.","rentab_liquida"),
    ]
    _tbl_rf(posicoes, colunas, total_field="valor_liquido")

def tab_cdb(snap_rf):
    dados = snap_rf.get("dados", {}) if snap_rf else {}
    cdb  = dados.get("classes", {}).get("CDB", {}).get("posicoes", [])
    lcis = dados.get("classes", {}).get("LCI/LCA", {}).get("posicoes", [])
    posicoes = cdb + lcis
    colunas = [
        ("Título",    "nome"),
        ("Investido", "investido"),
        ("Atual",     "atual"),
        ("Ganho",     "ganho"),
        ("Rentab.",   "rentab"),
    ]
    _tbl_rf(posicoes, colunas)
    st.caption("LCI/LCA: isentos de IR. CDB: valor bruto (IR na resgate).")


# ─── TAB: EVOLUÇÃO ────────────────────────────────────────────────────────────
def tab_evolucao(historico: pd.DataFrame):
    if historico.empty:
        st.info("Histórico disponível após a primeira atualização via executar_atualizacao.command.")
        return

    ultimo = historico.iloc[-1]
    c1, c2, c3 = st.columns(3)
    c1.metric("Último Snapshot", brl(float(ultimo["total_atual"])))
    c2.metric("Ganho Acumulado", brl(float(ultimo["total_ganho"]), sign=True))
    c3.metric("Rentabilidade", pct(float(ultimo["total_rentab"])))

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=historico["data"], y=historico["total_atual"],
        name="Patrimônio Total", mode="lines+markers",
        line=dict(color=VERDE, width=3),
        fill="tozeroy", fillcolor="rgba(26,71,49,0.08)",
    ))
    fig.add_trace(go.Scatter(
        x=historico["data"], y=historico["total_investido"],
        name="Capital Inicial", mode="lines",
        line=dict(color=OURO, width=2, dash="dash"),
    ))
    fig.update_layout(
        height=360, margin=dict(l=0,r=0,t=10,b=0),
        paper_bgcolor="#FFFBEF", plot_bgcolor="#FFFBEF",
        legend=dict(orientation="h", y=1.12),
        yaxis=dict(tickprefix="R$ ", separatethousands=True, gridcolor="#EDE8D5"),
        xaxis=dict(gridcolor="#EDE8D5"),
        hovermode="x unified",
    )
    st.plotly_chart(fig, use_container_width=True)

    # Tabela histórico
    df = historico.copy()
    df["Data"]       = df["data"].dt.strftime("%d/%m/%Y")
    df["Patrimônio"] = df["total_atual"].apply(brl)
    df["Ganho"]      = df["total_ganho"].apply(lambda x: brl(x, sign=True))
    df["Rentab."]    = df["total_rentab"].apply(pct)
    df["RV"]         = df["rv_atual"].apply(brl)
    df["RF"]         = df["rf_atual"].apply(brl)
    st.dataframe(df[["Data","Patrimônio","Ganho","Rentab.","RV","RF"]].iloc[::-1],
                 use_container_width=True, hide_index=True)


# ─── TAB: EMPRÉSTIMOS ─────────────────────────────────────────────────────────
def tab_emprestimos(emp: pd.DataFrame):
    if emp.empty:
        st.info("Nenhum empréstimo ativo cadastrado.")
        return

    total_divida = float(emp["saldo_devedor"].sum())
    total_juros  = float(emp["parcela_juros"].sum())

    c1, c2, c3 = st.columns(3)
    c1.markdown(f"""<div class='kpi-card ouro'>
        <div class='kpi-value'>{brl(total_divida)}</div>
        <div class='kpi-label'>💳 Total de Dívidas</div>
    </div>""", unsafe_allow_html=True)
    c2.markdown(f"""<div class='kpi-card neg'>
        <div class='kpi-value'>{brl(total_juros)}</div>
        <div class='kpi-label'>🔴 Juros Mensais</div>
        <div class='kpi-sub'>Custo mensal total em juros</div>
    </div>""", unsafe_allow_html=True)
    n_contratos = len(emp)
    c3.markdown(f"""<div class='kpi-card'>
        <div class='kpi-value'>{n_contratos}</div>
        <div class='kpi-label'>📋 Contratos Ativos</div>
    </div>""", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # Pizza por credor
    grp = emp.groupby("credor")["saldo_devedor"].sum().reset_index()
    col_g, col_t = st.columns([1, 1.8])
    with col_g:
        fig = go.Figure(go.Pie(
            labels=grp["credor"], values=grp["saldo_devedor"],
            hole=0.5, marker_colors=[VERDE, "#3A7D5A", OURO, "#D4A017"],
            textinfo="label+percent", textfont_size=12,
        ))
        fig.update_layout(height=260, margin=dict(l=0,r=0,t=0,b=0),
                          showlegend=False, paper_bgcolor="#FFFBEF")
        st.plotly_chart(fig, use_container_width=True)

    with col_t:
        df_show = emp[["credor","titulo","saldo_devedor","taxa_juros","parcela_juros"]].copy()
        df_show.columns = ["Credor","Título","Saldo Devedor","Taxa a.m.","Juros/Mês"]
        df_show["Saldo Devedor"] = df_show["Saldo Devedor"].apply(brl)
        df_show["Taxa a.m."]     = df_show["Taxa a.m."].apply(lambda x: f"{float(x)*100:.2f}%")
        df_show["Juros/Mês"]     = df_show["Juros/Mês"].apply(brl)
        st.dataframe(df_show, use_container_width=True, hide_index=True)

    # Totalizador por credor
    st.markdown("**Resumo por credor:**")
    resumo = emp.groupby("credor").agg(
        Contratos=("titulo","count"),
        Saldo_Total=("saldo_devedor","sum"),
        Juros_Mes=("parcela_juros","sum"),
    ).reset_index()
    resumo.columns = ["Credor","Contratos","Saldo Total","Juros/Mês"]
    resumo["Saldo Total"] = resumo["Saldo Total"].apply(brl)
    resumo["Juros/Mês"]  = resumo["Juros/Mês"].apply(brl)
    st.dataframe(resumo, use_container_width=True, hide_index=True)


# ─── TAB: INVESTIMENTOS ESCRITÓRIO ────────────────────────────────────────────
def tab_escritorio(inv: pd.DataFrame):
    if inv.empty:
        st.info("Nenhum dado de investimento cadastrado.")
        return

    ultimo = inv.iloc[-1]
    saldo  = float(ultimo["saldo_final"])
    rend   = float(ultimo["rendimento"])

    c1, c2, c3 = st.columns(3)
    c1.markdown(f"""<div class='kpi-card'>
        <div class='kpi-value'>{brl(saldo)}</div>
        <div class='kpi-label'>📈 Saldo Atual</div>
    </div>""", unsafe_allow_html=True)
    c2.markdown(f"""<div class='kpi-card ouro'>
        <div class='kpi-value'>{brl(rend)}</div>
        <div class='kpi-label'>💰 Rendimento Último Mês</div>
    </div>""", unsafe_allow_html=True)
    total_aporte = float(inv[inv["tipo"] != "Saldo Inicial"]["valor"].sum())
    c3.markdown(f"""<div class='kpi-card'>
        <div class='kpi-value'>{brl(total_aporte)}</div>
        <div class='kpi-label'>📥 Total de Aportes</div>
    </div>""", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    fig = go.Figure()
    inv_plot = inv[inv["saldo_final"] > 0].copy()
    fig.add_trace(go.Bar(
        x=inv_plot["mes"].dt.strftime("%b/%Y"), y=inv_plot["valor"],
        name="Aporte", marker_color=OURO, opacity=0.7,
    ))
    fig.add_trace(go.Scatter(
        x=inv_plot["mes"].dt.strftime("%b/%Y"), y=inv_plot["saldo_final"],
        name="Saldo", line=dict(color=VERDE, width=3), mode="lines+markers",
        marker=dict(size=8),
    ))
    fig.update_layout(
        height=300, margin=dict(l=0,r=0,t=10,b=0),
        legend=dict(orientation="h", y=1.12),
        paper_bgcolor="#FFFBEF", plot_bgcolor="#FFFBEF",
        yaxis=dict(tickprefix="R$ ", gridcolor="#EDE8D5"),
        hovermode="x unified",
    )
    st.plotly_chart(fig, use_container_width=True)

    df_show = inv_plot[["mes","tipo","valor","rendimento","saldo_final"]].copy()
    df_show.columns = ["Mês","Tipo","Aporte","Rendimento","Saldo Final"]
    df_show["Mês"]       = df_show["Mês"].dt.strftime("%b/%Y")
    df_show["Aporte"]    = df_show["Aporte"].apply(brl)
    df_show["Rendimento"]= df_show["Rendimento"].apply(brl)
    df_show["Saldo Final"]= df_show["Saldo Final"].apply(brl)
    st.dataframe(df_show, use_container_width=True, hide_index=True)


# ─── MAIN ─────────────────────────────────────────────────────────────────────
if "user" not in st.session_state:
    pagina_login()
else:
    render_header()

    # Carga de dados
    with st.spinner("Carregando dados..."):
        snap_rv     = load_snapshot("RV")
        snap_rf     = load_snapshot("RF")
        posicoes_rv = load_posicoes_rv()
        historico   = load_historico()
        emprestimos = load_emprestimos()
        investimentos = load_investimentos()

    # Tabs principais
    tabs = st.tabs([
        "📊 Resumo",
        "📈 Ações BR", "🇧🇷 ETF BR", "🏢 FIIs",
        "🌍 Internacional",
        "🏛️ Tesouro", "📋 CRI/CRA", "💼 Fundos", "🏦 CDB/LCI/LCA",
        "📉 Evolução",
        "💳 Empréstimos", "🏢 Escritório",
    ])

    with tabs[0]:  tab_resumo(snap_rv, snap_rf, posicoes_rv)
    with tabs[1]:  tab_rv_br("Ações BR",  snap_rv, posicoes_rv)
    with tabs[2]:  tab_rv_br("ETF BR",    snap_rv, posicoes_rv)
    with tabs[3]:  tab_rv_br("FII",       snap_rv, posicoes_rv)
    with tabs[4]:  tab_internacional(snap_rv, posicoes_rv)
    with tabs[5]:  tab_tesouro(snap_rf)
    with tabs[6]:  tab_cricra(snap_rf)
    with tabs[7]:  tab_fundos(snap_rf)
    with tabs[8]:  tab_cdb(snap_rf)
    with tabs[9]:  tab_evolucao(historico)
    with tabs[10]: tab_emprestimos(emprestimos)
    with tabs[11]: tab_escritorio(investimentos)

    # Logout
    st.markdown("<br>", unsafe_allow_html=True)
    cols = st.columns([5, 1])
    with cols[1]:
        if st.button("🚪 Sair", use_container_width=True):
            sb.auth.sign_out()
            st.session_state.clear()
            st.rerun()

    st.markdown(
        f"<p style='text-align:center;color:#bbb;font-size:.72rem'>"
        f"3P Finanças · Planejar · Poupar · Prosperar · {datetime.now().strftime('%d/%m/%Y %H:%M')}</p>",
        unsafe_allow_html=True,
    )
