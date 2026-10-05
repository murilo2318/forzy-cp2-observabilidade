"""
Registro de observabilidade das chamadas da API (contrato definido em GBA).

Cada chamada recebida gera um registro com:
    timestamp, metodo, rota, tag, status_code, latencia_ms,
    session_id (header X-Session-Id), feature (header X-Feature),
    headers_completos (1 se os dois headers de contexto vieram preenchidos).

Os registros ficam em SQLite (arquivo local), para sobreviverem a um
reinicio do servidor e poderem ser auditados depois.
"""

import os
import sqlite3
import threading
from datetime import datetime, timezone
from pathlib import Path

DB_PATH = Path(os.getenv("OBS_DB_PATH", Path(__file__).parent / "observabilidade.db"))

_lock = threading.Lock()

_SCHEMA = """
CREATE TABLE IF NOT EXISTS chamadas (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp         TEXT    NOT NULL,
    metodo            TEXT    NOT NULL,
    rota              TEXT    NOT NULL,
    tag               TEXT,
    status_code       INTEGER NOT NULL,
    latencia_ms       REAL    NOT NULL,
    session_id        TEXT,
    feature           TEXT,
    headers_completos INTEGER NOT NULL
)
"""


def _conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def inicializar() -> None:
    with _lock, _conn() as conn:
        conn.execute(_SCHEMA)


def registrar(metodo: str, rota: str, tag: str | None, status_code: int,
              latencia_ms: float, session_id: str | None,
              feature: str | None) -> None:
    """Grava um registro de chamada."""
    completos = 1 if (session_id and feature) else 0
    with _lock, _conn() as conn:
        conn.execute(
            "INSERT INTO chamadas (timestamp, metodo, rota, tag, status_code,"
            " latencia_ms, session_id, feature, headers_completos)"
            " VALUES (?,?,?,?,?,?,?,?,?)",
            (datetime.now(timezone.utc).isoformat(timespec="milliseconds"),
             metodo, rota, tag, status_code, round(latencia_ms, 3),
             session_id, feature, completos),
        )


def listar(limite: int = 200, feature: str | None = None,
           session_id: str | None = None) -> list[dict]:
    """Devolve os registros mais recentes primeiro, com filtros opcionais."""
    sql, params = "SELECT * FROM chamadas WHERE 1=1", []
    if feature:
        sql += " AND feature = ?"
        params.append(feature)
    if session_id:
        sql += " AND session_id = ?"
        params.append(session_id)
    sql += " ORDER BY id DESC LIMIT ?"
    params.append(limite)
    with _lock, _conn() as conn:
        return [dict(r) for r in conn.execute(sql, params).fetchall()]


def _percentil(valores: list[float], p: float) -> float:
    """Percentil por interpolacao linear (mesmo metodo padrao do numpy)."""
    if not valores:
        return 0.0
    v = sorted(valores)
    k = (len(v) - 1) * p / 100
    i = int(k)
    j = min(i + 1, len(v) - 1)
    return round(v[i] + (v[j] - v[i]) * (k - i), 3)


def resumo() -> dict:
    """Agrega todos os registros nos indicadores do contrato de metricas."""
    with _lock, _conn() as conn:
        linhas = [dict(r) for r in conn.execute("SELECT * FROM chamadas").fetchall()]

    total = len(linhas)
    if total == 0:
        return {"total_chamadas": 0}

    lat = [l["latencia_ms"] for l in linhas]
    erros = sum(1 for l in linhas if l["status_code"] >= 400)
    erros_5xx = sum(1 for l in linhas if l["status_code"] >= 500)
    completos = sum(l["headers_completos"] for l in linhas)

    def _agrupar(campo: str) -> dict:
        grupos: dict[str, list[dict]] = {}
        for l in linhas:
            grupos.setdefault(l[campo] or "(ausente)", []).append(l)
        return {
            chave: {
                "chamadas": len(g),
                "latencia_p50_ms": _percentil([x["latencia_ms"] for x in g], 50),
                "latencia_p95_ms": _percentil([x["latencia_ms"] for x in g], 95),
                "erros": sum(1 for x in g if x["status_code"] >= 400),
            }
            for chave, g in sorted(grupos.items())
        }

    return {
        "total_chamadas": total,
        "primeira_chamada": min(l["timestamp"] for l in linhas),
        "ultima_chamada": max(l["timestamp"] for l in linhas),
        "sessoes_distintas": len({l["session_id"] for l in linhas if l["session_id"]}),
        "latencia_p50_ms": _percentil(lat, 50),
        "latencia_p95_ms": _percentil(lat, 95),
        "latencia_max_ms": round(max(lat), 3),
        "taxa_erro_pct": round(100 * erros / total, 2),
        "taxa_erro_5xx_pct": round(100 * erros_5xx / total, 2),
        "completude_headers_pct": round(100 * completos / total, 2),
        "por_feature": _agrupar("feature"),
        "por_rota": _agrupar("rota"),
    }
