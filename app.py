
import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px

st.set_page_config(page_title="Dashboard ESF SUS", layout="wide", page_icon="🩺")

st.title("🩺 Dashboard — ESF (SUS)")
st.caption("Produção, resolutividade e KPIs")

# Dados de exemplo
np.random.seed(42)
meses = pd.date_range("2024-01-01", periods=12, freq="M")
consultas = np.random.randint(300, 600, size=12)
encaminhamentos = np.random.randint(40, 120, size=12)

df = pd.DataFrame({"Mês": meses, "Consultas": consultas, "Encaminhamentos": encaminhamentos})

# KPIs
col1, col2 = st.columns(2)
col1.metric("Consultas totais", f"{df['Consultas'].sum():,}".replace(",", "."))
col2.metric("Taxa de encaminhamento", f"{(df['Encaminhamentos'].sum() / df['Consultas'].sum() * 100):.1f}%")

# Gráfico
fig = px.line(df, x="Mês", y=["Consultas", "Encaminhamentos"], markers=True, title="Evolução mensal")
st.plotly_chart(fig, use_container_width=True)

st.dataframe(df, use_container_width=True)
