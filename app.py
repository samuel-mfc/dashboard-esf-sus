# app_regulacao.py — Protótipo de Dashboard para Regulação Assistencial (e-SUS Regulação / MIRA)
# Autor: ChatGPT (GPT-5 Thinking)
# -----------------------------------------------------------------------------
# Como usar:
# 1) pip install streamlit pandas numpy plotly
# 2) streamlit run app_regulacao.py
# 3) Publicar no Streamlit Cloud apontando para este arquivo
#
# Sobre os dados:
# • Este protótipo aceita um CSV/Parquet baseado no Modelo de Informação da Regulação Assistencial (MIRA).
# • Mínimo esperado de colunas (nomes sugeridos — mapeáveis na barra lateral):
#   - id_solicitacao, data_solicitacao, unidade_origem, equipe_origem, cns_paciente (opcional),
#   - especialidade, procedimento, prioridade (ex.: P1/P2/P3/P4),
#   - situacao (Aguardando|Agendado|Realizado|Cancelado|Devolvido), motivo_cancelamento (opcional),
#   - data_agendamento (se houver), data_realizacao (se houver),
#   - central_regulacao, servico_destino (prestador), municipio_destino,
#   - canal (APS|Urgência|Outros), justificativa/observacao (opcionais)
# • O protótipo também gera dados simulados para demonstração caso você não envie arquivo.

from __future__ import annotations
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from datetime import datetime

st.set_page_config(page_title="Regulação Assistencial — MIRA", page_icon="📊", layout="wide")

PRIMARY = "#0ea5e9"; ACCENT = "#10b981"; DANGER = "#ef4444"; MUTED = "#64748b"

# ---------------------------------
# Utilidades
# ---------------------------------
@st.cache_data(show_spinner=False)
def gerar_dados_fake(n=5000, seed=2025):
    rng = np.random.default_rng(seed)
    hoje = pd.Timestamp.today().normalize()
    datas_sol = pd.date_range(hoje - pd.DateOffset(months=6), hoje, freq="D")

    especialidades = [
        "Cardiologia", "Oftalmologia", "Ortopedia", "Dermatologia", "Ginecologia",
        "Endocrinologia", "Neurologia", "Urologia"
    ]
    prioridades = ["P1", "P2", "P3", "P4"]
    situacoes = ["Aguardando", "Agendado", "Realizado", "Cancelado", "Devolvido"]
    unidades = [f"UBS {c}" for c in list("ABCDE")] + ["UPA Central"]
    prestadores = ["HSP Municipal", "Clínica Vida", "IASC", "CMES Especialidades", "HE Estadual"]

    linhas = []
    for i in range(1, n+1):
        dsol = rng.choice(datas_sol)
        esp = rng.choice(especialidades, p=np.array([18,14,16,10,14,10,10,8])/100)
        pr = rng.choice(prioridades, p=[0.15, 0.35, 0.35, 0.15])
        un = rng.choice(unidades)
        sit = rng.choice(situacoes, p=[0.45, 0.18, 0.27, 0.07, 0.03])
        prest = rng.choice(prestadores)

        # tempos
        espera_ag = max(0, int(rng.normal({"P1":5, "P2":20, "P3":45, "P4":70}[pr], 8)))
        espera_real = espera_ag + max(0, int(rng.normal(7, 4)))

        dag = pd.NaT; dreal = pd.NaT
        if sit in ("Agendado", "Realizado", "Cancelado", "Devolvido"):
            dag = (pd.Timestamp(dsol) + pd.Timedelta(days=espera_ag))
        if sit == "Realizado":
            dreal = (pd.Timestamp(dsol) + pd.Timedelta(days=espera_real))

        linhas.append({
            "id_solicitacao": i,
            "data_solicitacao": pd.Timestamp(dsol),
            "unidade_origem": un,
            "equipe_origem": f"ESF {rng.integers(1,11):02d}",
            "especialidade": esp,
            "procedimento": f"PROC-{rng.integers(100,999)}",
            "prioridade": pr,
            "situacao": sit,
            "data_agendamento": dag,
            "data_realizacao": dreal,
            "central_regulacao": rng.choice(["Municipal","Estadual"]),
            "servico_destino": prest,
            "municipio_destino": rng.choice(["Município A","Município B","Município C"]),
            "canal": rng.choice(["APS","Urgência","Outros"], p=[0.7,0.2,0.1]),
        })

    df = pd.DataFrame(linhas)
    df["dia"] = df["data_solicitacao"].dt.date
    df["mes"] = df["data_solicitacao"].dt.to_period("M").dt.to_timestamp()
    # métricas de espera
    df["dias_ate_agendar"] = (df["data_agendamento"] - df["data_solicitacao"]).dt.days
    df["dias_ate_realizar"] = (df["data_realizacao"] - df["data_solicitacao"]).dt.days
    return df


