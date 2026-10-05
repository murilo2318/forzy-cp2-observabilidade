"""
Script de consumo via requests dos tres endpoints da API.

Uso:  python scripts/consumo.py            (API em http://localhost:8000)
      API_URL=http://outro:8000 python scripts/consumo.py
"""

import os
import uuid

import requests

API_URL = os.getenv("API_URL", "http://localhost:8000")
SESSION_ID = str(uuid.uuid4())


def chamar(caminho: str, feature: str, **params) -> requests.Response:
    headers = {"X-Session-Id": SESSION_ID, "X-Feature": feature}
    r = requests.get(f"{API_URL}{caminho}", headers=headers, params=params, timeout=10)
    print(f"GET {caminho} -> {r.status_code} ({r.elapsed.total_seconds() * 1000:.1f} ms)")
    return r


def main() -> None:
    print(f"Sessao: {SESSION_ID}\n")

    # 1. Leitura atual
    for tag in ["MTR-001", "MTR-003", "MTR-004"]:
        d = chamar(f"/v1/sensores/{tag}/leitura-atual", "script-leitura-atual").json()
        l = d["leitura"]
        print(f"   {tag}: estado={d['estado']} severidade={d['severidade']} "
              f"temp={l['temp_c']}C vib={l['vibracao_mms']}mm/s corrente={l['corrente_a']}A")

    # 2. Historico
    d = chamar("/v1/sensores/MTR-004/historico", "script-historico", horas=6).json()
    print(f"   {d['total_pontos']} pontos; primeiro={d['pontos'][0]['timestamp']} "
          f"ultimo={d['pontos'][-1]['timestamp']}")

    # Caso de erro, para aparecer na taxa de erro (TAG inexistente -> 404)
    chamar("/v1/sensores/MTR-999/leitura-atual", "script-leitura-atual")

    # 3. Observabilidade
    d = chamar("/v1/observabilidade", "script-observabilidade", limite=5).json()
    r = d["resumo"]
    print(f"   total={r['total_chamadas']} p50={r['latencia_p50_ms']}ms "
          f"p95={r['latencia_p95_ms']}ms erro={r['taxa_erro_pct']}% "
          f"headers_completos={r['completude_headers_pct']}%")
    print("   ultimos registros:")
    for reg in d["registros"]:
        print(f"     {reg['timestamp']} {reg['rota']} {reg['status_code']} "
              f"{reg['latencia_ms']}ms feature={reg['feature']}")


if __name__ == "__main__":
    main()
