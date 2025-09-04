# app.py — Dashboard com Streamlit
# --------------------------------------------------------------
# Este é um esqueleto inicial de um app Streamlit para visualizar
# seus dados processados no ETL (ex.: teste_aps). A ideia é ir
# evoluindo por módulos conforme você for pedindo.
# --------------------------------------------------------------

import os
from typing import Optional, Tuple, Dict

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

# =============================
# CONFIGURAÇÕES BÁSICAS
# =============================
st.set_page_config(
    page_title="Dashboard APS",
    page_icon="📊",
    layout="wide",
)

# =============================
# FUNÇÕES UTILITÁRIAS
# =============================
@st.cache_data(show_spinner=False)
def load_data(
    file_path: Optional[str] = None,
    uploaded_file: Optional[st.runtime.uploaded_file_manager.UploadedFile] = None,
) -> pd.DataFrame:
    """
    Carrega o DataFrame de duas formas:
    - a partir de um arquivo local no repositório (CSV ou Parquet)
    - ou de um arquivo enviado via uploader no sidebar.

    Retorna um DataFrame pandas. Lança erro amigável se nada for encontrado.
    """
    if uploaded_file is not None:
        if uploaded_file.name.lower().endswith(".parquet"):
            return pd.read_parquet(uploaded_file)
        return pd.read_csv(uploaded_file, sep=None, engine="python")  # autodetecta separador

    if file_path and os.path.exists(file_path):
        if file_path.lower().endswith(".parquet"):
            return pd.read_parquet(file_path)
        return pd.read_csv(file_path, sep=None, engine="python")

    raise FileNotFoundError(
        "Nenhuma fonte de dados encontrada. Envie um arquivo no sidebar ou configure o caminho padrão."
    )


def safe_nunique(s: pd.Series) -> int:
    """Retorna nunique de forma segura, mesmo se a série não existir/for vazia."""
    try:
        return s.nunique(dropna=True)
    except Exception:
        return 0


def kpi_box(label: str, value, help_text: str = ""):
    """Componente simples de KPI em colunas com formatação enxuta."""
    st.metric(label, value)
    if help_text:
        st.caption(help_text)


def plot_equipes_por_estabelecimento(df: pd.DataFrame, cnes_selecionado) -> go.Figure:
    """
    Plota um gráfico de barras horizontais (Plotly) com a quantidade de profissionais distintos
    por equipe (NO_REFERENCIA) para um dado estabelecimento (CO_CNES).
    """
    req_cols = {"CO_CNES", "NO_REFERENCIA", "CO_PROFISSIONAL_SUS"}
    if not req_cols.issubset(df.columns):
        fig = go.Figure()
        fig.update_layout(title="Colunas requeridas ausentes: " + ", ".join(sorted(req_cols - set(df.columns))))
        return fig

    g = (
        df[df["CO_CNES"] == cnes_selecionado]
        .groupby(["CO_CNES", "NO_REFERENCIA"]) ["CO_PROFISSIONAL_SUS"].nunique()
        .reset_index(name="qtd_profissionais")
        .sort_values("qtd_profissionais", ascending=True)
    )

    fig = go.Figure(
        data=[
            go.Bar(
                x=g["qtd_profissionais"],
                y=g["NO_REFERENCIA"],
                orientation="h",
                hovertemplate="<b>%{y}</b><br>Profissionais distintos: %{x}<extra></extra>",
            )
        ]
    )

    nome = df.loc[df["CO_CNES"] == cnes_selecionado, "NO_FANTASIA"].dropna().unique()
    nome_str = nome[0] if len(nome) else str(cnes_selecionado)

    fig.update_layout(
        title=f"Profissionais distintos por Equipe (NO_REFERENCIA)\n<sup>Estabelecimento: {nome_str} — CNES: {cnes_selecionado}</sup>",
        xaxis_title="Quantidade de Profissionais Distintos",
        yaxis_title="Equipe (NO_REFERENCIA)",
        height=max(420, 24 * max(1, len(g))),
        margin=dict(l=200, r=40, t=100, b=40),
    )
    return fig


def plot_percentual_nulos(df: pd.DataFrame) -> go.Figure:
    """Plota barras horizontais com o percentual de nulos por coluna."""
    null_pct = (df.isna().mean() * 100).round(2).sort_values(ascending=True)
    fig = go.Figure(
        data=[
            go.Bar(
                x=null_pct.values,
                y=null_pct.index.tolist(),
                orientation="h",
                hovertemplate="<b>%{y}</b><br>Nulos: %{x}%<extra></extra>",
            )
        ]
    )
    fig.update_layout(
        title="Percentual de valores nulos por coluna",
        xaxis_title="% de nulos",
        yaxis_title="Coluna",
        height=max(420, 20 * max(1, len(null_pct))),
        margin=dict(l=220, r=40, t=70, b=40),
    )
    return fig


