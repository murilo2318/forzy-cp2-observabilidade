"""
Sobe a API FastAPI dentro do mesmo processo do Streamlit quando ela nao
esta rodando (caso do Streamlit Cloud, que executa apenas um comando).

Rodando localmente com o uvicorn em outro terminal, este modulo nao faz
nada: ele detecta a API no ar e sai. Em qualquer dos casos o front continua
consumindo a API por HTTP, via requests.
"""

import sys
import threading
import time
from pathlib import Path

import requests
import streamlit as st

RAIZ = Path(__file__).resolve().parent.parent


def _no_ar(api_url: str) -> bool:
    try:
        return requests.get(f"{api_url}/health", timeout=1).status_code == 200
    except requests.RequestException:
        return False


@st.cache_resource(show_spinner="Iniciando a API...")
def garantir_api(api_url: str) -> str:
    """Devolve 'externa' se a API ja estava no ar, 'embutida' se foi iniciada aqui."""
    if _no_ar(api_url):
        return "externa"
    if "localhost" not in api_url and "127.0.0.1" not in api_url:
        return "externa"  # API remota fora do ar: nao ha o que iniciar aqui

    import uvicorn

    if str(RAIZ) not in sys.path:
        sys.path.insert(0, str(RAIZ))
    from backend.main import app

    porta = int(api_url.rsplit(":", 1)[-1])
    servidor = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=porta,
                                             log_level="warning"))
    threading.Thread(target=servidor.run, daemon=True).start()

    for _ in range(50):
        if _no_ar(api_url):
            break
        time.sleep(0.2)
    return "embutida"
