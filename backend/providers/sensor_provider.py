"""
Provedor de dados de sensores.
Sprint 1: leitura_atual() e historico_simulado() — inalterados.
Sprint 2: adiciona historico_com_tendencia() com curvas de degradacao realistas.
"""

import random
from datetime import datetime, timedelta
import numpy as np

# ─── Perfis de simulacao por status do equipamento (Sprint 1) ───────────────

_PERFIS: dict[str, dict] = {
    "Operacional": {
        "tensao":   (380, 8),
        "corrente": (40,  3),
        "temp":     (62,  4),
        "vibracao": (2.1, 0.4),
        "rpm":      (1760, 15),
    },
    "Em Manutenção": {
        "tensao":   (0,  0),
        "corrente": (0,  0),
        "temp":     (28, 2),
        "vibracao": (0,  0),
        "rpm":      (0,  0),
    },
    "Desligado": {
        "tensao":   (380, 2),
        "corrente": (0,   0),
        "temp":     (30,  2),
        "vibracao": (0.1, 0.05),
        "rpm":      (0,   0),
    },
}

# ─── Condicao de saude do sensor por TAG (Sprint 2) ─────────────────────────
# Independente do campo "status" do cadastro. Permite simular motores
# "Operacional" no cadastro mas com telemetria em degradacao.

_CONDICAO_SENSOR: dict[str, str] = {
    "MTR-001": "normal",
    "MTR-002": "manutencao",
    "MTR-003": "alerta",
    "MTR-004": "critico",
}


def _ruido(base: float, sigma: float) -> float:
    return round(max(0.0, base + random.gauss(0, sigma)), 2)


# ─── Sprint 1: funcoes originais (nao alteradas) ─────────────────────────────

def leitura_atual(tag: str, status: str = "Operacional") -> dict:
    perfil = _PERFIS.get(status, _PERFIS["Operacional"])
    return {
        "tag":          tag,
        "timestamp":    datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "tensao_v":     _ruido(*perfil["tensao"]),
        "corrente_a":   _ruido(*perfil["corrente"]),
        "temp_c":       _ruido(*perfil["temp"]),
        "vibracao_mms": _ruido(*perfil["vibracao"]),
        "rotacao_rpm":  _ruido(*perfil["rpm"]),
    }


def historico_simulado(tag: str, status: str = "Operacional", n: int = 24) -> list[dict]:
    agora = datetime.now()
    historico = []
    for i in range(n, 0, -1):
        leitura = leitura_atual(tag, status)
        leitura["timestamp"] = (agora - timedelta(hours=i)).strftime("%Y-%m-%d %H:%M")
        historico.append(leitura)
    return historico


# ─── Sprint 2: historico com tendencia de degradacao ────────────────────────

def historico_com_tendencia(tag: str, horas: int = 48) -> list[dict]:
    """
    Gera historico realista com curvas de tendencia por condicao do motor.
    Cada TAG tem uma semente fixa para que o historico seja consistente
    entre re-renders do Streamlit.

    Condicoes:
      - normal:     operacao estavel dentro dos limites
      - alerta:     temperatura e vibracao subindo gradualmente
      - critico:    degradacao acelerada com pico de falha nos ultimos 30%
      - manutencao: motor parado (corrente e rpm = 0)
    """
    condicao = _CONDICAO_SENSOR.get(tag, "normal")
    seed = sum(ord(c) for c in tag) % (2 ** 31)
    rng = np.random.default_rng(seed)

    n = horas * 12  # ponto a cada 5 minutos
    agora = datetime.now()
    timestamps = [agora - timedelta(minutes=5 * i) for i in range(n - 1, -1, -1)]

    if condicao == "critico":
        temp  = np.linspace(66, 95, n) + rng.normal(0, 2.0, n)
        vibr  = np.linspace(3.5, 8.8, n) + rng.normal(0, 0.35, n)
        corr  = np.linspace(35, 51, n) + rng.normal(0, 1.5, n)
        tens  = rng.normal(380, 6, n)
        rpm   = rng.normal(1760, 12, n)
        # Pico de falha nos ultimos 30% do historico
        fp = int(n * 0.70)
        temp[fp:] += rng.normal(5, 1.5, n - fp)
        vibr[fp:] += rng.normal(2, 0.5,  n - fp)

    elif condicao == "alerta":
        temp  = np.linspace(60, 79, n) + rng.normal(0, 2.0, n)
        vibr  = np.linspace(2.5, 5.3, n) + rng.normal(0, 0.30, n)
        corr  = np.linspace(38, 46, n) + rng.normal(0, 1.2, n)
        tens  = rng.normal(382, 5, n)
        rpm   = rng.normal(1760, 12, n)

    elif condicao == "manutencao":
        temp  = rng.normal(28, 2, n)
        vibr  = np.clip(rng.normal(0.05, 0.05, n), 0, 0.5)
        corr  = np.zeros(n)
        tens  = rng.normal(380, 2, n)
        rpm   = np.zeros(n)

    else:  # normal
        temp  = rng.normal(62, 3, n)
        vibr  = rng.normal(2.1, 0.4, n)
        corr  = rng.normal(40, 2, n)
        tens  = rng.normal(388, 5, n)
        rpm   = rng.normal(1760, 12, n)

    return [
        {
            "tag":          tag,
            "timestamp":    ts.strftime("%Y-%m-%d %H:%M"),
            "tensao_v":     round(float(np.clip(tens[i],  0,   500)), 2),
            "corrente_a":   round(float(np.clip(corr[i],  0,   100)), 2),
            "temp_c":       round(float(np.clip(temp[i],  15,  120)), 2),
            "vibracao_mms": round(float(np.clip(vibr[i],  0,   15)),  2),
            "rotacao_rpm":  round(float(np.clip(rpm[i],   0,  2000)), 2),
        }
        for i, ts in enumerate(timestamps)
    ]


def condicao_atual(tag: str) -> str:
    """Retorna a condicao de saude do sensor para uso no dashboard."""
    return _CONDICAO_SENSOR.get(tag, "normal")
