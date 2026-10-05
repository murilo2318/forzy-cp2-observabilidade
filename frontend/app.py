"""
Forzy - Sensor Monitoring (CP2 integrado GBA + Front-end).
Interface Streamlit que consome a API FastAPI via requests.

Rodar:  streamlit run frontend/app.py
"""

import sys
import uuid
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

sys.path.insert(0, str(Path(__file__).parent))
import api_client as api  # noqa: E402
from servidor_embutido import garantir_api  # noqa: E402

# Paleta semantica das Sprints anteriores
VERDE, AMARELO, VERMELHO, CINZA = "#3FB950", "#D29922", "#F85149", "#8B949E"
COR_ESTADO = {"saudavel": VERDE, "atencao": AMARELO, "critico": VERMELHO, "manutencao": CINZA}
NOME_ESTADO = {"saudavel": "Saudável", "atencao": "Atenção", "critico": "Crítico", "manutencao": "Em manutenção"}
METRICAS = {
    "temp_c": ("Temperatura", "°C"),
    "vibracao_mms": ("Vibração", "mm/s"),
    "corrente_a": ("Corrente", "A"),
    "tensao_v": ("Tensão", "V"),
    "rotacao_rpm": ("Rotação", "RPM"),
}

st.set_page_config(page_title="Forzy · Sensor Monitoring", page_icon="⚙️", layout="wide")

MODO_API = garantir_api(api.API_URL)

if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())
SID = st.session_state.session_id

st.title("Forzy · Sensor Monitoring")
st.caption("Leitura atual, histórico e observabilidade do provider de Sensores, consumidos da API via requests.")

with st.sidebar:
    st.subheader("Contexto da sessão")
    st.text_input("X-Session-Id", SID, disabled=True)
    st.caption(f"API: {api.API_URL} ({MODO_API})")
    try:
        tags = api.listar_tags(SID)
    except api.ApiError as e:
        st.error(str(e))
        st.stop()
    tag = st.selectbox("Equipamento (TAG)", tags)

aba_leitura, aba_hist, aba_obs = st.tabs(["Leitura atual", "Histórico", "Observabilidade"])

# ─── Leitura atual ───────────────────────────────────────────────────────────
with aba_leitura:
    st.button("Atualizar leitura", key="btn_leitura")
    try:
        dados = api.leitura_atual(tag, SID)
    except api.ApiError as e:
        st.error(str(e))
    else:
        estado = dados["estado"]
        cor = COR_ESTADO.get(estado, CINZA)
        st.markdown(
            f"<div style='padding:10px 16px;border-left:6px solid {cor};"
            f"background:{cor}22;border-radius:6px;margin-bottom:12px'>"
            f"<b>{dados['tag']}</b> · Estado: <b style='color:{cor}'>{NOME_ESTADO.get(estado, estado)}</b>"
            f" · Severidade: <b>{dados['severidade']}</b>"
            f" · Leitura de {dados['leitura']['timestamp']}</div>",
            unsafe_allow_html=True,
        )
        cols = st.columns(len(METRICAS))
        for col, (campo, (rotulo, unidade)) in zip(cols, METRICAS.items()):
            col.metric(rotulo, f"{dados['leitura'][campo]} {unidade}")
        if dados["desvios"]:
            st.subheader("Desvios encontrados")
            st.dataframe(pd.DataFrame(dados["desvios"])[["label", "valor", "unidade", "nivel", "limite"]],
                         hide_index=True, width="stretch")
        else:
            st.success("Nenhuma métrica fora dos limites.")
        st.caption(f"Completude dos campos da leitura: {dados['completude_campos_pct']}%")

# ─── Historico ───────────────────────────────────────────────────────────────
with aba_hist:
    c1, c2 = st.columns([1, 2])
    horas = c1.select_slider("Janela (horas)", [6, 12, 24, 48], value=24)
    campo = c2.selectbox("Métrica", list(METRICAS), format_func=lambda c: METRICAS[c][0])
    try:
        dados = api.historico(tag, horas, SID)
    except api.ApiError as e:
        st.error(str(e))
    else:
        df = pd.DataFrame(dados["pontos"])
        df["timestamp"] = pd.to_datetime(df["timestamp"])
        rotulo, unidade = METRICAS[campo]
        fig = go.Figure(go.Scatter(x=df["timestamp"], y=df[campo], mode="lines",
                                   name=rotulo, line=dict(color="#58A6FF")))
        lim = dados["limites"].get(campo)
        if lim:
            fig.add_hline(y=lim["warning"], line_dash="dash", line_color=AMARELO,
                          annotation_text="Atenção")
            fig.add_hline(y=lim["critical"], line_dash="dash", line_color=VERMELHO,
                          annotation_text="Crítico")
        fig.update_layout(height=380, margin=dict(l=10, r=10, t=30, b=10),
                          yaxis_title=f"{rotulo} ({unidade})", xaxis_title=None)
        st.plotly_chart(fig, width="stretch")
        st.caption(f"{dados['total_pontos']} de {dados['pontos_esperados']} pontos esperados (um a cada 5 minutos).")
        with st.expander("Ver tabela"):
            st.dataframe(df.sort_values("timestamp", ascending=False), hide_index=True,
                         width="stretch")

# ─── Observabilidade ─────────────────────────────────────────────────────────
with aba_obs:
    st.button("Atualizar relatório", key="btn_obs")
    try:
        dados = api.observabilidade(SID)
    except api.ApiError as e:
        st.error(str(e))
    else:
        r = dados["resumo"]
        if r.get("total_chamadas", 0) == 0:
            st.info("Ainda não há chamadas registradas.")
        else:
            k = st.columns(5)
            k[0].metric("Chamadas", r["total_chamadas"])
            k[1].metric("Latência p50", f"{r['latencia_p50_ms']:.1f} ms")
            k[2].metric("Latência p95", f"{r['latencia_p95_ms']:.1f} ms")
            k[3].metric("Taxa de erro", f"{r['taxa_erro_pct']:.1f}%")
            k[4].metric("Headers completos", f"{r['completude_headers_pct']:.1f}%")

            reg = pd.DataFrame(dados["registros"])
            reg["timestamp"] = pd.to_datetime(reg["timestamp"])
            reg["feature"] = reg["feature"].fillna("(ausente)")

            g1, g2 = st.columns(2)
            with g1:
                st.markdown("**Latência por chamada (ms)**")
                fig = go.Figure(go.Scatter(x=reg["timestamp"], y=reg["latencia_ms"],
                                           mode="markers", marker=dict(color="#58A6FF", size=6),
                                           text=reg["rota"]))
                fig.add_hline(y=r["latencia_p95_ms"], line_dash="dash", line_color=AMARELO,
                              annotation_text="p95")
                fig.update_layout(height=300, margin=dict(l=10, r=10, t=10, b=10))
                st.plotly_chart(fig, width="stretch")
            with g2:
                st.markdown("**Chamadas por funcionalidade (X-Feature)**")
                pf = pd.DataFrame([{"feature": f, **v} for f, v in r["por_feature"].items()])
                fig = go.Figure(go.Bar(x=pf["feature"], y=pf["chamadas"], marker_color="#58A6FF"))
                fig.update_layout(height=300, margin=dict(l=10, r=10, t=10, b=10))
                st.plotly_chart(fig, width="stretch")

            st.markdown("**Indicadores por rota**")
            st.dataframe(pd.DataFrame([{"rota": k_, **v} for k_, v in r["por_rota"].items()]),
                         hide_index=True, width="stretch")

            st.markdown("**Registros de chamadas (mais recentes primeiro)**")
            st.dataframe(reg, hide_index=True, width="stretch")
