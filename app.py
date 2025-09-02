pip install streamlit plotly pandas

import streamlit as st
import pandas as pd
import plotly.express as px

# ----------------------
# CARREGAR OS DADOS
# ----------------------
@st.cache_data
def carregar_dados():
    df = pd.read_csv('seu_arquivo.csv', parse_dates=['data_atendimento'])  # ajuste o caminho
    return df

df = carregar_dados()

# ----------------------
# FILTROS
# ----------------------
st.sidebar.title("Filtros")

anos = st.sidebar.multiselect("Selecione o(s) ano(s):", sorted(df['Ano'].unique()), default=sorted(df['Ano'].unique()))
unidades = st.sidebar.multiselect("Selecione o(s) estabelecimento(s):", sorted(df['nome_estab'].unique()), default=sorted(df['nome_estab'].unique()))
profissionais = st.sidebar.multiselect("Selecione o(s) profissional(is):", sorted(df['nome_profissional'].unique()), default=sorted(df['nome_profissional'].unique()))

# Filtro por período (data_atendimento)
data_min = df['data_atendimento'].min()
data_max = df['data_atendimento'].max()
periodo = st.sidebar.date_input("Selecione o período:", [data_min, data_max])

# ----------------------
# APLICAR FILTROS
# ----------------------
df_filtrado = df[
    (df['Ano'].isin(anos)) &
    (df['nome_estab'].isin(unidades)) &
    (df['nome_profissional'].isin(profissionais)) &
    (df['data_atendimento'] >= pd.to_datetime(periodo[0])) &
    (df['data_atendimento'] <= pd.to_datetime(periodo[1]))
]

# ----------------------
# GRÁFICO 1: Atendimentos por Médico
# ----------------------
atendimentos_por_medico = df_filtrado['nome_profissional'].value_counts().reset_index()
atendimentos_por_medico.columns = ['Profissional', 'Atendimentos']

fig1 = px.bar(
    atendimentos_por_medico,
    x='Atendimentos',
    y='Profissional',
    orientation='h',
    title='Atendimentos por Profissional'
)

# ----------------------
# GRÁFICO 2: Atendimentos por Unidade
# ----------------------
atendimentos_por_unidade = df_filtrado['nome_estab'].value_counts().reset_index()
atendimentos_por_unidade.columns = ['Unidade', 'Atendimentos']

fig2 = px.bar(
    atendimentos_por_unidade,
    x='Atendimentos',
    y='Unidade',
    orientation='h',
    title='Atendimentos por Unidade'
)

# ----------------------
# GRÁFICO 3: Evolução Temporal dos Atendimentos
# ----------------------
df_temporal = df_filtrado.copy()
df_temporal['MesAno'] = df_temporal['data_atendimento'].dt.to_period('M').astype(str)

atendimentos_tempo = df_temporal.groupby('MesAno').size().reset_index(name='Atendimentos')

fig3 = px.line(
    atendimentos_tempo,
    x='MesAno',
    y='Atendimentos',
    markers=True,
    title='Evolução dos Atendimentos ao Longo do Tempo'
)
fig3.update_xaxes(type='category')

# ----------------------
# LAYOUT NO STREAMLIT
# ----------------------
st.title("📊 Dashboard de Atendimentos Médicos")

st.plotly_chart(fig1, use_container_width=True)
st.plotly_chart(fig2, use_container_width=True)
st.plotly_chart(fig3, use_container_width=True)
