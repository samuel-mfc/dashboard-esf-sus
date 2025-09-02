import io
import pandas as pd
import numpy as np
import streamlit as st
import plotly.express as px

# -------------- Config básica --------------
st.set_page_config(page_title="Dashboard de Atendimentos", layout="wide")
st.title("📊 Dashboard de Atendimentos Médicos")

st.markdown(
    """
    **Colunas esperadas:**
    - `nome_profissional` (nome do profissional)  
    - `nome_estab` (nome do estabelecimento)  
    - `Ano` (ano de referência, número inteiro)  
    - `data_atendimento` (datetime do atendimento)  
    - `MesAno` (string que representa mês/ano, ex: `jan/2024` ou `01/2024`)  
    """
)

# -------------- Upload do arquivo --------------
uploaded = st.file_uploader("Envie seu arquivo CSV ou Excel", type=["csv", "xlsx"])

@st.cache_data(show_spinner=False)
def load_df(file) -> pd.DataFrame:
    if file.name.lower().endswith(".csv"):
        # Tenta ler com ; e , automaticamente
        data = file.read()
        for sep in [";", ",", "\t", "|"]:
            try:
                df = pd.read_csv(io.BytesIO(data), sep=sep, encoding="utf-8")
                # Se não tem mais de 1 coluna, tenta próxima separação
                if df.shape[1] == 1:
                    continue
                return df
            except Exception:
                continue
        # fallback: tenta sem sep
        file.seek(0)
        return pd.read_csv(io.BytesIO(data))
    else:
        return pd.read_excel(file)  # requer openpyxl para .xlsx

def coerce_datetime(series):
    """Converte qualquer coisa em datetime, se possível."""
    if pd.api.types.is_datetime64_any_dtype(series):
        return series
    # tenta conversões comuns
    dt = pd.to_datetime(series, errors="coerce", dayfirst=True, infer_datetime_format=True)
    return dt

def ensure_types(df: pd.DataFrame) -> pd.DataFrame:
    # Garante colunas esperadas
    required = ["nome_profissional", "nome_estab", "Ano", "data_atendimento", "MesAno"]
    missing = [c for c in required if c not in df.columns]
    if missing:
        st.error(f"As seguintes colunas estão faltando no arquivo: {missing}")
        st.stop()

    # Tipagens
    # Ano
    if not pd.api.types.is_integer_dtype(df["Ano"]):
        df["Ano"] = pd.to_numeric(df["Ano"], errors="coerce").astype("Int64")

    # data_atendimento
    df["data_atendimento"] = coerce_datetime(df["data_atendimento"])

    # cria coluna mensal "mes_ref" (datetime no 1º dia do mês) para ordenar corretamente
    # prioridade: usar data_atendimento; fallback: MesAno
    if df["data_atendimento"].notna().any():
        df["mes_ref"] = df["data_atendimento"].dt.to_period("M").dt.to_timestamp()
    else:
        # tenta parsear MesAno em diferentes formatos
        # exemplos aceitos: "jan/2024", "fev-2024", "01/2024", "2024-01"
        mesano = df["MesAno"].astype(str).str.strip()
        # primeiro tenta direto
        dt = pd.to_datetime(mesano, errors="coerce", dayfirst=True, infer_datetime_format=True)
        # se ainda tiver NaT, tenta mapear abreviações PT->num
        if dt.isna().any():
            mapa_pt = {
                "jan": "01", "fev": "02", "mar": "03", "abr": "04", "mai": "05", "jun": "06",
                "jul": "07", "ago": "08", "set": "09", "out": "10", "nov": "11", "dez": "12",
            }
            temp = mesano.str.lower()
            for k, v in mapa_pt.items():
                temp = temp.str.replace(fr"\b{k}\b", v, regex=True)
            # adiciona dia=01 quando faltar
            temp2 = temp.str.replace(r"^(\d{1,2})[/-](\d{4})$", r"\1/01/\2", regex=True)
            temp2 = temp2.str.replace(r"^(\d{4})-(\d{1,2})$", r"01/\2/\1", regex=True)
            dt2 = pd.to_datetime(temp2, errors="coerce", dayfirst=True, infer_datetime_format=True)
            dt = dt.fillna(dt2)

        df["mes_ref"] = dt.dt.to_period("M").dt.to_timestamp()

    # strings limpas
    df["nome_profissional"] = df["nome_profissional"].astype(str).str.strip()
    df["nome_estab"] = df["nome_estab"].astype(str).str.strip()

    # cria coluna de contagem (1 por atendimento)
    df["atendimentos"] = 1

    return df

