import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import date

# =========================
# CONFIG
# =========================
st.set_page_config(
    page_title="ESF — Produção, Resolutividade e KPIs",
    page_icon="🏥",
    layout="wide"
)

# =========================
# AJUDA / ESQUEMA DE DADOS
# =========================
ESQUEMA = {
    "atendimentos.csv": [
        "data_atendimento",     # YYYY-MM-DD
        "medico_id",
        "unidade",
        "tipo_atendimento",     # consulta, visita, procedimento...
        "encaminhamento",       # 0 = não, 1 = sim
        "paciente_id",
        "cid_principal"         # opcional
    ],
    "icsap.csv": [
        "data_internacao",
        "paciente_id",
        "unidade",
        "condicao_icsap"        # bool/int (1=ICSAP)
    ],
    "medicos.csv": [
        "medico_id",
        "medico_nome",
        "carga_horaria_semana", # horas
        "unidade"
    ]
}

# =========================
# LOADERS (com cache)
# =========================
@st.cache_data(show_spinner=False)
def load_csv(path: str, parse_dates=None, dtype=None) -> pd.DataFrame:
    try:
        return pd.read_csv(path, parse_dates=parse_dates, dtype=dtype)
    except Exception as e:
        st.warning(f"Não foi possível ler {path}. Detalhe: {e}")
        return pd.DataFrame()

@st.cache_data(show_spinner=False)
def load_data():
    df_at = load_csv("data/atendimentos.csv", parse_dates=["data_atendimento"])
    df_icsap = load_csv("data/icsap.csv", parse_dates=["data_internacao"])
    df_med = load_csv("data/medicos.csv")

    # Normalizações úteis
    if "data_atendimento" in df_at:
        df_at["data_atendimento"] = pd.to_datetime(df_at["data_atendimento"]).dt.date
    if "data_internacao" in df_icsap:
        df_icsap["data_internacao"] = pd.to_datetime(df_icsap["data_internacao"]).dt.date

    return df_at, df_icsap, df_med

df_at, df_icsap, df_med = load_data()

# =========================
# SIDEBAR — FILTROS
# =========================
with st.sidebar:
    st.header("🔎 Filtros")
    st.caption("**Estratégia Saúde da Família — SUS**")

    # Período
    if not df_at.empty:
        min_d = min(df_at["data_atendimento"])
        max_d = max(df_at["data_atendimento"])
    else:
        min_d, max_d = date(2025, 1, 1), date.today()

    dt_ini, dt_fim = st.date_input(
        "Período",
        value=(min_d, max_d),
        min_value=min_d,
        max_value=max_d
    )

    # Unidade
    unidades = sorted(df_at["unidade"].dropna().unique().tolist()) if not df_at.empty else []
    unidade_sel = st.multiselect("Unidade(s)", unidades, default=unidades[:1] if unidades else [])

    # Médico
    if not df_med.empty:
        # junta nome com id para facilitar filtro
        df_med["_label"] = df_med["medico_nome"].astype(str) + " — " + df_med["medico_id"].astype(str)
        medicos_opts = df_med.set_index("medico_id")["_label"].to_dict()
        medicos_ids = list(medicos_opts.keys())
    else:
        medicos_opts, medicos_ids = {}, []

    medicos_sel = st.multiselect(
        "Médico(s)",
        options=medicos_ids,
        format_func=lambda k: medicos_opts.get(k, str(k))
    )

    st.divider()
    st.markdown("**Esquema esperado (colunas)**")
    with st.expander("Ver colunas por arquivo"):
        for arq, cols in ESQUEMA.items():
            st.code(f"{arq}: {', '.join(cols)}", language="text")

# =========================
# APLICA FILTROS
# =========================
if not df_at.empty:
    mask = (df_at["data_atendimento"] >= dt_ini) & (df_at["data_atendimento"] <= dt_fim)
    if unidade_sel:
        mask &= df_at["unidade"].isin(unidade_sel)
    if medicos_sel:
        mask &= df_at["medico_id"].isin(medicos_sel)
    dff = df_at.loc[mask].copy()
else:
    dff = pd.DataFrame()

# =========================
# TÍTULO
# =========================
st.title("🏥 ESF — Produção, Resolutividade e KPIs")

# =========================
# KPIs DE TOPO
# =========================
def kpi_cards(data: pd.DataFrame):
    c1, c2, c3, c4 = st.columns(4)

    total_at = len(data)
    consultas = data.query("tipo_atendimento == 'consulta'").shape[0] if not data.empty else 0
    resolutividade = 0.0
    if not data.empty and "encaminhamento" in data:
        base_consultas = data.query("tipo_atendimento == 'consulta'")
        if len(base_consultas) > 0:
            resolutividade = (base_consultas["encaminhamento"].eq(0).mean()) * 100

    # produtividade média (consultas/dia por médico) — simples
    prod = 0.0
    if not data.empty:
        if "medico_id" in data and "data_atendimento" in data:
            tmp = (
                data.query("tipo_atendimento == 'consulta'")
                .groupby(["medico_id", "data_atendimento"])
                .size()
                .groupby("medico_id")
                .mean()
            )
            if len(tmp) > 0:
                prod = tmp.mean()

    c1.metric("Atendimentos (total)", f"{total_at:,}".replace(",", "."))
    c2.metric("Consultas", f"{consultas:,}".replace(",", "."))
    c3.metric("Resolutividade APS (%)", f"{resolutividade:,.1f}".replace(",", "."))
    c4.metric("Produtividade (consultas/dia por médico)", f"{prod:,.2f}".replace(",", "."))

