# Forzy · Sensor Monitoring API — CP2 integrado (Governança em IA + Front-end)

Observabilidade de um endpoint da solução Forzy · Digital Twin. O provider de
Sensores construído nas Sprints 1 a 3 é exposto como API FastAPI; cada chamada
recebida gera um registro de observabilidade (headers de contexto, timestamp e
latência); e uma interface em Streamlit consome tudo via `requests`.

FIAP · Tecnólogo em Inteligência Artificial · Turma 2TIAPF · 2026

## Integrantes

| Nome | RM |
| --- | --- |
| Murilo de Faria Benhossi | 562358 |
| Nicolas Lemos Ribeiro | 553273 |
| Ricardo de Paiva Melo | 565522 |
| Luís Fernando de Oliveira Salgado | 561401 |
| Pedro Leal Murad | 565460 |
| Jonas Alaf | 566479 |

## Arquitetura

```
frontend/app.py (Streamlit)          scripts/consumo.py
        │                                   │
        └────── frontend/api_client.py ─────┘      requests + headers
                        │                          X-Session-Id / X-Feature
                        ▼
              backend/main.py (FastAPI)
                 │            │
   middleware de │            │ rotas
 observabilidade │            ▼
                 │   providers/sensor_provider.py   (Sprints 1 e 2, sem alteração)
                 │   analytics/rules_engine.py      (Sprint 3, sem alteração)
                 ▼
     backend/observabilidade.py  →  SQLite (observabilidade.db)
```

- **Back-end (`backend/`)**: FastAPI apenas para o provider de Sensores. Um
  middleware mede a latência de cada chamada e grava um registro com timestamp,
  método, rota, TAG, status, latência, `X-Session-Id` e `X-Feature`.
- **Front-end (`frontend/`)**: Streamlit com três abas (Leitura atual, Histórico
  e Observabilidade). Não importa nada do back-end: todo dado chega pela API.
- **Script (`scripts/consumo.py`)**: consome os três endpoints pelo terminal.

Fora do escopo deste checkpoint (ficam para a Sprint 4): autenticação e
migração dos providers de Equipamentos e Plantas.

## Endpoints

| Funcionalidade | Endpoint | Retorno |
| --- | --- | --- |
| Leitura atual | `GET /v1/sensores/{tag}/leitura-atual` | Leitura, estado, severidade e desvios |
| Histórico | `GET /v1/sensores/{tag}/historico?horas=24` | Pontos a cada 5 minutos |
| Observabilidade | `GET /v1/observabilidade?limite=200` | Indicadores agregados e registros de chamadas |
| Apoio | `GET /v1/sensores` | TAGs disponíveis (MTR-001 a MTR-004) |

Documentação interativa em `http://localhost:8000/docs`.

### Registro de observabilidade (um por chamada)

| Campo | Origem |
| --- | --- |
| `timestamp` | Relógio do servidor (UTC) |
| `metodo`, `rota`, `tag`, `status_code` | Requisição e resposta |
| `latencia_ms` | Medida no middleware |
| `session_id` | Header `X-Session-Id` |
| `feature` | Header `X-Feature` |
| `headers_completos` | 1 se os dois headers vieram preenchidos |

## Como rodar localmente

Pacotes necessários (em `requirements.txt`): `fastapi`, `uvicorn`, `requests`,
`streamlit`, `pandas`, `numpy`, `plotly`. Testado com Python 3.13.

```bash
python3.13 -m pip install -r requirements.txt
```

Terminal 1, na raiz do projeto (back-end):

```bash
python3.13 -m uvicorn backend.main:app --port 8000
```

Terminal 2, na raiz do projeto (front-end):

```bash
python3.13 -m streamlit run frontend/app.py
```

Terminal 3, opcional (script de consumo):

```bash
python3.13 scripts/consumo.py
```

Se a API estiver em outro endereço, defina `API_URL` antes de rodar o front ou
o script.

## Vídeo de demonstração

(link do vídeo)
