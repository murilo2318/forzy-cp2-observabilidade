"""
Sprint 3 — Motor de regras analiticas (camada de inteligencia).

Este modulo representa o ponto onde, futuramente, entrara o modelo de
Machine Learning real (deteccao de anomalia / classificacao de estado).
Por ora, aplica regras de threshold sobre os campos reais do sensor_provider
da Sprint 1:  temp_c, vibracao_mms, corrente_a, tensao_v, rotacao_rpm.

Contrato de saida deste modulo:
    estado   -> "saudavel" | "atencao" | "critico" | "manutencao"
    desvios  -> lista de dicts descrevendo cada metrica fora do baseline

O front-end NUNCA importa este modulo diretamente. Ele consome o
alert_provider, que orquestra rules_engine + nlp_summary. Assim, trocar
estas regras por um modelo real nao afeta a camada visual.
"""

# ─── Limites (mesmos valores da Sprint 2, centralizados aqui) ───────────────
# baseline (verde)  < warning
# atencao (amarelo)  warning <= v < critical
# critico (vermelho) v >= critical

LIMITES: dict[str, dict[str, float]] = {
    "temp_c":       {"warning": 75.0, "critical": 90.0},
    "vibracao_mms": {"warning": 4.5,  "critical": 7.1},
    "corrente_a":   {"warning": 46.0, "critical": 51.0},
}

LABELS: dict[str, str] = {
    "temp_c":       "Temperatura",
    "vibracao_mms": "Vibracao",
    "corrente_a":   "Corrente",
    "tensao_v":     "Tensao",
    "rotacao_rpm":  "Rotacao",
}

UNIDADES: dict[str, str] = {
    "temp_c":       "°C",
    "vibracao_mms": "mm/s",
    "corrente_a":   "A",
    "tensao_v":     "V",
    "rotacao_rpm":  "RPM",
}

# Ordem de severidade para comparacao
_ORDEM = {"saudavel": 0, "atencao": 1, "critico": 2, "manutencao": 0}


def _classifica_metrica(campo: str, valor: float) -> str:
    """Classifica uma unica metrica em saudavel/atencao/critico."""
    lim = LIMITES.get(campo)
    if not lim:
        return "saudavel"
    if valor >= lim["critical"]:
        return "critico"
    if valor >= lim["warning"]:
        return "atencao"
    return "saudavel"


def avaliar(leitura: dict) -> dict:
    """
    Recebe uma leitura de sensor (dict com os campos da Sprint 1) e devolve
    o diagnostico de estado operacional.

    Retorno:
        {
          "estado": "critico",
          "severidade": 2,
          "desvios": [
             {"campo": "vibracao_mms", "valor": 8.4,
              "nivel": "critico", "limite": 7.1,
              "label": "Vibracao", "unidade": "mm/s"},
             ...
          ]
        }
    """
    # Motor parado = manutencao (mesma regra da Sprint 2)
    if leitura.get("rotacao_rpm", 0) == 0 and leitura.get("corrente_a", 0) == 0:
        return {"estado": "manutencao", "severidade": 0, "desvios": []}

    desvios: list[dict] = []
    estado = "saudavel"

    for campo, lim in LIMITES.items():
        valor = float(leitura.get(campo, 0.0))
        nivel = _classifica_metrica(campo, valor)
        if nivel != "saudavel":
            limite = lim["critical"] if nivel == "critico" else lim["warning"]
            desvios.append({
                "campo":    campo,
                "valor":    round(valor, 2),
                "nivel":    nivel,
                "limite":   limite,
                "label":    LABELS.get(campo, campo),
                "unidade":  UNIDADES.get(campo, ""),
            })
        if _ORDEM[nivel] > _ORDEM[estado]:
            estado = nivel

    severidade = _ORDEM[estado]
    return {"estado": estado, "severidade": severidade, "desvios": desvios}


def avaliar_serie(historico: list[dict]) -> dict:
    """
    Avalia o estado com base na ultima leitura de um historico completo.
    Conveniencia para o alert_provider.
    """
    if not historico:
        return {"estado": "saudavel", "severidade": 0, "desvios": []}
    return avaliar(historico[-1])