if uploaded is None:
    st.info("Envie o arquivo para carregar os dados e habilitar os filtros e gráficos.")
    st.stop()

df_raw = load_df(uploaded)
df = ensure_types(df_raw.copy())

# -------------- Filtros (Sidebar) --------------
st.sidebar.header("Filtros")

anos = sorted([a for a in df["Ano"].dropna().unique() if pd.notna(a)])
anos_sel = st.sidebar.multiselect("Ano de execução", options=anos, default=anos)

# aplique primeiro o filtro de ano para reduzir o universo de seleção
df_year = df[df["Ano"].isin(anos_sel)] if anos_sel else df.copy()

unidades = sorted(df_year["nome_estab"].dropna().unique().tolist())
unid_sel = st.sidebar.multiselect("Unidade (nome_estab)", options=unidades, default=unidades)

medicos = sorted(df_year["nome_profissional"].dropna().unique().tolist())
med_sel = st.sidebar.multiselect("Profissional (nome_profissional)", options=medicos, default=medicos)

# aplica filtros combinados
mask = pd.Series(True, index=df.index)
if anos_sel:
    mask &= df["Ano"].isin(anos_sel)
if unid_sel:
    mask &= df["nome_estab"].isin(unid_sel)
if med_sel:
    mask &= df["nome_profissional"].isin(med_sel)

df_f = df[mask].copy()

if df_f.empty:
    st.warning("Nenhum dado após aplicar os filtros.")
    st.stop()

# -------------- KPIs rápidos --------------
col_a, col_b, col_c = st.columns(3)
with col_a:
    st.metric("Total de atendimentos", int(df_f["atendimentos"].sum()))
with col_b:
    st.metric("Profissionais únicos", df_f["nome_profissional"].nunique())
with col_c:
    st.metric("Unidades únicas", df_f["nome_estab"].nunique())

# -------------- Gráfico 1: Médicos x Nº de atendimentos --------------
grp_med = (
    df_f.groupby("nome_profissional", dropna=False)["atendimentos"]
    .sum()
    .reset_index()
    .sort_values("atendimentos", ascending=True)  # asc para barras horizontais ordenadas
)

fig1 = px.bar(
    grp_med,
    x="atendimentos",
    y="nome_profissional",
    orientation="h",
    title="Atendimentos por Profissional",
    labels={"atendimentos": "Nº de atendimentos", "nome_profissional": "Profissional"},
)
fig1.update_layout(yaxis=dict(automargin=True))

# -------------- Gráfico 2: Unidades x Nº de atendimentos --------------
grp_uni = (
    df_f.groupby("nome_estab", dropna=False)["atendimentos"]
    .sum()
    .reset_index()
    .sort_values("atendimentos", ascending=True)
)

fig2 = px.bar(
    grp_uni,
    x="atendimentos",
    y="nome_estab",
    orientation="h",
    title="Atendimentos por Unidade (Estabelecimento)",
    labels={"atendimentos": "Nº de atendimentos", "nome_estab": "Unidade"},
)
fig2.update_layout(yaxis=dict(automargin=True))

# -------------- Gráfico 3: Linha temporal (mensal) --------------
# Agrega por mês; já filtrado por unidade e profissional via df_f
# Usamos mes_ref para ordenar corretamente
ts = (
    df_f.dropna(subset=["mes_ref"])
       .groupby("mes_ref", as_index=False)["atendimentos"]
       .sum()
       .sort_values("mes_ref")
)

# Opcional: exibir o rótulo "MesAno" bonito
ts["MesAno_fmt"] = ts["mes_ref"].dt.strftime("%b/%Y").str.title()

fig3 = px.line(
    ts,
    x="mes_ref",
    y="atendimentos",
    markers=True,
    title="Série temporal de atendimentos (mensal)",
    labels={"mes_ref": "Mês", "atendimentos": "Nº de atendimentos"},
)
# mostrar também como tooltip a forma legível
fig3.update_traces(hovertemplate="Mês: %{x|%b/%Y}<br>Atendimentos: %{y}<extra></extra>")
fig3.update_layout(xaxis=dict(tickformat="%b/%Y"))

# -------------- Layout dos gráficos --------------
g1, g2 = st.columns(2)
with g1:
    st.plotly_chart(fig1, use_container_width=True)
with g2:
    st.plotly_chart(fig2, use_container_width=True)

st.plotly_chart(fig3, use_container_width=True)

# -------------- Tabela opcional (detalhes) --------------
with st.expander("Ver dados filtrados"):
    st.dataframe(df_f.sort_values("data_atendimento", na_position="last").reset_index(drop=True))