# =============================
# SIDEBAR (Entrada de dados e filtros)
# =============================
with st.sidebar:
    st.header("⚙️ Configurações")

    st.markdown(
        "Carregue um arquivo **CSV** ou **Parquet** (resultado do seu ETL).\n\n"
        "Opcionalmente, você pode definir um caminho padrão no código."
    )

    uploaded = st.file_uploader("Enviar arquivo de dados", type=["csv", "parquet"])  # noqa: F841

    # Caso queira referenciar um arquivo no repo, ajuste aqui:
    default_path = st.text_input("Caminho padrão (opcional)", value="data/etl_saida.parquet")

# =============================
# CARREGAR DADOS
# =============================
try:
    df = load_data(file_path=default_path if default_path else None, uploaded_file=uploaded)
except Exception as e:
    st.error(f"Erro ao carregar dados: {e}")
    st.stop()

st.success("Dados carregados com sucesso!")

# =============================
# PÁGINAS / NAVEGAÇÃO
# =============================
pagina = st.sidebar.radio(
    "Navegação",
    ["Visão Geral", "Equipes por Estabelecimento", "Qualidade dos Dados"],
    index=0,
)

# =============================
# VISÃO GERAL
# =============================
if pagina == "Visão Geral":
    st.title("📊 Dashboard APS — Visão Geral")
    st.caption("Resumo inicial dos dados carregados.")

    cols_exist = {c for c in ["CO_PROFISSIONAL_SUS", "SEQ_EQUIPE", "CO_CNES", "NO_FANTASIA", "DS_EQUIPE"] if c in df.columns}

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        kpi_box("Profissionais distintos", safe_nunique(df.get("CO_PROFISSIONAL_SUS", pd.Series(dtype=object))), "Base completa")
    with c2:
        kpi_box("Equipes distintas (SEQ_EQUIPE)", safe_nunique(df.get("SEQ_EQUIPE", pd.Series(dtype=object))))
    with c3:
        kpi_box("Estabelecimentos (CO_CNES)", safe_nunique(df.get("CO_CNES", pd.Series(dtype=object))))
    with c4:
        kpi_box("Tipos de Equipe (DS_EQUIPE)", safe_nunique(df.get("DS_EQUIPE", pd.Series(dtype=object))))

    st.markdown("---")
    st.subheader("Amostra dos dados")
    st.dataframe(df.head(30), use_container_width=True)

# =============================
# EQUIPES POR ESTABELECIMENTO
# =============================
elif pagina == "Equipes por Estabelecimento":
    st.title("👩‍⚕️ Equipes por Estabelecimento")
    st.caption("Gráfico interativo de profissionais distintos por equipe dentro de cada estabelecimento.")

    if not {"CO_CNES", "NO_FANTASIA"}.issubset(df.columns):
        st.warning("Colunas necessárias ausentes: CO_CNES, NO_FANTASIA.")
    else:
        # Mapeia CO_CNES -> NO_FANTASIA
        mapa_nome: Dict = (
            df[["CO_CNES", "NO_FANTASIA"]]
            .dropna(subset=["CO_CNES", "NO_FANTASIA"]).drop_duplicates("CO_CNES")
            .set_index("CO_CNES")["NO_FANTASIA"].to_dict()
        )
        # Ordenar por nome fantasia para facilitar busca
        opcoes = sorted([(nome, cnes) for cnes, nome in mapa_nome.items()], key=lambda x: x[0].lower())

        # Seletor de estabelecimento pelo nome
        nome_sel = st.selectbox("Selecione o estabelecimento (NO_FANTASIA)", options=[n for n, _ in opcoes])
        cnes_sel = next(c for n, c in opcoes if n == nome_sel)

        fig = plot_equipes_por_estabelecimento(df, cnes_sel)
        st.plotly_chart(fig, use_container_width=True, config={"displaylogo": False})

        # Tabela detalhada abaixo
        st.markdown("### Detalhe (tabela)")
        detalhe = (
            df[df["CO_CNES"] == cnes_sel]
            .groupby(["NO_REFERENCIA"]) ["CO_PROFISSIONAL_SUS"].nunique()
            .reset_index(name="qtd_profissionais")
            .sort_values("qtd_profissionais", ascending=False)
        )
        st.dataframe(detalhe, use_container_width=True)

# =============================
# QUALIDADE DOS DADOS
# =============================
elif pagina == "Qualidade dos Dados":
    st.title("🧪 Qualidade dos Dados")
    st.caption("Análise de nulos por coluna.")

    fig_nulos = plot_percentual_nulos(df)
    st.plotly_chart(fig_nulos, use_container_width=True, config={"displaylogo": False})

    st.markdown("### Tabela de nulos")
    null_tbl = (df.isna().mean() * 100).round(2).reset_index()
    null_tbl.columns = ["coluna", "%_nulos"]
    st.dataframe(null_tbl.sort_values("%_nulos", ascending=False), use_container_width=True)

# =============================
# RODAPÉ
# =============================
st.markdown("---")
st.caption("Feito com ❤️ em Streamlit. Vamos iterar juntos: peça a próxima funcionalidade!")
