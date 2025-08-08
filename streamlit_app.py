import streamlit as st
from supabase import create_client
import pandas as pd
import plotly.express as px
from datetime import datetime

# Configurações Supabase
SUPABASE_URL = "https://ptjtlkjlzrrytciluokh.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InB0anRsa2psenJyeXRjaWx1b2toIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTQ1MDU2ODksImV4cCI6MjA3MDA4MTY4OX0.lb85vyHSHEVZ5HBNjIOgKcDwQ9lO7-YLuQ7xyt4ncOQ"

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

@st.cache_data(ttl=600)
def get_table(table_name):
    response = supabase.table(table_name).select("*").execute()
    if response.error:
        st.error(f"Erro ao buscar dados da tabela {table_name}: {response.error.message}")
        return pd.DataFrame()
    return pd.DataFrame(response.data)

# Carregar dados
df_upcross = get_table("up_crossell")
df_metas = get_table("metas")
df_churn = get_table("churn")
df_bd_lt = get_table("bd_lt")

# Configurações página
st.set_page_config(page_title="Dashboard de Monetização – V4 Company", layout="wide")

# Cabeçalho
col1, col2 = st.columns([1,6])
with col1:
    st.image("https://v4company.com.br/wp-content/uploads/2020/05/logo_v4company_header.svg", width=120)
with col2:
    st.title("Dashboard de Monetização – V4 Company")
    last_update = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    st.write(f"Última atualização: {last_update}")

st.markdown("---")

# Preparar dados Up & Crossell (filtrar ganhos)
if not df_upcross.empty:
    df_upcross["data oportunidade"] = pd.to_datetime(df_upcross["data oportunidade"], errors='coerce')
    df_upcross["receita recorrente"] = pd.to_numeric(df_upcross["receita recorrente"], errors='coerce').fillna(0)
    df_upcross["receita one-time"] = pd.to_numeric(df_upcross["receita one-time"], errors='coerce').fillna(0)
    df_upcross["receita variável"] = pd.to_numeric(df_upcross["receita variável"], errors='coerce').fillna(0)
    df_upcross["receita total"] = pd.to_numeric(df_upcross["receita total"], errors='coerce').fillna(0)
    df_upcross["situação"] = df_upcross["situação"].str.lower()
else:
    st.warning("Tabela up_crossell vazia ou não carregada.")

df_ganho = df_upcross[df_upcross["situação"].isin(["fechado", "ganho"])]

# Último mês com dados
ultimo_mes = df_ganho["data oportunidade"].max().to_period("M") if not df_ganho.empty else None

# KPIs
df_mes_atual = df_ganho[df_ganho["data oportunidade"].dt.to_period("M") == ultimo_mes] if ultimo_mes else pd.DataFrame()
receita_mes_atual = df_mes_atual["receita total"].sum() if not df_mes_atual.empty else 0

df_metas["mês assinatura"] = pd.to_datetime(df_metas["mês assinatura"], errors='coerce')
meta_mes = df_metas[df_metas["mês assinatura"].dt.to_period("M") == ultimo_mes]["meta total"].sum() if ultimo_mes else 0

perc_meta_batida = (receita_mes_atual / meta_mes * 100) if meta_mes > 0 else 0

df_churn["mês assinatura"] = pd.to_datetime(df_churn["mês assinatura"], errors='coerce')
churn_mes = df_churn[df_churn["mês assinatura"].dt.to_period("M") == ultimo_mes]["churn recorrente"].sum() if ultimo_mes else 0

receita_liquida = receita_mes_atual - churn_mes

qtd_ganhas = len(df_mes_atual)
ticket_medio = receita_mes_atual / qtd_ganhas if qtd_ganhas > 0 else 0

oportunidades_ganhas = qtd_ganhas

mes_anterior = (ultimo_mes - 1) if ultimo_mes else None
df_mes_anterior = df_ganho[df_ganho["data oportunidade"].dt.to_period("M") == mes_anterior] if mes_anterior else pd.DataFrame()
receita_mes_anterior = df_mes_anterior["receita total"].sum() if not df_mes_anterior.empty else 1

nrr = receita_liquida / receita_mes_anterior * 100 if receita_mes_anterior > 0 else 0

# KPIs - grid 4x2
st.subheader("Visão Geral - KPIs")
kpi1, kpi2, kpi3, kpi4 = st.columns(4)
kpi5, kpi6, kpi7, kpi8 = st.columns(4)

kpi1.metric(label="Receita Mês Atual", value=f"R$ {receita_mes_atual:,.2f}")
kpi2.metric(label="Meta do Mês", value=f"R$ {meta_mes:,.2f}", delta=f"{perc_meta_batida:.2f}%")
kpi3.progress(min(perc_meta_batida/100, 1.0))
kpi4.metric(label="Receita Líquida", value=f"R$ {receita_liquida:,.2f}", delta=f"R$ {(receita_liquida - receita_mes_anterior):,.2f}")
kpi5.metric(label="Churn do Mês", value=f"R$ {churn_mes:,.2f}")
kpi6.metric(label="Ticket Médio", value=f"R$ {ticket_medio:,.2f}")
kpi7.metric(label="Oportunidades Ganhas", value=oportunidades_ganhas)
kpi8.metric(label="NRR (%)", value=f"{nrr:.2f}%")

st.markdown("---")

# Receita ao longo do tempo
st.subheader("Receita ao longo do tempo")

df_ganho["mes"] = df_ganho["data oportunidade"].dt.to_period("M").dt.to_timestamp()
receita_por_mes = df_ganho.groupby("mes")[["receita recorrente", "receita one-time"]].sum().reset_index()
receita_por_mes["receita total"] = receita_por_mes["receita recorrente"] + receita_por_mes["receita one-time"]

fig_area = px.area(receita_por_mes, x="mes", y=["receita recorrente", "receita one-time"],
                   labels={"mes": "Mês", "value": "Receita (R$)", "variable": "Tipo de Receita"},
                   title="Receita Recorrente vs One-time por Mês",
                   color_discrete_map={"receita recorrente": "green", "receita one-time": "gray"})
st.plotly_chart(fig_area, use_container_width=True)

df_metas_agg = df_metas.groupby(pd.Grouper(key="mês assinatura", freq="M"))["meta total"].sum().reset_index()

fig_linha = px.line(receita_por_mes, x="mes", y="receita total", title="Receita Total x Meta por Mês")
fig_linha.add_scatter(x=df_metas_agg["mês assinatura"], y=df_metas_agg["meta total"], mode="lines+markers", name="Meta", line=dict(dash="dash"))
st.plotly_chart(fig_linha, use_container_width=True)

st.subheader("Receita por Squad")
receita_squad = df_ganho.groupby("squad")["receita total"].sum().reset_index().sort_values("receita total", ascending=False)
fig_squad = px.bar(receita_squad, x="squad", y="receita total", labels={"squad": "Squad", "receita total": "Receita (R$)"},
                   title="Receita Total por Squad", color="receita total", color_continuous_scale="Greens")
st.plotly_chart(fig_squad, use_container_width=True)
