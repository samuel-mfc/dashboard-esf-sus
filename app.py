import io
import sys
from typing import List, Tuple

import pandas as pd
import numpy as np
import streamlit as st
import plotly.express as px

# =============================
# Configuração da Página
# =============================
st.set_page_config(
    page_title="Dashboard de Atendimentos Clínicos (RNDS)",
    page_icon="🩺",
    layout="wide",
    initial_sidebar_state="expanded",
)

# =============================
# Texto de Apresentação
# =============================
st.title("🩺 Dashboard de Atendimentos Clínicos — RNDS")
st.markdown(
    """
Este app lê um **CSV** no formato mínimo do *Registro de Atendimento Clínico (RAC)* e 
monta um painel interativo com filtros, indicadores e gráficos. 

**Como usar:** faça upload do CSV na barra lateral. Opcionalmente, exporte os dados filtrados.
"""
)

# =============================
# Esquema mínimo esperado
# =============================
REQUIRED_COLUMNS: List[str] = [
    "identificador_nacional_individuo",
    "identificador_estabelecimento_saude_cnes",
    "procedencia",
    "data_hora_atendimento_iso8601",
    "modalidade_assistencial",
    "carater_atendimento",
    "profissional_identificador_cpf",
    "profissional_numero_conselho",
    "profissional_conselho",
    "profissional_uf_conselho",
    "profissional_ocupacao_cbo",
    "profissional_responsavel",
    "problema_diagnostico_codigo",
    "problema_diagnostico_terminologia",
]

ALIASES = {
    # Permite pequenas variações comuns
    "data_hora_atendimento": "data_hora_atendimento_iso8601",
    "data_atendimento": "data_hora_atendimento_iso8601",
    "cnes": "identificador_estabelecimento_saude_cnes",
    "cns_cpf": "identificador_nacional_individuo",
}

# =============================
# Funções utilitárias
# =============================

@st.cache_data(show_spinner=False)
def load_csv(file: io.BytesIO) -> pd.DataFrame:
    return pd.read_csv(file, dtype=str, encoding="utf-8")


def normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    cols = {c: c.strip() for c in df.columns}
    df = df.rename(columns=cols)
    # Normalizar para minúsculas e mapear aliases
    mapping = {}
    for c in df.columns:
        base = c
        low = c.lower()
        if low in ALIASES:
            mapping[c] = ALIASES[low]
        else:
            mapping[c] = c
    df = df.rename(columns=mapping)
    return df


def validate_schema(df: pd.DataFrame) -> Tuple[bool, List[str]]:
    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    return (len(missing) == 0, missing)


def coerce_types(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    # Datas
    if "data_hora_atendimento_iso8601" in df.columns:
        df["data_hora_atendimento_iso8601"] = pd.to_datetime(
            df["data_hora_atendimento_iso8601"], errors="coerce"
        )
        df["data"] = df["data_hora_atendimento_iso8601"].dt.date
        df["ano"] = df["data_hora_atendimento_iso8601"].dt.year
        df["mes"] = df["data_hora_atendimento_iso8601"].dt.to_period("M").astype(str)
        df["semana"] = df["data_hora_atendimento_iso8601"].dt.strftime("%Y-%U")
        df["hora"] = df["data_hora_atendimento_iso8601"].dt.hour
        dias_pt = ["segunda-feira","terça-feira","quarta-feira","quinta-feira","sexta-feira","sábado","domingo"]
        df["dia_semana"] = df["data_hora_atendimento_iso8601"].dt.dayofweek.map(
            lambda i: dias_pt[i] if pd.notna(i) else None
        )
    # Numéricos (onde fizer sentido)
    for c in ["identificador_estabelecimento_saude_cnes"]:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="ignore")
    return df


def kpi(label: str, value, help: str = ""):
    mcol = st.metric
    mcol(label, value, help=help)


