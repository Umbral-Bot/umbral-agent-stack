"""Mission Control configuration — env-driven, no defaults para secretos."""

from __future__ import annotations

import os
from pathlib import Path

# --- HTTP ---
HOST: str = os.getenv("MISSION_CONTROL_HOST", "127.0.0.1")
PORT: int = int(os.getenv("MISSION_CONTROL_PORT", "8089"))

# --- Auth ---
# Bearer obligatorio en todas las rutas excepto /health (ver ADR-009 D4).
TOKEN: str | None = os.getenv("MISSION_CONTROL_TOKEN")

# --- Backends de datos ---
REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")
OPENCLAW_JSON_PATH: Path = Path(
    os.getenv("OPENCLAW_JSON_PATH", str(Path.home() / ".openclaw" / "openclaw.json"))
)
QUOTA_STATE_PATH: Path = Path(
    os.getenv(
        "OPENCLAW_QUOTA_STATE_PATH",
        str(Path.home() / ".config" / "openclaw" / "claude-quota-state.json"),
    )
)
EVAL_REPORT_PATH: Path = Path(
    os.getenv(
        "MISSION_CONTROL_EVAL_REPORT_PATH",
        str(
            Path(__file__).resolve().parents[1]
            / "reports"
            / "evals"
            / "generated"
            / "core-eval-harness-latest.json"
        ),
    )
)

# --- PIT vault (PIT-5 P5.1, solo lectura) ---
PIT_VAULT_PATH: Path = Path(
    os.getenv("PIT_VAULT_PATH", str(Path.home() / "umbral-pit-vault"))
)
PIT_EVIDENCE_DIR: Path = Path(
    os.getenv("PIT_EVIDENCE_DIR", str(Path.home() / ".coord-ag-evidence"))
)
# Fallback de spec (hallazgo P5.0: el vault piloto no tiene spec/pit_spec.yaml).
PIT_SPEC_FALLBACK_DIR: Path = Path(
    os.getenv(
        "PIT_SPEC_FALLBACK_DIR",
        str(Path(__file__).resolve().parents[1] / "examples"),
    )
)

# --- Persistencia (ADR-009 D5) ---
SNAPSHOTS_DIR: Path = Path(
    os.getenv(
        "MISSION_CONTROL_SNAPSHOTS_DIR",
        str(Path(__file__).resolve().parent / "snapshots"),
    )
)

# Colas Redis que el dispatcher conoce (mantener sync con dispatcher.service).
KNOWN_QUEUES: tuple[str, ...] = (
    "umbral:tasks:pending",
    "umbral:tasks:in_flight",
    "umbral:tasks:dead_letter",
)
