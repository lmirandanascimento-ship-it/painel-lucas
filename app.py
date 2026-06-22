import streamlit as st
from supabase import create_client
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime

# ────────────────────────────────────────────────────────────────────────────
# CONFIG
# ────────────────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="3P Finanças | Painel Lucas",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="collapsed",
)

VERDE   = "#1F5C38"
VERDE_M = "#277A4A"
OURO    = "#B8960C"

st.markdown(f"""
<style>
    /* Fundo geral */
    .stApp {{ background-color: #F5F5F5; }}
    /* Header */
    .header-3p {{
        background: {VERDE};
        padding: 14px 24px;
        border-radius: 10px;
        margin-bottom: 20px;
        display: flex;
        align-items: center;
        justify-content: space-between;
    }}
    /* Cartões de KPI */
    .kpi-card {{
        background: white;
        border: 1px solid #E0E0E0;
        border-left: 5px solid {VERDE};
        border-radius: 8px;
        padding: 18px 20px;
    }}
    .kpi-card.ouro {{ border-left-color: {OURO}; }}
    .kpi-value {{ font-size: 1.7rem; font-weight: 700; color: #1A1A1A; }}
    .kpi-label {{ font-size: 0.82rem; color: #777; margin-top: 4px; }}
    /* Alertas */
    .alerta-ouro {{
        background: #FFFBEB;
        border-left: 4px solid {OURO};
        padding: 12px 16px;
        border-radius: 6px;
        margin-top: 12px;
    }}
    /* Login */
    .login-container {{
        max-width: 400px;
        margin: 60px auto;
        background: white;
        padding: 40px;
        border-radius: 12px;
        box-shadow: 0 2px 12px rgba(0,0,0,0.10);
    }}
    /* Esconde menu e footer do Streamlit */
    #MainMenu {{visibility: hidden;}}
    footer {{visibility: hidden;}}
</style>
""", unsafe_allow_html=True)


# ────────────────────────────────────────────────────────────────────────────
# SUPABASE
# ────────────────────────────────────────────────────────────────────────────
@st.cache_resource
def get_supabase():
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)

sb = get_supabase()


# ────────────────────────────────────────────────────────────────────────────
# UTILIDADES
# ────────────────────────────────────────────────────────────────────────────
def brl(valor):
    """Formata número como R$ 1.234,56"""
    if valor is None:
        return "—"
    return f"R$ {float(valor):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


# ────────────────────────────────────────────────────────────────────────────
# AUTENTICAÇÃO
# ────────────────────────────────────────────────────────────────────────────
def pagina_login():
    _, col, _ = st.columns([1, 1.2, 1])
    with col:
        st.markdown(f"""
        <div style='text-align:center; padding: 30px 0 10px'>
            <h1 style='color:{VERDE}; font-size:2rem; margin-bottom:4px'>3P FINANÇAS</h1>
            <p style='color:{OURO}; font-style:italic; font-size:0.95rem; margin:0'>
                Planejar · Poupar · Prosperar
            </p>
        </div>
        """, unsafe_allow_html=True)

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
                st.session_state["user"]    = r.user
                st.session_state["session"] = r.session
                st.rerun()
            except Exception:
                st.error("E-mail ou senha incorretos. Tente novamente.")


# ────────────────────────────────────────────────────────────────────────────
# DADOS
# ────────────────────────────────────────────────────────────────────────────
@st.cache_data(ttl=300, show_spinner=False)
def load_investimentos():
    r = sb.table("investimentos_escritorio").select("*").order("mes").execute()
    df = pd.DataFrame(r.data)
    if not df.empty:
        df["mes"] = pd.to_datetime(df["mes"])
    return df


@st.cache_data(ttl=300, show_spinner=False)
def load_emprestimos():
    r = sb.table("emprestimos").select("*").eq("status", "ativo").order("credor").execute()
    return pd.DataFrame(r.data)