# =============================
# Sidebar — Upload & Filtros
# =============================
st.sidebar.header("📤 Upload & Filtros")
file = st.sidebar.file_uploader("Envie o CSV do RAC (mínimo)", type=["csv"]) 

example_note = st.sidebar.expander("Ver colunas mínimas esperadas").checkbox(
    "Mostrar lista de colunas"
)
if example_note:
    st.sidebar.code("\n".join(REQUIRED_COLUMNS), language="text")

if file is None:
    st.info("Envie um arquivo CSV na barra lateral para iniciar.")
    st.stop()

# Carregar dados
try:
    df_raw = load_csv(file)
except Exception as e:
    st.error(f"Erro ao ler o CSV: {e}")
    st.stop()

# Normalizar e validar
_df = normalize_columns(df_raw)
ok, missing = validate_schema(_df)
if not ok:
    st.error(
        "Colunas obrigatórias ausentes no CSV:\n- " + "\n- ".join(missing)
    )
    st.stop()

# Tipos e colunas derivadas
df = coerce_types(_df)

# Filtros
with st.sidebar:
    st.markdown("---")
    st.subheader("🔎 Filtros")
    # Intervalo de datas
    min_date = pd.to_datetime(df["data_hora_atendimento_iso8601"].min())
    max_date = pd.to_datetime(df["data_hora_atendimento_iso8601"].max())
    date_range = st.date_input(
        "Período do atendimento",
        value=(min_date.date(), max_date.date()),
        min_value=min_date.date(),
        max_value=max_date.date(),
    )

    modalidades = sorted(df["modalidade_assistencial"].dropna().unique())
    sel_modalidades = st.multiselect(
        "Modalidade assistencial",
        options=modalidades,
        default=modalidades,
    )

    caracteres = sorted(df["carater_atendimento"].dropna().unique())
    sel_carater = st.multiselect(
        "Caráter do atendimento",
        options=caracteres,
        default=caracteres,
    )

    procedencias = sorted(df["procedencia"].dropna().unique())
    sel_procedencia = st.multiselect(
        "Procedência",
        options=procedencias,
        default=procedencias,
    )

    terminologias = sorted(df["problema_diagnostico_terminologia"].dropna().unique())
    sel_termo = st.multiselect(
        "Terminologia (CID/CIAP)",
        options=terminologias,
        default=terminologias,
    )

# Aplicar filtros
mask = (
    (df["data_hora_atendimento_iso8601"].dt.date >= date_range[0])
    & (df["data_hora_atendimento_iso8601"].dt.date <= date_range[1])
    & (df["modalidade_assistencial"].isin(sel_modalidades))
    & (df["carater_atendimento"].isin(sel_carater))
    & (df["procedencia"].isin(sel_procedencia))
    & (df["problema_diagnostico_terminologia"].isin(sel_termo))
)

filtered = df.loc[mask].copy()

# =============================
# KPIs
# =============================
st.subheader("📈 Indicadores Gerais")
kpi_cols = st.columns(4)
with kpi_cols[0]:
    kpi("Atendimentos", f"{len(filtered):,}".replace(",", "."))
with kpi_cols[1]:
    kpi("Indivíduos únicos", filtered["identificador_nacional_individuo"].nunique())
with kpi_cols[2]:
    kpi("Estabelecimentos (CNES)", filtered["identificador_estabelecimento_saude_cnes"].nunique())
with kpi_cols[3]:
    kpi("Profissionais", filtered["profissional_identificador_cpf"].nunique())

# =============================
# Gráficos
# =============================
st.subheader("📊 Visualizações")

