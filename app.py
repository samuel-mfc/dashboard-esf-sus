# app.py
# pip install streamlit plotly pandas openpyxl

import streamlit as st
import pandas as pd
import plotly.express as px
from io import StringIO

st.set_page_config(page_title="Dashboard de Atendimentos", layout="wide")

st.title("📊 Dashboard de Atendimentos Médicos")

COL_ANO = "Ano"
COL_UNID = "nome_estab"
COL_MED  = "nome_profissional"
EXPECTED_COLS = {COL_ANO, COL_UNID, COL_MED}

# ==========================
# 1) Carregar dados
# ==========================
st.sidebar.header("Dados")

@st.cache_data
def load_data(file):
    name = file.name.lower()
    if name.endswith(".csv"):
        # Tenta auto detectar separador
        data = file.read().decode("utf-8", errors="ignore")
        # heurística simples: ; vs ,
        sep = ";" if data.count(";") > data.count(",") else ","
        return pd.read_csv(StringIO(data), sep=sep)
    elif name.endswith(".xlsx") or name.endswith(".xls"):
        return pd.read_excel(file)
    else:
        raise ValueError("Formato não suportado. Envie CSV ou Excel.")

uploaded = st.sidebar.file_uploader("Envie um arquivo CSV/Excel com as colunas: Ano, nome_estab, nome_profissional",
                                    type=["csv", "xlsx", "xls"])

if uploaded is not None:
    try:
        df = load_data(uploaded)
    except Exception as e:
        st.error(f"Erro ao carregar arquivo: {e}")
        st.stop()
else:
    st.sidebar.info("Nenhum arquivo enviado. Usando dados de exemplo.")
    df = pd.DataFrame({
        COL_ANO: [2023, 2023, 2023, 2024, 2024, 2024, 2025, 2025, 2025],
        COL_UNID: ["Centro", "Centro", "Zona Sul", "Centro", "Zona Norte", "Zona Norte", "Centro", "Zona Sul", "Zona Norte"],
        COL_MED: ["Ana", "Bruno", "Ana", "Carlos", "Bruno", "Ana", "Ana", "Diana", "Carlos"]
    })

# Validação de colunas
missing = EXPECTED_COLS - set(df.columns)
if missing:
    st.error(f"As seguintes colunas obrigatórias não foram encontradas no arquivo: {sorted(missing)}")
    st.stop()

# ==========================
# 2) Preparação e Filtros
# ==========================
df_f = df.copy()

# Coerção leve: garante visual consistente
df_f["_Ano_str"] = df_f[COL_ANO].astype(str)
df_f["_Unid_str"] = df_f[COL_UNID].astype(str)
df_f["_Med_str"]  = df_f[COL_MED].astype(str)

st.sidebar.header("Filtros")

anos_opts = sorted(df_f["_Ano_str"].dropna().unique().tolist())
unid_opts = sorted(df_f["_Unid_str"].dropna().unique().tolist())
med_opts  = sorted(df_f["_Med_str"].dropna().unique().tolist())

anos_sel = st.sidebar.multiselect("Ano(s)", anos_opts, default=anos_opts)
unid_sel = st.sidebar.multiselect("Unidade(s)", unid_opts, default=unid_opts)
med_sel  = st.sidebar.multiselect("Profissional(is)", med_opts, default=med_opts)

top_n = st.sidebar.slider("Top N por gráfico", min_value=5, max_value=50, value=15, step=5)

mask = (
    df_f["_Ano_str"].isin(anos_sel) &
    df_f["_Unid_str"].isin(unid_sel) &
    df_f["_Med_str"].isin(med_sel)
)
dff = df_f.loc[mask].copy()

m1, m2, m3 = st.columns(3)
m1.metric("Total de Atendimentos (filtro)", len(dff))
m2.metric("Profissionais únicos", dff[COL_MED].nunique())
m3.metric("Unidades únicas", dff[COL_UNID].nunique())

if dff.empty:
    st.warning("Sem dados para os filtros selecionados.")
    st.stop()

# ==========================
# 3) Agregações
# ==========================
por_medico = (
    dff.groupby(COL_MED, dropna=False)
       .size()
       .reset_index(name="Atendimentos")
       .sort_values("Atendimentos", ascending=False)
       .head(top_n)
)

por_unidade = (
    dff.groupby(COL_UNID, dropna=False)
       .size()
       .reset_index(name="Atendimentos")
       .sort_values("Atendimentos", ascending=False)
       .head(top_n)
)

# ==========================
# 4) Gráficos (Plotly)
# ==========================
fig_med = px.bar(
    por_medico,
    x="Atendimentos",
    y=COL_MED,
    orientation="h",
    title="Atendimentos por Profissional" (Top {min(top_n, len(por_medico))}) — n={len(dff)}"
)
fig_med.update_layout(
    xaxis_title="Atendimentos",
    yaxis_title="Profissional",
    hovermode="x unified",
    margin=dict(l=10, r=10, t=60, b=10)
)

fig_unid = px.bar(
    por_unidade,
    x="Atendimentos",
    y=COL_UNID,
    orientation="h",
    title="Atendimentos por Unidade" (Top {min(top_n, len(por_unidade))}) — n={len(dff)}"
)
fig_unid.update_layout(
    xaxis_title="Atendimentos",
    yaxis_title="Unidade",
    hovermode="x unified",
    margin=dict(l=10, r=10, t=60, b=10)
)

c1, c2 = st.columns(2)
with c1:
    st.plotly_chart(fig_med, use_container_width=True)
with c2:
    st.plotly_chart(fig_unid, use_container_width=True)

# ==========================
# 5) Tabela e Download
# ==========================
with st.expander("Ver dados filtrados"):
    st.dataframe(dff[[COL_ANO, COL_UNID, COL_MED]])

csv = dff[[COL_ANO, COL_UNID, COL_MED]].to_csv(index=False).encode("utf-8")
st.download_button(
    "⬇️ Baixar dados filtrados (CSV)",
    data=csv,
    file_name="atendimentos_filtrados.csv",
    mime="text/csv"
)