# ────────────────────────────────────────────────────────────────────────────
# DASHBOARD
# ────────────────────────────────────────────────────────────────────────────
def pagina_dashboard():
    user = st.session_state.get("user")
    nome_exibicao = (user.email or "Lucas").split("@")[0].capitalize()

    # ── Header ──────────────────────────────────────────────────────────────
    st.markdown(f"""
    <div class='header-3p'>
        <div>
            <span style='color:{OURO}; font-size:1.2rem; font-weight:700'>3P FINANÇAS</span>
            <span style='color:#ccc; font-size:0.85rem; margin-left:14px'>Planejar · Poupar · Prosperar</span>
        </div>
        <div style='color:#ddd; font-size:0.85rem'>
            📅 {datetime.now().strftime("%d/%m/%Y")} &nbsp;|&nbsp; 👤 {nome_exibicao}
        </div>
    </div>
    """, unsafe_allow_html=True)

    # ── Carga de dados ───────────────────────────────────────────────────────
    with st.spinner("Carregando dados..."):
        inv = load_investimentos()
        emp = load_emprestimos()

    # ── KPIs ────────────────────────────────────────────────────────────────
    saldo_inv      = float(inv["saldo_final"].iloc[-1]) if not inv.empty else 0
    total_divida   = float(emp["saldo_devedor"].sum()) if not emp.empty else 0
    total_juros    = float(emp["parcela_juros"].sum()) if not emp.empty else 0
    rend_mensal    = float(inv["rendimento"].iloc[-1]) if not inv.empty else 0
    saldo_liquido  = saldo_inv - total_divida

    c1, c2, c3, c4 = st.columns(4)

    with c1:
        st.markdown(f"""
        <div class='kpi-card'>
            <div class='kpi-value'>{brl(saldo_inv)}</div>
            <div class='kpi-label'>📈 Investimentos do Escritório</div>
            <div style='font-size:0.78rem; color:{VERDE}; margin-top:6px'>
                +{brl(rend_mensal)} de rendimento esse mês
            </div>
        </div>""", unsafe_allow_html=True)

    with c2:
        st.markdown(f"""
        <div class='kpi-card ouro'>
            <div class='kpi-value'>{brl(total_divida)}</div>
            <div class='kpi-label'>💳 Total de Dívidas (Empréstimos)</div>
            <div style='font-size:0.78rem; color:{OURO}; margin-top:6px'>
                {brl(total_juros)}/mês apenas em juros
            </div>
        </div>""", unsafe_allow_html=True)

    with c3:
        cor = VERDE if saldo_liquido >= 0 else "#C0392B"
        sinal = "+" if saldo_liquido >= 0 else ""
        st.markdown(f"""
        <div class='kpi-card' style='border-left-color:{cor}'>
            <div class='kpi-value' style='color:{cor}'>{sinal}{brl(saldo_liquido)}</div>
            <div class='kpi-label'>⚖️ Saldo Líquido (Inv. − Dívidas)</div>
        </div>""", unsafe_allow_html=True)

    with c4:
        cobertura = (rend_mensal / total_juros * 100) if total_juros > 0 else 0
        cor_cob = VERDE if cobertura >= 100 else OURO
        st.markdown(f"""
        <div class='kpi-card' style='border-left-color:{cor_cob}'>
            <div class='kpi-value' style='color:{cor_cob}'>{cobertura:.0f}%</div>
            <div class='kpi-label'>🔄 Cobertura: rendimento vs. juros</div>
            <div style='font-size:0.78rem; color:#777; margin-top:6px'>
                Ideal: rendimento ≥ juros mensais
            </div>
        </div>""", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Investimentos do Escritório ──────────────────────────────────────────
    st.markdown(f"#### 📈 Investimentos do Escritório — Evolução")

    if not inv.empty:
        inv_plot = inv[inv["saldo_final"] > 0].copy()

        fig = go.Figure()
        # Barras de aporte
        fig.add_trace(go.Bar(
            x=inv_plot["mes"].dt.strftime("%b/%Y"),
            y=inv_plot["valor"],
            name="Aporte",
            marker_color=OURO,
            opacity=0.75,
            yaxis="y",
        ))
        # Linha de saldo
        fig.add_trace(go.Scatter(
            x=inv_plot["mes"].dt.strftime("%b/%Y"),
            y=inv_plot["saldo_final"],
            name="Saldo Final",
            line=dict(color=VERDE, width=3),
            mode="lines+markers",
            marker=dict(size=8, color=VERDE),
            yaxis="y",
        ))
        # Linha de rendimento
        fig.add_trace(go.Scatter(
            x=inv_plot["mes"].dt.strftime("%b/%Y"),
            y=inv_plot["rendimento"],
            name="Rendimento",
            line=dict(color=VERDE_M, width=2, dash="dot"),
            mode="lines+markers",
            marker=dict(size=6, color=VERDE_M),
            yaxis="y",
        ))
        fig.update_layout(
            height=320,
            margin=dict(l=0, r=0, t=10, b=0),
            legend=dict(orientation="h", y=1.12, x=0),
            paper_bgcolor="white",
            plot_bgcolor="white",
            yaxis=dict(
                tickprefix="R$ ",
                separatethousands=True,
                gridcolor="#F0F0F0",
            ),
            hovermode="x unified",
        )
        st.plotly_chart(fig, use_container_width=True)

        # Tabela
        t = inv_plot[["mes", "tipo", "valor", "rendimento", "saldo_final"]].copy()
        t.columns = ["Mês", "Tipo Mov.", "Aporte (R$)", "Rendimento (R$)", "Saldo Final (R$)"]
        t["Mês"] = t["Mês"].dt.strftime("%b/%Y")
        for col in ["Aporte (R$)", "Rendimento (R$)", "Saldo Final (R$)"]:
            t[col] = t[col].apply(brl)
        st.dataframe(t, use_container_width=True, hide_index=True)
    else:
        st.info("Nenhum dado de investimento cadastrado ainda.")

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Empréstimos ──────────────────────────────────────────────────────────
    st.markdown(f"#### 💳 Empréstimos — Posição Atual")

    if not emp.empty:
        col_graf, col_tab = st.columns([1, 1.6])

        with col_graf:
            grp = emp.groupby("credor")["saldo_devedor"].sum().reset_index()
            cores_pizza = [VERDE, "#3A7D5A", OURO, "#D4A017", "#5C9E77"]
            fig2 = go.Figure(go.Pie(
                labels=grp["credor"],
                values=grp["saldo_devedor"],
                hole=0.48,
                marker_colors=cores_pizza[:len(grp)],
                textinfo="label+percent",
                textfont_size=12,
            ))
            fig2.update_layout(
                height=280,
                margin=dict(l=0, r=0, t=10, b=0),
                showlegend=False,
                paper_bgcolor="white",
            )
            st.plotly_chart(fig2, use_container_width=True)

        with col_tab:
            e = emp[["credor", "titulo", "saldo_devedor", "taxa_juros", "parcela_juros"]].copy()
            e.columns = ["Credor", "Título", "Saldo Devedor", "Taxa a.m.", "Juros/Mês"]
            e["Saldo Devedor"] = e["Saldo Devedor"].apply(brl)
            e["Taxa a.m."]     = e["Taxa a.m."].apply(lambda x: f"{float(x)*100:.2f}%")
            e["Juros/Mês"]     = e["Juros/Mês"].apply(brl)
            st.dataframe(e, use_container_width=True, hide_index=True)

            st.markdown(f"""
            <div class='alerta-ouro'>
            <b>⚠️ Custo mensal em juros: {brl(total_juros)}</b><br>
            <small>Rendimento atual dos investimentos: <b>{brl(rend_mensal)}/mês</b>
            — cobertura de {cobertura:.0f}% dos juros</small>
            </div>
            """, unsafe_allow_html=True)

        # Totalizador por credor
        st.markdown("<br>", unsafe_allow_html=True)
        resumo = emp.groupby("credor").agg(
            Contratos=("titulo", "count"),
            Saldo_Total=("saldo_devedor", "sum"),
            Juros_Total=("parcela_juros", "sum"),
        ).reset_index()
        resumo.columns = ["Credor", "Contratos", "Saldo Total", "Juros/Mês"]
        resumo["Saldo Total"] = resumo["Saldo Total"].apply(brl)
        resumo["Juros/Mês"]  = resumo["Juros/Mês"].apply(brl)
        st.dataframe(resumo, use_container_width=True, hide_index=True)
    else:
        st.info("Nenhum empréstimo cadastrado ainda.")

    # ── Rodapé ──────────────────────────────────────────────────────────────
    st.markdown("<br><br>", unsafe_allow_html=True)
    cols = st.columns([4, 1])
    with cols[1]:
        if st.button("🚪 Sair", use_container_width=True):
            sb.auth.sign_out()
            st.session_state.clear()
            st.rerun()

    st.markdown(
        f"<p style='text-align:center; color:#aaa; font-size:0.75rem'>"
        f"3P Finanças · Planejar · Poupar · Prosperar · atualizado em {datetime.now().strftime('%d/%m/%Y %H:%M')}</p>",
        unsafe_allow_html=True
    )


# ────────────────────────────────────────────────────────────────────────────
# MAIN
# ────────────────────────────────────────────────────────────────────────────
if "user" not in st.session_state:
    pagina_login()
else:
    pagina_dashboard()
