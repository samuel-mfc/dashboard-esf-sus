# app.py — Dashboard ESF SUS (produção, resolutividade e KPIs)
# Autor: ChatGPT (GPT-5 Thinking) — Protótipo para equipes de ESF
# ---------------------------------------------------------------
# Como usar:
# 1) Instale dependências:  pip install streamlit pandas numpy plotly
# 2) Rode local:             streamlit run app.py
# 3) Para publicar:          https://docs.streamlit.io/streamlit-community-cloud/deploy
#
# IMPORTANTE: Você pode carregar dados reais (CSV/Parquet) com o botão na barra lateral.
#             O protótipo também gera dados de exemplo para demonstração.

from __future__ import annotations
import os
import io
import uuid
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from datetime import datetime, timedelta

# -----------------------------
# Configurações do app
# -----------------------------
st.set_page_config(
    page_title="ESF — Produção, Resolutividade e KPIs",
    layout="wide",
    page_icon="🩺",
)

# Paleta e estilo rápido
PRIMARY = "#0ea5e9"  # azul-ciano
ACCENT = "#10b981"   # verde
DANGER = "#ef4444"   # vermelho
MUTED = "#64748b"    # cinza

# -----------------------------
# Utilidades
# -----------------------------
@st.cache_data(show_spinner=False)
def gerar_dados_exemplo(n_meses: int = 12, seed: int = 42) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Gera dados simulados de produção ESF e uma tabela de população adscrita por Unidade."""
    rng = np.random.default_rng(seed)

    # Entidades básicas
    unidades = [f"UBS {c}" for c in list("ABCDE")]  # 5 unidades
    equipes = [f"ESF {i:02d}" for i in range(1, 11)]  # 10 equipes
    medicos = [
        {"medico_id": i, "medico_nome": f"Dr(a). {nome}", "equipe": rng.choice(equipes), "unidade": rng.choice(unidades)}
        for i, nome in enumerate([
            "Ana", "Bruno", "Carla", "Diego", "Elaine", "Fabio", "Gabriela", "Henrique", "Iara", "João",
            "Karen", "Luis", "Mariana", "Nicolas", "Olivia"
        ], start=1)
    ]
    medicos_df = pd.DataFrame(medicos)

    # População adscrita por unidade (para normalização: consultas por 1000 hab)
    pop = pd.DataFrame({
        "unidade": unidades,
        "pop_adscrita": rng.integers(8000, 18000, size=len(unidades))
    })

    # Datas: últimos n_meses
    hoje = pd.Timestamp.today().normalize()
    inicio = (hoje - pd.DateOffset(months=n_meses-1)).replace(day=1)
    datas = pd.date_range(inicio, hoje, freq="D")

    # Dicionários de valores
    sexos = ["F", "M"]
    faixas = ["0-5", "6-17", "18-39", "40-59", "60+"]
    condicoes = ["Nenhuma", "HAS", "DM", "DPOC/Asma", "Gestante"]
    tipos = ["Consulta", "Visita domiciliar", "Procedimento", "Urgência"]

    procedimentos = [
        ("0301010030", "Consulta clínica em APS"),
        ("0301010049", "Retorno em APS"),
        ("0202010034", "Coleta exame laboratório"),
        ("0205010038", "Curativo simples"),
        ("0202030068", "Eletrocardiograma"),
    ]

    registros = []
    atendimento_id_seq = 1
    for _ in range(6000):  # n de linhas
        d = rng.choice(datas)
        m = medicos_df.sample(1, random_state=int(rng.integers(0, 1e9))).iloc[0]

        sexo = rng.choice(sexos, p=[0.55, 0.45])
        faixa = rng.choice(faixas, p=[0.08, 0.16, 0.38, 0.24, 0.14])
        cond = rng.choice(condicoes, p=[0.52, 0.22, 0.16, 0.07, 0.03])
        tipo = rng.choice(tipos, p=[0.70, 0.12, 0.10, 0.08])
        proc = procedimentos[0] if tipo in ("Consulta", "Urgência") else rng.choice(procedimentos[1:])
        sigtap, proc_desc = proc

        # Encaminhamento e desfecho
        encaminhado = bool(rng.random() < 0.18)  # ~18% encaminha
        desfecho = (
            "Resolvido na APS" if not encaminhado and rng.random() < 0.75 else
            ("Acompanhamento APS" if not encaminhado else "Encaminhado")
        )

        # Exames e tempo de espera
        exames = int(max(0, rng.poisson(0.9 if tipo=="Consulta" else 0.3)))
        tempo_espera = max(0, int(rng.normal(6, 3)))  # dias

        registros.append({
            "atendimento_id": atendimento_id_seq,
            "data_atendimento": pd.Timestamp(d),
            "medico_id": m.medico_id,
            "medico_nome": m.medico_nome,
            "equipe": m.equipe,
            "unidade": m.unidade,
            "paciente_id": int(rng.integers(100000, 999999)),
            "sexo": sexo,
            "faixa_etaria": faixa,
            "condicao_cronica": cond,
            "tipo_atendimento": tipo,
            "procedimento_sigtap": sigtap,
            "procedimento_desc": proc_desc,
            "encaminhado": encaminhado,
            "desfecho": desfecho,
            "exames_solicitados": exames,
            "tempo_espera_dias": tempo_espera,
        })
        atendimento_id_seq += 1

    df = pd.DataFrame(registros)

    # Ordenadores auxiliares
    df["dia"] = df["data_atendimento"].dt.date
    df["mes"] = df["data_atendimento"].dt.to_period("M").dt.to_timestamp()
    return df, pop


def kpi_cards(col, label: str, value, help_txt: str | None = None, delta: str | None = None):
    """Pequeno atalho para mostrar KPI como card."""
    col.markdown(
        f"""
        <div style='border:1px solid #e5e7eb;border-radius:16px;padding:16px;'>
            <div style='font-size:12px;color:{MUTED}'>{label}</div>
            <div style='font-size:28px;font-weight:700;'>{value}</div>
            {f"<div style='font-size:12px;color:{MUTED};margin-top:6px;'>{help_txt}</div>" if help_txt else ''}
            {f"<div style='font-size:12px;color:{ACCENT};margin-top:6px;'>Δ {delta}</div>" if delta else ''}
        </div>
        """,
        unsafe_allow_html=True,
    )


def calcular_indicadores(df: pd.DataFrame, pop_adscrita: pd.DataFrame | None = None) -> dict:
    total_at = int(df.shape[0])
    consultas = int((df["tipo_atendimento"] == "Consulta").sum())
    visitas = int((df["tipo_atendimento"] == "Visita domiciliar").sum())

    # Encaminhamentos e resolutividade
    taxa_enc = float((df["encaminhado"].mean() * 100) if len(df) else 0.0)

    # "Resolutividade" aqui = % de desfechos concluídos na APS (Resolvido ou Acompanhamento) sem encaminhar
    resolutivo = df[(df["encaminhado"] == False) & (df["desfecho"].isin(["Resolvido na APS", "Acompanhamento APS"]))]
    taxa_res = float((len(resolutivo) / len(df) * 100) if len(df) else 0.0)

    # Exames por consulta
    exames_por_cons = float((df.loc[df["tipo_atendimento"] == "Consulta", "exames_solicitados"].mean()) if consultas else 0.0)

    # Tempo médio de espera
    tmed = float(df["tempo_espera_dias"].mean()) if len(df) else 0.0

    # Consultas por 1000 hab (normalizado por unidade)
    if pop_adscrita is not None and not pop_adscrita.empty:
        por_unidade = (
            df[df["tipo_atendimento"] == "Consulta"]["unidade"].value_counts().rename_axis("unidade").reset_index(name="consultas")
            .merge(pop_adscrita, on="unidade", how="left")
        )
        por_unidade["cons_por_1000"] = por_unidade["consultas"] / por_unidade["pop_adscrita"] * 1000
        cons_1000 = float(por_unidade["cons_por_1000"].mean()) if len(por_unidade) else 0.0
    else:
        cons_1000 = np.nan

    return {
        "total_atendimentos": total_at,
        "consultas": consultas,
        "visitas": visitas,
        "taxa_encaminhamento": taxa_enc,
        "taxa_resolutividade": taxa_res,
        "exames_por_consulta": exames_por_cons,
        "tempo_medio_espera": tmed,
        "consultas_por_1000": cons_1000,
    }


def plot_linhas_producao(df: pd.DataFrame):
    base = df.groupby(["mes", "tipo_atendimento"], as_index=False).size()
    fig = px.line(
        base, x="mes", y="size", color="tipo_atendimento",
        markers=True,
        labels={"mes": "Mês", "size": "Atendimentos", "tipo_atendimento": "Tipo"},
        title="Evolução mensal de produção",
    )
    fig.update_layout(legend_title_text="Tipo de atendimento", hovermode="x unified", margin=dict(t=60, b=20, l=20, r=20))
    return fig


def plot_ranking_medicos(df: pd.DataFrame, top_n: int = 15):
    base = df[df["tipo_atendimento"] == "Consulta"].groupby("medico_nome", as_index=False).size()
    base = base.sort_values("size", ascending=False).head(top_n)
    fig = px.bar(
        base, x="size", y="medico_nome", orientation="h",
        labels={"size": "Consultas", "medico_nome": "Médico(a)"},
        title=f"Top {top_n} — Consultas por médico(a)",
    )
    fig.update_layout(margin=dict(t=60, b=20, l=20, r=20))
    return fig


def plot_desfechos(df: pd.DataFrame):
    base = df["desfecho"].value_counts().rename_axis("desfecho").reset_index(name="qtde")
    fig = px.pie(base, names="desfecho", values="qtde", title="Distribuição de desfechos")
    fig.update_traces(textposition="inside", textinfo="percent+label")
    fig.update_layout(margin=dict(t=60, b=20, l=20, r=20))
    return fig


def plot_funil_resolutividade(df: pd.DataFrame):
    # Estágios simples de funil (exemplo): Consultas -> Sem encaminhamento -> Resolvidos/Acompanhamento
    total_cons = int((df["tipo_atendimento"] == "Consulta").sum())
    sem_enc = int(((df["tipo_atendimento"] == "Consulta") & (~df["encaminhado"])).sum())
    resolvidos = int(((df["tipo_atendimento"] == "Consulta") & (~df["encaminhado"]) & (df["desfecho"].isin(["Resolvido na APS", "Acompanhamento APS"])) ).sum())

    stages = ["Consultas", "Sem encaminhamento", "Resolvidos/Acompanhamento"]
    values = [total_cons, sem_enc, resolvidos]

    fig = go.Figure(go.Funnel(y=stages, x=values, textinfo="value+percent initial"))
    fig.update_layout(title="Funil de resolutividade (consultas)", margin=dict(t=60, b=20, l=20, r=20))
    return fig


def filtros_sidebar(df: pd.DataFrame, pop_df: pd.DataFrame) -> pd.DataFrame:
    st.sidebar.header("⚙️ Filtros")

    # Intervalo de datas
    min_d, max_d = df["data_atendimento"].min().date(), df["data_atendimento"].max().date()
    dt_ini, dt_fim = st.sidebar.date_input(
        "Período",
        value=(min_d, max_d),
        min_value=min_d,
        max_value=max_d,
    )

    # Multiselects
    unidades = ["(Todas)"] + sorted(df["unidade"].unique().tolist())
    equipes = ["(Todas)"] + sorted(df["equipe"].unique().tolist())
    medicos = ["(Todos)"] + sorted(df["medico_nome"].unique().tolist())
    conds = ["(Todas)"] + sorted(df["condicao_cronica"].unique().tolist())

    sel_unid = st.sidebar.multiselect("Unidade (UBS)", unidades, default=["(Todas)"])
    sel_eqp = st.sidebar.multiselect("Equipe (ESF)", equipes, default=["(Todas)"])
    sel_med = st.sidebar.multiselect("Médico(a)", medicos, default=["(Todos)"])
    sel_cond = st.sidebar.multiselect("Condição crônica", conds, default=["(Todas)"])

    # Dados próprios
    if st.sidebar.checkbox("Carregar dados reais (CSV/Parquet)"):
        up = st.sidebar.file_uploader("Selecione seu arquivo", type=["csv", "parquet"])
        if up is not None:
            try:
                if up.name.lower().endswith(".csv"):
                    real = pd.read_csv(up, encoding="utf-8")
                else:
                    real = pd.read_parquet(up)
                # Espera colunas compatíveis; se necessário, mapeie aqui
                # Campos esperados mínimos: data_atendimento, medico_nome, equipe, unidade, tipo_atendimento,
                # encaminhado (bool), desfecho (texto), exames_solicitados (int), tempo_espera_dias (int)
                # Opcional: condicao_cronica, sexo, faixa_etaria
                real["data_atendimento"] = pd.to_datetime(real["data_atendimento"]).dt.tz_localize(None)
                real["dia"] = real["data_atendimento"].dt.date
                real["mes"] = real["data_atendimento"].dt.to_period("M").dt.to_timestamp()
                df = real
            except Exception as e:
                st.sidebar.error(f"Falha ao ler o arquivo: {e}")

    # Aplicar filtros
    mask = (
    (df["dia"] >= dt_ini) &
    (df["dia"] <= dt_fim)
)

    if sel_unid and "(Todas)" not in sel_unid:
        mask &= df["unidade"].isin(sel_unid)
    if sel_eqp and "(Todas)" not in sel_eqp:
        mask &= df["equipe"].isin(sel_eqp)
    if sel_med and "(Todos)" not in sel_med:
        mask &= df["medico_nome"].isin(sel_med)
    if sel_cond and "(Todas)" not in sel_cond:
        mask &= df["condicao_cronica"].isin(sel_cond)

    st.sidebar.markdown("---")
    st.sidebar.subheader("📦 População adscrita (opcional)")
    st.sidebar.caption("Use para normalizar consultas/1000 habitantes por unidade")
    pop_up = st.sidebar.file_uploader("População por unidade (CSV com colunas: unidade, pop_adscrita)", type=["csv"], key="pop")
    if pop_up is not None:
        try:
            pop_df = pd.read_csv(pop_up)
        except Exception as e:
            st.sidebar.error(f"Falha ao ler população: {e}")

    df_filt = df.loc[mask].copy()
    return df_filt, pop_df


def tabela_resumo_medicos(df: pd.DataFrame) -> pd.DataFrame:
    """Resumo por médico com produção, % encaminhamento, resolutividade, exames/consulta, TME."""
    if df.empty:
        return pd.DataFrame()

    grp = df.groupby("medico_nome")
    out = pd.DataFrame({
        "Médico(a)": grp.size(),
        "Consultas": grp.apply(lambda g: (g["tipo_atendimento"] == "Consulta").sum()),
        "% Encaminhamento": grp["encaminhado"].mean() * 100,
        "Exames/Consulta": grp.apply(lambda g: g.loc[g["tipo_atendimento"]=="Consulta", "exames_solicitados"].mean()),
        "TME (dias)": grp["tempo_espera_dias"].mean(),
        "Resolutividade %": grp.apply(lambda g: ( ((~g["encaminhado"]) & g["desfecho"].isin(["Resolvido na APS", "Acompanhamento APS"])) .sum() / len(g) * 100 ) if len(g) else np.nan),
    }).reset_index().rename(columns={"medico_nome": "Médico(a)", 0: "Atendimentos"})

    out = out.rename(columns={"Médico(a)": "Médico(a)", "Médico(a)": "Médico(a)"})
    out = out.sort_values("Consultas", ascending=False)
    return out


# -----------------------------
# App
# -----------------------------
st.title("🩺 Dashboard — ESF (SUS)")
st.caption("Produção, resolutividade e KPIs por médico, equipe e unidade")

with st.expander("ℹ️ Sobre o protótipo e esquema de dados", expanded=False):
    st.markdown(
        """
        **Esquema mínimo esperado (colunas):**  
        `data_atendimento (datetime)` · `medico_nome` · `equipe` · `unidade` · `tipo_atendimento` · `encaminhado (bool)` · `desfecho (str)` · `exames_solicitados (int)` · `tempo_espera_dias (int)`  
        **Opcionais:** `condicao_cronica` · `sexo` · `faixa_etaria` · `procedimento_sigtap` · `procedimento_desc` · `paciente_id`

        Use a barra lateral para **filtrar por período, unidade, equipe, médico e condição crônica** e para **carregar dados reais**.
        """
    )

# Dados base (exemplo) + população adscrita
base_df, pop_df = gerar_dados_exemplo(n_meses=12, seed=2025)

# Filtros
filt_df, pop_df = filtros_sidebar(base_df, pop_df)

# KPIs principais
ind = calcular_indicadores(filt_df, pop_df)

c1, c2, c3, c4, c5, c6 = st.columns(6)
kpi_cards(c1, "Atendimentos", f"{ind['total_atendimentos']:,}".replace(",", "."), "Total no período filtrado")
kpi_cards(c2, "Consultas", f"{ind['consultas']:,}".replace(",", "."), "Somente tipo 'Consulta'")
kpi_cards(c3, "Resolutividade (%)", f"{ind['taxa_resolutividade']:.1f}%", "Fechados na APS sem encaminhar")
kpi_cards(c4, "Encaminhamentos (%)", f"{ind['taxa_encaminhamento']:.1f}%", "Proporção de casos encaminhados")
kpi_cards(c5, "Exames/Consulta", f"{ind['exames_por_consulta']:.2f}", "Média de exames por consulta")
val_c1000 = "—" if pd.isna(ind["consultas_por_1000"]) else f"{ind['consultas_por_1000']:.1f}"
kpi_cards(c6, "Consultas/1000 hab.", val_c1000, "Normalizado por unidade (se população fornecida)")

st.markdown("---")

# Linhas de produção (mensal)
colA, colB = st.columns((2, 1))
with colA:
    st.plotly_chart(plot_linhas_producao(filt_df), use_container_width=True)
with colB:
    st.plotly_chart(plot_desfechos(filt_df), use_container_width=True)

st.plotly_chart(plot_funil_resolutividade(filt_df), use_container_width=True)

# Ranking médicos
st.plotly_chart(plot_ranking_medicos(filt_df, top_n=15), use_container_width=True)

# Tabela resumo por médico
st.subheader("📋 Resumo por médico(a)")
sum_med = tabela_resumo_medicos(filt_df)
st.dataframe(sum_med, use_container_width=True)

# Download dos dados filtrados
st.markdown("### ⬇️ Exportar dados filtrados")
@st.cache_data(show_spinner=False)
def to_csv_bytes(df: pd.DataFrame):
    return df.to_csv(index=False).encode("utf-8")

csv_bytes = to_csv_bytes(filt_df)
st.download_button(
    label="Baixar CSV (dados filtrados)",
    data=csv_bytes,
    file_name="esf_dados_filtrados.csv",
    mime="text/csv",
)

# Observações finais
st.markdown(
    f"""
    <div style='margin-top:18px;color:{MUTED};font-size:12px;'>
    *Este é um protótipo com dados simulados. Ajuste as definições de <b>resolutividade</b> e <b>encaminhamento</b> conforme seu protocolo local.*<br>
    Sugerimos conectar à sua base (e-SUS/PEC, Regulação, SISAB/SIGTAP) e criar um agendamento de atualização.
    </div>
    """,
    unsafe_allow_html=True,
)
