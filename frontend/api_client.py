"""
Cliente HTTP do front-end. Toda chamada a API passa por aqui, via requests,
e leva os headers de contexto exigidos pelo contrato de observabilidade:
    X-Session-Id -> identifica a sessao do usuario
    X-Feature    -> identifica a funcionalidade da interface que chamou
"""

import os

import requests

API_URL = os.getenv("API_URL", "http://localhost:8000")
TIMEOUT = 10


class ApiError(Exception):
    pass


def _get(caminho: str, session_id: str, feature: str, params: dict | None = None) -> dict:
    headers = {"X-Session-Id": session_id, "X-Feature": feature}
    try:
        r = requests.get(f"{API_URL}{caminho}", headers=headers,
                         params=params, timeout=TIMEOUT)
    except requests.RequestException as e:
        raise ApiError(f"Nao foi possivel conectar na API em {API_URL}. "
                       f"O back-end esta rodando? ({e.__class__.__name__})")
    if r.status_code >= 400:
        try:
            detalhe = r.json().get("detail", r.text)
        except ValueError:
            detalhe = r.text
        raise ApiError(f"Erro {r.status_code}: {detalhe}")
    return r.json()


def listar_tags(session_id: str) -> list[str]:
    return _get("/v1/sensores", session_id, "seletor-tags")["tags"]


def leitura_atual(tag: str, session_id: str) -> dict:
    return _get(f"/v1/sensores/{tag}/leitura-atual", session_id, "leitura-atual")


def historico(tag: str, horas: int, session_id: str) -> dict:
    return _get(f"/v1/sensores/{tag}/historico", session_id, "historico",
                params={"horas": horas})


def observabilidade(session_id: str, limite: int = 500) -> dict:
    return _get("/v1/observabilidade", session_id, "observabilidade",
                params={"limite": limite})
