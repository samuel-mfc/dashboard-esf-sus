import streamlit as st
import pandas as pd
import plotly.express as px

# ------------------------------
# CONFIGURAÇÃO DA PÁGINA
# ------------------------------
st.set_page_config(
    page_title="Dashboard de Atendimentos Médicos",
    layout="wide"
)

st.title("📊 Dashboard de Atendimentos Médicos")
st.markdown("Este painel permite a visualização dos atendimentos por profissional, por unidade e ao longo do tempo.")

# ------------------------------
# CARREGAR DADOS
# ------------------------------
@st.cache_data
def carregar_dados(uploaded_file):
    if uploaded_file is not None:
        df = pd.read_csv(uploaded_file, parse_dates=['data_atendimento'])
        return df
    else:
        return None

uploaded_file = st.sidebar.file_uploader("📁 Faça upload do arquivo CSV", type=["csv"])

df = carregar_dados(uploaded_file)

if df is None:
    st.warning("Por favor, envie o arquivo `atendimentos.csv` para continuar.")
    st.stop()

# Garante que colunas necessárias existam
if 'Ano' not in df.columns:
    df['Ano'] = df['data_atendimento'].dt.year

# ------------------------------
# SIDEBAR – FILTROS
# ------------------------------
st.sidebar.header("Filtros")

anos = st.sidebar.multiselect(
    "Ano do Atendimento:",
    options=sorted(df['Ano'].unique()),
    default=sorted(df['Ano'].unique())
)

unidades = st.sidebar.multiselect(
    "Estabelecimento:",
    options=sorted(df['nome_estab'].unique()),
    default=sorted(df['nome_estab'].unique())
)

profissionais = st.sidebar.multiselect(
    "Profissional:",
    options=sorted(df['nome_profissional'].unique()),
    default=sorted(df['nome_profissional'].unique())
)

# Filtro por intervalo de datas
data_min = df['data_atendimento'].min()
data_max = df['data_atendimento'].max()

periodo = st.sidebar.date_input(
    "Período do Atendimento:",
    value=(data_min, data_max),
    min_value=data_min,
    max_value=data_max
)

# ------------------------------
# FILTRAR DATAFRAME
# ------------------------------
df_filtrado = df[
    (df['Ano'].isin(anos)) &
    (df['nome_estab'].isin(unidades)) &
    (df['nome_profissional'].isin(profissionais)) &
    (df['data_atendimento'] >= pd.to_datetime(periodo[0])) &
    (df['data_atendimento'] <= pd.to_datetime(periodo[1]))
]

# ------------------------------
# GRÁFICO 1: Atendimentos por Profissional
# ------------------------------
atendimentos_prof = (
    df_filtrado['nome_profissional']
    .value_counts()
    .reset_index()
    .rename(columns={'index': 'Profissional', 'nome_profissional': 'Atendimentos'})
)

if not atendimentos_prof.empty:
    fig_prof = px.bar(
        atendimentos_prof,
        x='Atendimentos',
        y='Profissional',
        orientation='h',
        title='Atendimentos por Profissional'
    )
    st.plotly_chart(fig_prof, use_container_width=True)
else:
    st.warning("Nenhum atendimento encontrado para os filtros selecionados (Profissional).")

# ------------------------------
# GRÁFICO 2: Atendimentos por Unidade
# ------------------------------
atendimentos_estab = (
    df_filtrado['nome_estab']
    .value_counts()
    .reset_index()
    .rename(columns={'index': 'Unidade', 'nome_estab': 'Atendimentos'})
)

if not atendimentos_estab.empty:
    fig_estab = px.bar(
        atendimentos_estab,
        x='Atendimentos',
        y='Unidade',
        orientation='h',
        title='Atendimentos por Unidade'
    )
    st.plotly_chart(fig_estab, use_container_width=True)
else:
    st.warning("Nenhum atendimento encontrado para os filtros selecionados (Unidade).")

# ------------------------------
# GRÁFICO 3: Evolução Temporal
# ------------------------------
df_temp = df_filtrado.copy()
df_temp['MesAno'] = df_temp['data_atendimento'].dt.to_period('M').astype(str)

evolucao = (
    df_temp.groupby('MesAno')
    .size()
    .reset_index(name='Atendimentos')
)

if not evolucao.empty:
    fig_tempo = px.line(
        evolucao,
        x='MesAno',
        y='Atendimentos',
        title='Evolução dos Atendimentos ao Longo do Tempo',
        markers=True
    )
    fig_tempo.update_xaxes(type='category')
    st.plotly_chart(fig_tempo, use_container_width=True)
else:
    st.warning("Nenhum atendimento encontrado no período selecionado.")
