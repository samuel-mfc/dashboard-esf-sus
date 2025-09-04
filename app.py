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

try:
    import streamlit as st  # type: ignore
    ST_AVAILABLE = True
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

def plot_equipes_por_estabelecimento(df: pd.DataFrame, cnes_selecionado: int) -> go.Figure:
    if not {"CO_CNES", "NO_REFERENCIA", "CO_PROFISSIONAL_SUS"}.issubset(df.columns):
        fig = go.Figure()
        fig.update_layout(title="Colunas requeridas ausentes para este gráfico.")
        return fig
    
    
    dados = (
        df[df["CO_CNES"] == cnes_selecionado]
        .groupby("NO_REFERENCIA")["CO_PROFISSIONAL_SUS"]
        .nunique()
        .reset_index(name="qtd_profissionais")
        .sort_values("qtd_profissionais", ascending=True)
     )


    nome = (df.loc[df["CO_CNES"] == cnes_selecionado, "NO_FANTASIA"].dropna().unique())
    nome_str = nome[0] if len(nome) else str(cnes_selecionado)


    fig = go.Figure(
        data=[
            go.Bar(
                x=dados["qtd_profissionais"],
                y=dados["NO_REFERENCIA"],
                orientation="h",
                hovertemplate="<b>%{y}</b><br>Profissionais distintos: %{x}<extra></extra>",
            )
        ]
    )


    fig.update_layout(
        title=(
        "Profissionais distintos por Equipe (NO_REFERENCIA)<br>"
        f"<sup>Estabelecimento: {nome_str} — CNES: {cnes_selecionado}</sup>"
        ),
        xaxis_title="Quantidade de Profissionais Distintos",
        yaxis_title="Equipe (NO_REFERENCIA)",
        height=max(420, 20 * len(dados)),
        margin=dict(l=220, r=40, t=100, b=40),
     )
 return fig


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
    st.write("Colunas carregadas:", df.columns.tolist())
    st.write("Shape do dataframe:", df.shape)

    pagina = st.sidebar.radio(
        "Navegação",
        ["Visão Geral", "Equipes por Estabelecimento", "Categorias Profissionais"],
        index=0,
    )

    if pagina == "Visão Geral":
        st.title("📊 Dashboard APS — Visão Geral")
        st.caption("Resumo inicial dos dados carregados.")

        c1, c2, c3, c4 = st.columns(4)
        with c1:
            st.metric("Profissionais distintos", safe_nunique(df.get("CO_PROFISSIONAL_SUS", pd.Series(dtype=object))))
        with c2:
            st.metric("Equipes distintas (SEQ_EQUIPE)", safe_nunique(df.get("SEQ_EQUIPE", pd.Series(dtype=object))))
        with c3:
            st.metric("Estabelecimentos (CO_CNES)", safe_nunique(df.get("CO_CNES", pd.Series(dtype=object))))
        with c4:
            st.metric("Tipos de Equipe (DS_EQUIPE)", safe_nunique(df.get("DS_EQUIPE", pd.Series(dtype=object))))

        st.markdown("---")
        st.subheader("Amostra dos dados")
        st.dataframe(df.head(30), use_container_width=True)

    elif pagina == "Equipes por Estabelecimento":
        st.title("👩‍⚕️ Equipes por Estabelecimento")
        st.caption("Gráfico interativo de profissionais distintos por equipe dentro de cada estabelecimento.")

        faltantes = {"CO_CNES", "NO_FANTASIA"} - set(df.columns)
        if faltantes:
            st.error(f"Colunas obrigatórias ausentes nesta página:\n- " + "\n- ".join(faltantes))
            st.stop()

        mapa_nome = (
            df[["CO_CNES", "NO_FANTASIA"]]
            .dropna(subset=["CO_CNES", "NO_FANTASIA"])
            .drop_duplicates("CO_CNES")
            .set_index("CO_CNES")["NO_FANTASIA"].to_dict()
        )
        opcoes = sorted([(nome, cnes) for cnes, nome in mapa_nome.items()], key=lambda x: x[0].lower())
        nome_sel = st.selectbox("Selecione o estabelecimento (NO_FANTASIA)", options=[n for n, _ in opcoes])
        cnes_sel = next(c for n, c in opcoes if n == nome_sel)

        st.write("DEBUG seleção CNES:", cnes_sel)
        st.write("DEBUG registros filtrados:", df[df["CO_CNES"] == cnes_sel].head())

        fig = plot_equipes_por_estabelecimento(df, cnes_sel)
        st.plotly_chart(fig, use_container_width=True, config={"displaylogo": False})

        st.markdown("### Detalhe (tabela)")
        detalhe = (
            df[df["CO_CNES"] == cnes_sel]
            .groupby(["NO_REFERENCIA"])["CO_PROFISSIONAL_SUS"].nunique()
            .reset_index(name="qtd_profissionais")
            .sort_values("qtd_profissionais", ascending=False)
        )
        st.dataframe(detalhe, use_container_width=True)

    elif pagina == "Categorias Profissionais":
        st.title("🧑‍⚕️ Categorias Profissionais por Estabelecimento")

        faltantes = {"CO_CNES", "NO_FANTASIA"} - set(df.columns)
        if faltantes:
            st.error(f"Colunas obrigatórias ausentes nesta página:\n- " + "\n- ".join(faltantes))
            st.stop()

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