kpi_cards(dff)

# =========================
# ABA: VISÃO GERAL
# =========================
aba1, aba2, aba3 = st.tabs(["📊 Visão Geral", "👨‍⚕️ Médicos", "🏥 ICSAP"])

with aba1:
    st.subheader("Evolução mensal de atendimentos")
    if not dff.empty:
        dff["mes"] = pd.to_datetime(dff["data_atendimento"]).map(lambda d: f"{d.year}-{d.month:02d}")
        serie = dff.groupby("mes").size().reset_index(name="atendimentos")
        fig = px.line(serie, x="mes", y="atendimentos", markers=True)
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Sem dados para o período/seleção.")

    colA, colB = st.columns(2)
    with colA:
        st.markdown("**Atendimentos por tipo**")
        if not dff.empty:
            g = dff.groupby("tipo_atendimento").size().reset_index(name="qtd").sort_values("qtd", ascending=False)
            fig = px.bar(g, x="tipo_atendimento", y="qtd", text="qtd")
            fig.update_traces(textposition="outside")
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.empty()

    with colB:
        st.markdown("**Encaminhamentos por 100 consultas**")
        if not dff.empty:
            base_c = dff.query("tipo_atendimento == 'consulta'")
            tmp = (
                base_c.groupby("unidade")["encaminhamento"]
                .apply(lambda s: s.mean() * 100)
                .reset_index(name="encaminhamentos_%")
                .sort_values("encaminhamentos_%", ascending=False)
            )
            fig = px.bar(tmp, x="unidade", y="encaminhamentos_%", text="encaminhamentos_%")
            fig.update_traces(texttemplate="%{text:.1f}", textposition="outside")
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.empty()

# =========================
# ABA: MÉDICOS (ranking/comparativo)
# =========================
with aba2:
    st.subheader("Comparativo por médico")
    if not dff.empty and "medico_id" in dff:
        # junta nome
        dff = dff.merge(df_med[["medico_id", "medico_nome"]], on="medico_id", how="left")

        # Produção total
        prod = dff.groupby("medico_nome").size().reset_index(name="atendimentos")
        fig1 = px.bar(prod.sort_values("atendimentos", ascending=False),
                      x="medico_nome", y="atendimentos", text="atendimentos")
        fig1.update_layout(xaxis_title="", yaxis_title="Atendimentos")
        st.plotly_chart(fig1, use_container_width=True)

        # Resolutividade (consultas sem encaminhamento)
        base_c = dff.query("tipo_atendimento == 'consulta'")
        if not base_c.empty:
            res = (
                base_c.groupby("medico_nome")["encaminhamento"]
                .apply(lambda s: (s.eq(0).mean()) * 100)
                .reset_index(name="resolutividade_%")
            )
            fig2 = px.bar(res.sort_values("resolutividade_%", ascending=False),
                          x="medico_nome", y="resolutividade_%", text="resolutividade_%")
            fig2.update_traces(texttemplate="%{text:.1f}")
            fig2.update_layout(xaxis_title="", yaxis_title="Resolutividade (%)")
            st.plotly_chart(fig2, use_container_width=True)
        else:
            st.info("Não há consultas para calcular resolutividade no recorte atual.")
    else:
        st.info("Sem dados para exibir por médico.")

# =========================
# ABA: ICSAP (opcional)
# =========================
with aba3:
    st.subheader("Internações por Condições Sensíveis à APS (ICSAP)")
    if df_icsap.empty:
        st.info("Não há dados de ICSAP carregados.")
    else:
        # Filtro por período/unidade igual ao de atendimentos (quando fizer sentido)
        mask_icsap = (df_icsap["data_internacao"] >= dt_ini) & (df_icsap["data_internacao"] <= dt_fim)
        if unidade_sel:
            mask_icsap &= df_icsap["unidade"].isin(unidade_sel)
        icsap_f = df_icsap.loc[mask_icsap].copy()

        col1, col2 = st.columns(2)
        with col1:
            por_unidade = icsap_f.groupby("unidade").size().reset_index(name="icsap")
            fig = px.bar(por_unidade.sort_values("icsap", ascending=False), x="unidade", y="icsap", text="icsap")
            fig.update_layout(xaxis_title="", yaxis_title="ICSAP (contagem)")
            st.plotly_chart(fig, use_container_width=True)

        with col2:
            por_mes = (
                icsap_f.assign(mes=lambda d: pd.to_datetime(d["data_internacao"]).map(lambda x: f"{x.year}-{x.month:02d}"))
                .groupby("mes")
                .size()
                .reset_index(name="icsap")
            )
            fig = px.line(por_mes, x="mes", y="icsap", markers=True)
            st.plotly_chart(fig, use_container_width=True)

# =========================
# RODAPÉ
# =========================
st.caption("Dica: use a aba *Médicos* para identificar oportunidades de educação permanente, revisar encaminhamentos e fortalecer a resolutividade na APS.")