def kpi(col, label, value, help_txt=None):
    col.markdown(f"""
        <div style='border:1px solid #e5e7eb;border-radius:16px;padding:16px;'>
          <div style='font-size:12px;color:{MUTED}'>{label}</div>
          <div style='font-size:28px;font-weight:700;'>{value}</div>
          {f"<div style='font-size:12px;color:{MUTED};margin-top:6px;'>{help_txt}</div>" if help_txt else ''}
        </div>
    """, unsafe_allow_html=True)


# ---------------------------------
# Carregar dados (widgets + função cacheada)
# ---------------------------------

# Função cacheada: apenas lê/processa os dados
@st.cache_data(show_spinner=False)
def carregar_dados(file) -> pd.DataFrame:
    """Lê o arquivo enviado (CSV/Parquet) e prepara colunas auxiliares.
    Se 'file' for None, gera dados simulados.
    """
    if file is None:
        return gerar_dados_fake()

    # leitura
    if file.name.lower().endswith(".csv"):
        df = pd.read_csv(file)
    else:
        df = pd.read_parquet(file)

    # parse de datas
    for c in ["data_solicitacao", "data_agendamento", "data_realizacao"]:
        if c in df.columns:
            df[c] = pd.to_datetime(df[c], errors="coerce").dt.tz_localize(None)

    # colunas auxiliares
    if "data_solicitacao" in df.columns:
        df["dia"] = df["data_solicitacao"].dt.date
        df["mes"] = df["data_solicitacao"].dt.to_period("M").dt.to_timestamp()

    if {"data_agendamento", "data_solicitacao"}.issubset(df.columns):
        df["dias_ate_agendar"] = (df["data_agendamento"] - df["data_solicitacao"]).dt.days

    if {"data_realizacao", "data_solicitacao"}.issubset(df.columns):
        df["dias_ate_realizar"] = (df["data_realizacao"] - df["data_solicitacao"]).dt.days

    return df


# --- Widget fora da função cacheada ---
st.sidebar.subheader("📥 Dados")
up = st.sidebar.file_uploader(
    "CSV/Parquet conforme MIRA (veja colunas mínimas acima)",
    type=["csv", "parquet"]
)

# --- Agora sim: carregar os dados com cache ---
base = carregar_dados(up)

def filtros(df: pd.DataFrame):
    st.sidebar.header("⚙️ Filtros")
    min_d, max_d = df["data_solicitacao"].min().date(), df["data_solicitacao"].max().date()
    dt_ini, dt_fim = st.sidebar.date_input("Período da solicitação", value=(min_d, max_d), min_value=min_d, max_value=max_d)

    sel_sit = st.sidebar.multiselect("Situação", ["Aguardando","Agendado","Realizado","Cancelado","Devolvido"], default=["Aguardando","Agendado","Realizado"])
    sel_pri = st.sidebar.multiselect("Prioridade", sorted(df["prioridade"].dropna().unique()), default=list(sorted(df["prioridade"].dropna().unique())))
    sel_esp = st.sidebar.multiselect("Especialidade", sorted(df["especialidade"].dropna().unique()))
    sel_un = st.sidebar.multiselect("Unidade origem", sorted(df["unidade_origem"].dropna().unique()))
    sel_prest = st.sidebar.multiselect("Serviço/Prestador", sorted(df["servico_destino"].dropna().unique()))

    mask = (df["dia"] >= dt_ini) & (df["dia"] <= dt_fim)
    if sel_sit: mask &= df["situacao"].isin(sel_sit)
    if sel_pri: mask &= df["prioridade"].isin(sel_pri)
    if sel_esp: mask &= df["especialidade"].isin(sel_esp)
    if sel_un: mask &= df["unidade_origem"].isin(sel_un)
    if sel_prest: mask &= df["servico_destino"].isin(sel_prest)

    return df.loc[mask].copy()


# ---------------------------------
# Indicadores
# ---------------------------------

def indicadores(df: pd.DataFrame) -> dict:
    fila_atual = int((df["situacao"] == "Aguardando").sum())
    agendadas = int((df["situacao"] == "Agendado").sum())
    realizadas = int((df["situacao"] == "Realizado").sum())
    canceladas = int((df["situacao"] == "Cancelado").sum())
    devolvidas = int((df["situacao"] == "Devolvido").sum())

    # tempos — ignorando NaN
    med_ate_ag = float(df["dias_ate_agendar"].dropna().median()) if "dias_ate_agendar" in df else np.nan
    p90_ate_ag = float(df["dias_ate_agendar"].dropna().quantile(0.90)) if "dias_ate_agendar" in df else np.nan
    med_ate_real = float(df["dias_ate_realizar"].dropna().median()) if "dias_ate_realizar" in df else np.nan

    # taxa de cancelamento entre os que tinham agendamento
    base_cancel = df[df["situacao"].isin(["Agendado","Cancelado","Devolvido","Realizado"])]
    taxa_cancel = float((base_cancel["situacao"].isin(["Cancelado","Devolvido"]).mean()*100) if len(base_cancel) else 0.0)

    return {
        "fila_atual": fila_atual,
        "agendadas": agendadas,
        "realizadas": realizadas,
        "canceladas": canceladas,
        "devolvidas": devolvidas,
        "med_ate_ag": med_ate_ag,
        "p90_ate_ag": p90_ate_ag,
        "med_ate_real": med_ate_real,
        "taxa_cancel": taxa_cancel,
    }


