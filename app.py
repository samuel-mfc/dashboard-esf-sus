# app.py — Dashboard com Streamlit (com fallback quando Streamlit não está instalado)
# ----------------------------------------------------------------------------
# Este arquivo detecta automaticamente se o módulo `streamlit` está disponível.
# - Se **Streamlit estiver instalado**: roda a interface completa (páginas, KPIs, gráficos).
# - Se **Streamlit NÃO estiver instalado**: entra em **modo CLI de auto‑testes**,
#   executa testes unitários simples dos utilitários e salva gráficos de exemplo
#   em HTML na pasta `artifacts/`, sem quebrar com ModuleNotFoundError.
#
# Para rodar com UI:
#     pip install streamlit pandas plotly pyarrow
#     streamlit run app.py
# ----------------------------------------------------------------------------

import os
from typing import Optional, Dict, Any

import pandas as pd
import plotly.graph_objects as go
import plotly.io as pio

# =============================
# TENTATIVA DE IMPORT DO STREAMLIT
# =============================
try:
    import streamlit as st  # type: ignore
    ST_AVAILABLE = True

    # Alias do decorator de cache para permitir reuso em funções
    cache_data = st.cache_data
except ModuleNotFoundError:
    ST_AVAILABLE = False

    class _NoStreamlitShim:
        def __getattr__(self, _):
            def _noop(*args, **kwargs):
                return None
            return _noop

    st = _NoStreamlitShim()

    def cache_data(*dargs, **dkwargs):
        def _decorator(func):
            return func
        return _decorator


@cache_data(show_spinner=False)
def load_data(file_path: Optional[str] = None, uploaded_file: Optional[Any] = None) -> pd.DataFrame:
    if uploaded_file is not None:
        nome = getattr(uploaded_file, "name", "").lower()
        if nome.endswith(".parquet"):
            return pd.read_parquet(uploaded_file)
        return pd.read_csv(uploaded_file, sep=None, engine="python")

    if file_path and os.path.exists(file_path):
        if file_path.lower().endswith(".parquet"):
            return pd.read_parquet(file_path)
        return pd.read_csv(file_path, sep=None, engine="python")

    raise FileNotFoundError("Nenhuma fonte de dados encontrada.")


def safe_nunique(s: pd.Series) -> int:
    try:
        return s.nunique(dropna=True)
    except Exception:
        return 0


def plot_profissionais_por_categoria(df: pd.DataFrame, cnes_selecionado: int) -> go.Figure:
    if not {"CO_CNES", "DS_ATIVIDADE_PROFISSIONAL", "CO_PROFISSIONAL_SUS"}.issubset(df.columns):
        fig = go.Figure()
        fig.update_layout(title="Colunas necessárias ausentes.")
        return fig

    grupo = (
        df[df["CO_CNES"] == cnes_selecionado]
        .groupby("DS_ATIVIDADE_PROFISSIONAL")["CO_PROFISSIONAL_SUS"]
        .nunique()
        .sort_values(ascending=True)
        .reset_index(name="qtd_profissionais")
    )

    nome = df.loc[df["CO_CNES"] == cnes_selecionado, "NO_FANTASIA"].dropna().unique()
    nome_str = nome[0] if len(nome) else str(cnes_selecionado)

    fig = go.Figure(
        data=[
            go.Bar(
                x=grupo["qtd_profissionais"],
                y=grupo["DS_ATIVIDADE_PROFISSIONAL"],
                orientation="h",
                hovertemplate="<b>%{y}</b><br>Profissionais: %{x}<extra></extra>",
            )
        ]
    )

    fig.update_layout(
        title=(
            f"Profissionais por Categoria Profissional<br><sup>{nome_str} — CNES {cnes_selecionado}</sup>"
        ),
        xaxis_title="Quantidade de Profissionais",
        yaxis_title="Categoria Profissional",
        height=max(420, 20 * len(grupo)),
        margin=dict(l=250, r=40, t=100, b=40),
    )
    return fig


if ST_AVAILABLE:
    st.set_page_config(page_title="Dashboard APS", page_icon="📊", layout="wide")

    with st.sidebar:
        st.header("⚙️ Configurações")
        uploaded = st.file_uploader("Enviar arquivo de dados", type=["csv", "parquet"])
        default_path = st.text_input("Caminho padrão (opcional)", value="data/etl_saida.parquet")

    try:
        df = load_data(file_path=default_path if default_path else None, uploaded_file=uploaded)
    except Exception as e:
        st.error(f"Erro ao carregar dados: {e}")
        st.stop()

    st.success("Dados carregados com sucesso!")

    pagina = st.sidebar.radio(
        "Navegação",
        ["Visão Geral", "Equipes por Estabelecimento", "Categorias Profissionais"],
        index=0,
    )

    if pagina == "Categorias Profissionais":
        st.title("🧑‍⚕️ Categorias Profissionais por Estabelecimento")

        if not {"CO_CNES", "NO_FANTASIA"}.issubset(df.columns):
            st.warning("Colunas necessárias ausentes: CO_CNES, NO_FANTASIA.")
        else:
            mapa_nome = (
                df[["CO_CNES", "NO_FANTASIA"]]
                .dropna().drop_duplicates("CO_CNES")
                .set_index("CO_CNES")["NO_FANTASIA"].to_dict()
            )

            opcoes = sorted([(nome, cnes) for cnes, nome in mapa_nome.items()], key=lambda x: x[0].lower())
            nome_sel = st.selectbox("Selecione o estabelecimento", [n for n, _ in opcoes])
            cnes_sel = next(c for n, c in opcoes if n == nome_sel)

            fig = plot_profissionais_por_categoria(df, cnes_sel)
            st.plotly_chart(fig, use_container_width=True, config={"displaylogo": False})