# Séries temporais por dia
if not filtered.empty:
    ts = (
        filtered.groupby("data", dropna=True)["identificador_nacional_individuo"]
        .count()
        .reset_index(name="atendimentos")
        .sort_values("data")
    )
    fig_ts = px.line(ts, x="data", y="atendimentos", markers=True, title="Atendimentos por dia")
    st.plotly_chart(fig_ts, use_container_width=True)

    col1, col2 = st.columns(2)

    # Top diagnósticos
    with col1:
        top_diag = (
            filtered.groupby(["problema_diagnostico_terminologia", "problema_diagnostico_codigo"])  
            ["identificador_nacional_individuo"].count()
            .reset_index(name="atendimentos")
            .sort_values("atendimentos", ascending=False)
            .head(15)
        )
        fig_diag = px.bar(
            top_diag,
            x="atendimentos",
            y="problema_diagnostico_codigo",
            color="problema_diagnostico_terminologia",
            orientation="h",
            title="Top diagnósticos",
        )
        st.plotly_chart(fig_diag, use_container_width=True)

    # Atendimentos por modalidade e caráter
    with col2:
        moda = (
            filtered.groupby(["modalidade_assistencial", "carater_atendimento"])  
            ["identificador_nacional_individuo"].count()
            .reset_index(name="atendimentos")
        )
        fig_mod = px.bar(
            moda,
            x="modalidade_assistencial",
            y="atendimentos",
            color="carater_atendimento",
            barmode="group",
            title="Atendimentos por modalidade e caráter",
        )
        st.plotly_chart(fig_mod, use_container_width=True)

    # Mapa de calor (dia da semana x hora)
    heat = (
        filtered.assign(dia_semana=pd.Categorical(
            filtered["dia_semana"],
            categories=[
                "segunda-feira",
                "terça-feira",
                "quarta-feira",
                "quinta-feira",
                "sexta-feira",
                "sábado",
                "domingo",
            ],
            ordered=True,
        ))
        .groupby(["dia_semana", "hora"])  
        ["identificador_nacional_individuo"].count()
        .reset_index(name="atendimentos")
    )
    fig_heat = px.density_heatmap(
        heat,
        x="hora",
        y="dia_semana",
        z="atendimentos",
        nbinsx=24,
        title="Distribuição horária por dia da semana",
        labels={"hora": "Hora do dia"},
    )
    st.plotly_chart(fig_heat, use_container_width=True)

else:
    st.warning("Nenhum registro atende aos filtros selecionados.")

# =============================
# Tabela e Download
# =============================
st.subheader("🧾 Amostra de dados filtrados")
st.dataframe(filtered.head(200), use_container_width=True)

st.download_button(
    label="⬇️ Baixar dados filtrados (CSV)",
    data=filtered.to_csv(index=False).encode("utf-8"),
    file_name="rac_filtrado.csv",
    mime="text/csv",
)

# =============================
# Detalhes e Qualidade
# =============================
st.subheader("🧪 Validação & Qualidade")

# Linhas inválidas por data não parseada
invalid_dt = df[df["data_hora_atendimento_iso8601"].isna()]
colq1, colq2, colq3 = st.columns(3)
with colq1:
    st.metric("Linhas com data inválida", len(invalid_dt))
with colq2:
    st.metric("Diagnósticos distintos", filtered[[
        "problema_diagnostico_terminologia",
        "problema_diagnostico_codigo"
    ]].drop_duplicates().shape[0])
with colq3:
    st.metric("CNES distintos", filtered["identificador_estabelecimento_saude_cnes"].nunique())

if len(invalid_dt) > 0:
    with st.expander("Visualizar linhas com data inválida"):
        st.dataframe(invalid_dt.head(200), use_container_width=True)

# =============================
# Rodapé
# =============================
st.markdown("""
---
**Observações**
- Este painel assume o **mínimo obrigatório** do RAC. Campos adicionais (ex.: procedimentos, sinais vitais, desfecho) podem ser incorporados.
- Datas são interpretadas a partir de `data_hora_atendimento_iso8601` (ISO-8601). Se o CSV trouxer outro nome, utilize os **aliases** ou ajuste antes de importar.
- Compatível com arquivos gerados pelo exemplo de dataframe desta conversa.
""")