def plot_backlog(df: pd.DataFrame):
    base = df.groupby(["mes","situacao"], as_index=False).size()
    fig = px.area(base, x="mes", y="size", color="situacao", groupnorm=None, title="Backlog por mês (situação)")
    fig.update_layout(hovermode="x unified", margin=dict(t=60,b=20,l=20,r=20))
    return fig


def plot_espera_por_prioridade(df: pd.DataFrame):
    base = df[df["situacao"].isin(["Agendado","Realizado"])].copy()
    if base.empty:
        return go.Figure()
    base = base.melt(id_vars=["prioridade"], value_vars=["dias_ate_agendar","dias_ate_realizar"], var_name="fase", value_name="dias")
    base = base.dropna()
    fig = px.box(base, x="prioridade", y="dias", color="fase", points="suspectedoutliers", title="Tempo de espera por prioridade (agendar vs realizar)")
    fig.update_layout(margin=dict(t=60,b=20,l=20,r=20))
    return fig


def plot_ranking_fila(df: pd.DataFrame, top_n=15):
    base = df[df["situacao"]=="Aguardando"]["especialidade"].value_counts().reset_index()
    base.columns = ["especialidade","fila"]
    base = base.sort_values("fila", ascending=True).tail(top_n)
    fig = px.bar(base, x="fila", y="especialidade", orientation="h", title=f"Top {top_n} filas por especialidade")
    fig.update_layout(margin=dict(t=60,b=20,l=20,r=20))
    return fig


def plot_funil(df: pd.DataFrame):
    etapas = ["Solicitado","Agendado","Realizado"]
    vals = [len(df), int((df["situacao"]=="Agendado").sum()), int((df["situacao"]=="Realizado").sum())]
    fig = go.Figure(go.Funnel(y=etapas, x=vals, textinfo="value+percent initial"))
    fig.update_layout(title="Funil de solicitações", margin=dict(t=60,b=20,l=20,r=20))
    return fig


def tabela_prioridade(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty: return pd.DataFrame()
    g = df.groupby("prioridade")
    out = pd.DataFrame({
        "Solicitações": g.size(),
        "Fila (agora)": g.apply(lambda x: (x["situacao"]=="Aguardando").sum()),
        "Mediana até agendar": g["dias_ate_agendar"].median(),
        "P90 até agendar": g["dias_ate_agendar"].quantile(0.90),
        "Mediana até realizar": g["dias_ate_realizar"].median(),
        "Cancel/Devol (%)": g.apply(lambda x: (x["situacao"].isin(["Cancelado","Devolvido"]).mean()*100)),
    }).reset_index().sort_values("P90 até agendar")
    return out


# ---------------------------------
# APP
# ---------------------------------
st.title("📊 Dashboard — Regulação Assistencial (MIRA)")
st.caption("Solicitações, filas, tempos de espera, funis e prioridades — inspirado no Modelo de Informação do e-SUS Regulação")

with st.expander("ℹ️ Sobre o protótipo / colunas esperadas", expanded=False):
    st.markdown(
        """
        Este dashboard segue o **Modelo de Informação da Regulação Assistencial (MIRA)** descrito na Wiki do Ministério da Saúde.
        Colunas mínimas esperadas: `id_solicitacao`, `data_solicitacao`, `especialidade`, `prioridade`, `situacao`, `data_agendamento`, `data_realizacao`, `unidade_origem`, `servico_destino`.
        """
    )

base = carregar_dados()
filtrado = filtros(base)

# KPIs
ind = indicadores(filtrado)
ca, cb, cc, cd, ce = st.columns(5)
kpi(ca, "Fila atual (Aguardando)", f"{ind['fila_atual']:,}".replace(",","."))
kpi(cb, "Agendadas", f"{ind['agendadas']:,}".replace(",","."))
kpi(cc, "Realizadas", f"{ind['realizadas']:,}".replace(",","."))
kpi(cd, "Cancel/Devol (%)", f"{ind['taxa_cancel']:.1f}%", "entre casos com etapa marcada")
kpi(ce, "Mediana até agendar (dias)", f"{ind['med_ate_ag']:.0f}", f"P90: {ind['p90_ate_ag']:.0f}d")

st.markdown("---")

col1, col2 = st.columns((2,1))
with col1:
    st.plotly_chart(plot_backlog(filtrado), use_container_width=True)
with col2:
    st.plotly_chart(plot_funil(filtrado), use_container_width=True)

st.plotly_chart(plot_espera_por_prioridade(filtrado), use_container_width=True)

st.plotly_chart(plot_ranking_fila(filtrado, top_n=15), use_container_width=True)

st.subheader("📋 Tabela por prioridade")
st.dataframe(tabela_prioridade(filtrado), use_container_width=True)

# Tabela detalhada (recorte)
st.subheader("🔎 Solicitações — detalhe (amostra)")
st.dataframe(filtrado.sort_values("data_solicitacao", ascending=False).head(200), use_container_width=True)
