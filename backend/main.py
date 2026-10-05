"""
Forzy - Sensor Monitoring API (CP2 integrado GBA + Front-end).

Expoe o provider de Sensores das Sprints 1 a 3 como API FastAPI e registra,
a cada chamada, os metadados de observabilidade definidos em Governanca em IA.

Rodar:  uvicorn backend.main:app --reload --port 8000
"""

import time
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import FastAPI, HTTPException, Query, Request

from backend import observabilidade as obs
from backend.analytics import rules_engine as rules
from backend.providers import sensor_provider

# TAGs conhecidas pelo provider de sensores (o provider de Equipamentos
# so sera migrado na Sprint 4).
TAGS = sorted(sensor_provider._CONDICAO_SENSOR.keys())
CAMPOS = ["tensao_v", "corrente_a", "temp_c", "vibracao_mms", "rotacao_rpm"]

# Rotas que nao entram no registro (documentacao e verificacao de saude).
_NAO_REGISTRAR = ("/docs", "/redoc", "/openapi.json", "/health", "/favicon.ico")


@asynccontextmanager
async def lifespan(app: FastAPI):
    obs.inicializar()
    yield


app = FastAPI(
    title="Forzy - Sensor Monitoring API",
    version="1.0.0",
    description="Leitura atual, historico e observabilidade do provider de Sensores.",
    lifespan=lifespan,
)


@app.middleware("http")
async def registrar_chamada(request: Request, call_next):
    """Mede a latencia e grava o registro de observabilidade de cada chamada."""
    if request.url.path.startswith(_NAO_REGISTRAR):
        return await call_next(request)

    inicio = time.perf_counter()
    status_code = 500
    try:
        response = await call_next(request)
        status_code = response.status_code
        return response
    finally:
        latencia_ms = (time.perf_counter() - inicio) * 1000
        rota = request.scope.get("route")
        obs.registrar(
            metodo=request.method,
            rota=rota.path if rota else request.url.path,
            tag=request.path_params.get("tag"),
            status_code=status_code,
            latencia_ms=latencia_ms,
            session_id=request.headers.get("X-Session-Id"),
            feature=request.headers.get("X-Feature"),
        )


def _validar_tag(tag: str) -> str:
    tag = tag.upper()
    if tag not in TAGS:
        raise HTTPException(404, f"TAG '{tag}' nao encontrada. Disponiveis: {TAGS}")
    return tag


def _completude(leitura: dict) -> float:
    """Percentual dos campos de sensor presentes e nao nulos na leitura."""
    ok = sum(1 for c in CAMPOS if leitura.get(c) is not None)
    return round(100 * ok / len(CAMPOS), 2)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/v1/sensores")
def listar_tags():
    """TAGs disponiveis (apoio para o front montar o seletor)."""
    return {"tags": TAGS}


@app.get("/v1/sensores/{tag}/leitura-atual")
def leitura_atual(tag: str):
    """Ultima leitura do sensor, com estado e severidade do motor de regras."""
    tag = _validar_tag(tag)
    # Mesmo criterio da Sprint 3: a leitura atual e o ultimo ponto do historico.
    leitura = sensor_provider.historico_com_tendencia(tag, horas=1)[-1]
    diagnostico = rules.avaliar(leitura)
    return {
        "tag": tag,
        "leitura": leitura,
        "estado": diagnostico["estado"],
        "severidade": diagnostico["severidade"],
        "desvios": diagnostico["desvios"],
        "limites": rules.LIMITES,
        "completude_campos_pct": _completude(leitura),
        "consultado_em": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }


@app.get("/v1/sensores/{tag}/historico")
def historico(tag: str, horas: int = Query(24, ge=1, le=168)):
    """Historico do sensor (um ponto a cada 5 minutos)."""
    tag = _validar_tag(tag)
    pontos = sensor_provider.historico_com_tendencia(tag, horas=horas)
    return {
        "tag": tag,
        "horas": horas,
        "total_pontos": len(pontos),
        "pontos_esperados": horas * 12,
        "limites": rules.LIMITES,
        "pontos": pontos,
    }


@app.get("/v1/observabilidade")
def observabilidade(
    limite: int = Query(200, ge=1, le=5000),
    feature: str | None = None,
    session_id: str | None = None,
):
    """Registros de chamadas coletados e indicadores agregados (uso de GBA)."""
    return {
        "resumo": obs.resumo(),
        "registros": obs.listar(limite=limite, feature=feature, session_id=session_id),
    }
