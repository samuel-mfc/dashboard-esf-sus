import pandas as pd
import streamlit as st
import plotly.graph_objects as go

st.set_page_config(layout="wide")
st.title("Evolução do Tempo de Espera por Mês")
st.caption("Selecione especialidades e unidades para visualizar as tendências de espera ao longo do tempo")

# 📥 Upload do arquivo
uploaded_file = st.file_uploader("Faça o upload da base de solicitações médicas (.csv ou .xlsx)", type=["csv", "xlsx"])

if uploaded_file:
    # 🧹 Leitura do arquivo
    if uploaded_file.name.endswith('.csv'):
        df = pd.read_csv(uploaded_file)
    else:
        df = pd.read_excel(uploaded_file)

    # ✅ Verificações básicas
    colunas_necessarias = {'data_solicitacao', 'tempo_espera_dias', 'Especialidade', 'Unidade Solicitante'}
    if not colunas_necessarias.issubset(df.columns):
        st.error(f"⚠️ O arquivo deve conter as colunas: {colunas_necessarias}")
    else:
        # 📆 Converter para Mês/Ano
        df['MesAno'] = pd.to_datetime(df['data_solicitacao']).dt.to_period('M').astype(str)

        # 🧮 Filtros interativos
        especialidades = df['Especialidade'].dropna().unique()
        unidades = df['Unidade Solicitante'].dropna().unique()

        col1, col2 = st.columns(2)
        especialidades_selecionadas = col1.multiselect("Filtrar por Especialidade", options=sorted(especialidades), default=list(especialidades))
        unidades_selecionadas = col2.multiselect("Filtrar por Unidade Solicitante", options=sorted(unidades), default=list(unidades))

        # 🎯 Aplicar filtros
        df_filtrado = df[
            df['Especialidade'].isin(especialidades_selecionadas) &
            df['Unidade Solicitante'].isin(unidades_selecionadas)
        ]

        if df_filtrado.empty:
            st.warning("Nenhum dado encontrado para os filtros selecionados.")
        else:
            # 📊 Agregação
            agrupado = df_filtrado.groupby('MesAno')['tempo_espera_dias'].agg(
                mediana='median',
                q1=lambda x: x.quantile(0.25),
                q3=lambda x: x.quantile(0.75)
            ).reset_index()

            # 📈 Gráfico
            fig = go.Figure()

            # 3º Quartil
            fig.add_trace(go.Scatter(
                x=agrupado['MesAno'],
                y=agrupado['q3'],
                mode='lines',
                name='3º Quartil',
                line=dict(dash='dot', color='rgba(255, 160, 160, 0.3)'),
            ))
            
            # Faixa entre 1º e 3º Quartil (área preenchida)
            fig.add_trace(go.Scatter(
                x=pd.concat([agrupado['MesAno'], agrupado['MesAno'][::-1]]),
                y=pd.concat([agrupado['q1'], agrupado['q3'][::-1]]),
                fill='toself',
                fillcolor='rgba(173,216,230,0.3)',
                line=dict(color='rgba(255,255,255,0)'),
                hoverinfo="skip",
                showlegend=False,
                name='Faixa entre Quartis'
            ))
            
            # Mediana
            fig.add_trace(go.Scatter(
                x=agrupado['MesAno'],
                y=agrupado['mediana'],
                mode='lines+markers',
                name='Mediana',
                line=dict(color='blue')
            ))
            
            # 1º Quartil
            fig.add_trace(go.Scatter(
                x=agrupado['MesAno'],
                y=agrupado['q1'],
                mode='lines',
                name='1º Quartil',
                line=dict(dash='dot', color='rgba(144, 238, 144, 0.3)'),
            ))
            
            # 🔧 Garantir que todos os meses apareçam no eixo X
            meses_ordenados = sorted(agrupado['MesAno'].unique())
            
            fig.update_layout(
                title="Tempo de Espera (dias) por Mês",
                xaxis_title="Mês/Ano",
                yaxis_title="Tempo de Espera (dias)",
                hovermode="x unified",
                template="plotly_white",
                xaxis=dict(
                    type='category',
                    categoryorder='array',
                    categoryarray=meses_ordenados,
                    tickangle=0  # você pode mudar para -45 se quiser inclinar os meses
                )
            )
