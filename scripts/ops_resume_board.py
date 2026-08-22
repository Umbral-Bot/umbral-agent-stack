#!/usr/bin/env python3
"""
Ops Resume Board — tablero de reingreso generado on-demand desde ledgers JSONL.

Escanea `<root>/*/docs/operations/ledger-*.jsonl` (un archivo por repo/programa
coordinado con la skill cursor-orchestrator), calcula el estado vigente por
(frente, pkg, dest) tomando el último evento por timestamp, y lo imprime como
tablero humano o JSON.

Este script SOLO LEE. No escribe en ningún ledger, no toca Notion, no toca
Mission Control ni board.md. Ver docs/operations/README.md para el schema y
docs/ops/ops-resume-reentry-2026-08-02.md para el runbook completo.

Opcionales del contrato cursor-orchestrator 0.11.0 (`OPTIONAL_FIELDS`):
passthrough literal desde la línea vigente hacia cada pelota y `--json`, sin
inferir. Reglas exactas en docs/operations/README.md § «Campos opcionales».

Uso:
    python scripts/ops_resume_board.py                    # tablero humano, root = carpeta padre de este repo
    python scripts/ops_resume_board.py --json              # salida JSON
    python scripts/ops_resume_board.py --root D:\\Code       # otra carpeta contenedora de repos
    python scripts/ops_resume_board.py --with-prs           # + gh pr list --state open por repo (red, best-effort)
    python scripts/ops_resume_board.py --stale-hours 12     # umbral de frescura distinto a 24h
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# BLOCKED/NO_ACK se tratan como ABIERTOS, no terminales. reference-bitacora.md
# (umbral-skills-registry/skills/cursor-orchestrator) es explicito: "SIN_ACK y
# BLOCKED como estados marcados, no como silencio" — el objetivo es que sigan
# visibles como pelota pendiente de decision, no que desaparezcan del conteo
# de abiertas ni se muestren con el flag [CERRADO]. Codificarlos como
# terminales (lectura literal del enum PKG-OPS-RESUME-A1) los haria invisibles
# en el exacto tablero pensado para surfacear "pelotas de David" — documentado
# como desviacion deliberada en docs/ops/ops-resume-reentry-2026-08-02.md.
TERMINAL_EVENTS = {"PASS", "FAIL", "CERRADO"}
OPEN_EVENTS = {
    "EMITIDO",
    "ACK",
    "REPORTADO",
    "REEMISION",
    "PENDING",
    "DEPLOYED",
    "BLOCKED",
    "NO_ACK",
    "PAUSED",  # contrato cursor-orchestrator 0.11.0 (2026-08-20)
    "RESUMED",  # contrato cursor-orchestrator 0.11.0 (2026-08-20)
}
# Solo estos eventos disparan el chequeo de staleness (spec del paquete PKG-OPS-RESUME-A1).
STALE_TRIGGER_EVENTS = {"EMITIDO", "ACK"}

# Opcionales por línea (cursor-orchestrator 0.11.0). Passthrough literal: el
# generador los PASA si vienen, no los EXIGE ni los infiere. Estas tuplas
# DIRIGEN load_events / build_board / _ball_to_dict: agregar un campo acá es
# lo único que hace falta para que viaje de la línea JSONL al --json (más el
# atributo con default en LedgerEvent y BallState).
OPTIONAL_STRING_FIELDS = ("event_id", "thread", "tipo", "gate_state", "next")
OPTIONAL_LIST_FIELDS = ("links",)
OPTIONAL_FIELDS = OPTIONAL_STRING_FIELDS + OPTIONAL_LIST_FIELDS

LEDGER_GLOB = "*/docs/operations/ledger-*.jsonl"
DEFAULT_STALE_HOURS = 24


@dataclass
class LedgerEvent:
    repo: str
    ledger_file: str
    line_no: int
    ts_raw: str
    ts: Optional[datetime]
    pkg: str
    frente: str
    dest: str
    evento: str
    ev: str
    nota: str
    # Opcionales 0.11.0 — vacíos si la línea fuente no los trae.
    event_id: str = ""
    thread: str = ""
    tipo: str = ""
    gate_state: str = ""
    next: str = ""
    links: List[str] = field(default_factory=list)
    # Opcionales presentes en la fuente pero con tipo incorrecto (p. ej. `next`
    # como lista): se descartan a vacío Y se nombran acá, para que "no vino"
    # y "vino mal" sean distinguibles en el --json (filosofía: marcar, no esconder).
    opcionales_descartados: List[str] = field(default_factory=list)


@dataclass
class BallState:
    frente: str
    pkg: str
    dest: str
    evento: str
    ts_raw: str
    ts: Optional[datetime]
    ev: str
    nota: str
    fuente: str
    is_terminal: bool
    is_known_event: bool
    stale: bool
    next_inferido: str
    # Opcionales 0.11.0 (passthrough literal de la línea vigente; `next` es
    # distinto de `next_inferido`, ver README). `opcionales_descartados` = los
    # que vinieron con tipo incorrecto.
    event_id: str = ""
    thread: str = ""
    tipo: str = ""
    gate_state: str = ""
    next: str = ""
    links: List[str] = field(default_factory=list)
    opcionales_descartados: List[str] = field(default_factory=list)


def optional_str(data: Dict[str, Any], key: str) -> str:
    """Passthrough literal de un opcional string: se copia tal cual (sin
    recortar) solo si la fuente trae un string no vacío ni solo-espacios;
    ausente, null, en blanco o de otro tipo → "" (no se inventa ni se coacciona)."""
    value = data.get(key)
    return value if isinstance(value, str) and value.strip() else ""


def _list_field_type_ok(value: Any) -> bool:
    """Fuente única de verdad de si `value` tiene una FORMA válida para un
    campo lista (string único, o lista donde CADA ítem es string) — sin
    importar contenido vacío. La usan `normalize_links` y
    `optional_type_mismatches` para no divergir: un ítem no-string en la
    lista es mismatch de TODO el campo, no un keep parcial."""
    if isinstance(value, str):
        return True
    if isinstance(value, list):
        return all(isinstance(item, str) for item in value)
    return False


def normalize_links(value: Any) -> List[str]:
    """`links` del contrato es lista de strings (URLs). Un string único se
    envuelve en lista de 1. Si la forma no es válida (`_list_field_type_ok`
    -- p. ej. CUALQUIER ítem no-string), el campo entero es mismatch de tipo
    → `[]` (ver `optional_type_mismatches`, que marca "links" en el mismo
    caso: nunca hay keep parcial de una lista con forma inválida). Con forma
    válida: strings vacíos/solo-espacios se filtran (normalización de
    presencia, no mismatch); el resto se recorta (son URLs)."""
    if not _list_field_type_ok(value):
        return []
    if isinstance(value, str):
        cleaned = value.strip()
        return [cleaned] if cleaned else []
    return [item.strip() for item in value if item.strip()]


def optional_type_mismatches(data: Dict[str, Any]) -> List[str]:
    """Nombres de opcionales que la fuente trae con un tipo que el contrato no
    admite (string esperado y vino lista/número/bool; campo-lista con algo que
    no es string ni lista, o con CUALQUIER ítem no-string). Ausente o null NO
    es mismatch — la regla de listas es la misma que usa `normalize_links`
    (`_list_field_type_ok`), a propósito: flag y payload no pueden divergir."""
    bad: List[str] = []
    for key in OPTIONAL_STRING_FIELDS:
        value = data.get(key)
        if value is not None and not isinstance(value, str):
            bad.append(key)
    for key in OPTIONAL_LIST_FIELDS:
        value = data.get(key)
        if value is None:
            continue
        if not _list_field_type_ok(value):
            bad.append(key)
    return bad


def parse_ts(raw: Optional[str]) -> Optional[datetime]:
    """Parsea timestamps ISO tolerando 'Z' y ausencia de zona/segundos.

    Los ledgers reales mezclan '2026-08-01T12:40' (naive) con
    '2026-08-01T04:55:00Z' (aware). Para poder comparar, todo lo aware se
    normaliza a UTC naive; lo naive se asume ya en esa misma escala. Esto es
    una aproximación deliberada (ver docs/operations/README.md) — la
    staleness es una señal de alerta orientativa, no un SLA de precisión horaria.
    """
    if not raw:
        return None
    try:
        dt = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        return None
    if dt.tzinfo is not None:
        dt = dt.astimezone(timezone.utc).replace(tzinfo=None)
    return dt


def discover_ledgers(root: Path) -> List[Path]:
    if not root.exists():
        return []
    return sorted(root.glob(LEDGER_GLOB))


def load_events(ledger_path: Path, repo_root: Path) -> Tuple[List[LedgerEvent], int]:
    events: List[LedgerEvent] = []
    skipped = 0
    try:
        repo_name = ledger_path.relative_to(repo_root).parts[0]
    except ValueError:
        repo_name = ledger_path.parent.parent.parent.name
    try:
        # errors="replace": un byte no-UTF-8 (ledger escrito en ANSI por un
        # writer PowerShell viejo) no puede tumbar el tablero entero — se
        # muestra con U+FFFD, que es lo que ya traen algunos ledgers reales.
        text = ledger_path.read_bytes().decode("utf-8-sig", errors="replace")
    except OSError:
        return events, skipped
    for line_no, raw_line in enumerate(text.splitlines(), start=1):
        line = raw_line.strip()
        if not line:
            continue
        try:
            data = json.loads(line)
        except json.JSONDecodeError:
            skipped += 1
            continue
        if not isinstance(data, dict):
            skipped += 1
            continue
        events.append(
            LedgerEvent(
                repo=repo_name,
                ledger_file=ledger_path.name,
                line_no=line_no,
                ts_raw=str(data.get("ts") or ""),
                ts=parse_ts(data.get("ts")),
                pkg=str(data.get("pkg") or "(sin-pkg)"),
                frente=str(data.get("frente") or "(sin-frente)"),
                dest=str(data.get("dest") or "(sin-dest)"),
                evento=str(data.get("evento") or "").strip().upper(),
                ev=str(data.get("ev") or ""),
                nota=str(data.get("nota") or ""),
                opcionales_descartados=optional_type_mismatches(data),
                **{key: optional_str(data, key) for key in OPTIONAL_STRING_FIELDS},
                **{key: normalize_links(data.get(key)) for key in OPTIONAL_LIST_FIELDS},
            )
        )
    return events, skipped


def infer_next(evento: str, dest: str, nota: str) -> str:
    """'next_inferido' = nota tal cual si existe; si no, una heurística genérica
    por tipo de evento. Nunca inventa hechos específicos del frente."""
    if nota:
        return nota
    heuristics = {
        "EMITIDO": f"esperando ACK de {dest}",
        "ACK": f"en curso, esperando REPORTADO de {dest}",
        "REPORTADO": "esperando veredicto (PASS/FAIL/BLOCKED)",
        "REEMISION": "reemitido, esperando ACK",
        "PENDING": "pendiente de iniciar",
        "DEPLOYED": "desplegado, esperando verificación",
        "BLOCKED": "bloqueado, requiere decisión explícita",
        "NO_ACK": "sin ACK, requiere reemisión o cierre",
        "PAUSED": "pausado, esperando RESUMED",
        "RESUMED": "retomado",
        "PASS": "cerrado en verde",
        "FAIL": "cerrado en rojo",
        "CERRADO": "cerrado",
    }
    return heuristics.get(evento, "evento no reconocido por el schema (posible drift)")


def latest_by_key(events: List[LedgerEvent]) -> Dict[Tuple[str, str, str], LedgerEvent]:
    """Estado vigente por (frente, pkg, dest normalizado). Gana el `ts` mayor;
    a `ts` igual (frecuente: ACK y REPORTADO en el mismo minuto) gana la línea
    leída DESPUÉS — dentro de un archivo, la más abajo (append-only); entre
    archivos, el que `discover_ledgers` ordena último. Los opcionales viajan
    con la línea ganadora, nunca se mezclan entre líneas."""
    latest: Dict[Tuple[str, str, str], LedgerEvent] = {}
    for ev in events:
        key = (ev.frente, ev.pkg, ev.dest.strip().lower() or "(sin-dest)")
        current = latest.get(key)
        if current is None:
            latest[key] = ev
            continue
        if ev.ts and current.ts:
            if ev.ts >= current.ts:
                latest[key] = ev
        elif ev.ts and not current.ts:
            # Preferimos un ts parseable a uno roto, aunque el roto venga después
            # en el archivo: es más confiable que adivinar por orden de lectura.
            latest[key] = ev
        elif not ev.ts and not current.ts:
            latest[key] = ev  # ninguno parseable: última línea leída gana
        # ev.ts is None and current.ts is not None -> nos quedamos con current
    return latest


def build_board(
    root: Path, stale_hours: int, now: datetime
) -> Tuple[List[BallState], Dict[str, Any]]:
    ledger_paths = discover_ledgers(root)
    all_events: List[LedgerEvent] = []
    total_skipped = 0
    scanned_files: List[str] = []
    for path in ledger_paths:
        events, skipped = load_events(path, root)
        all_events.extend(events)
        total_skipped += skipped
        scanned_files.append(str(path))

    latest = latest_by_key(all_events)

    balls: List[BallState] = []
    for (frente, pkg, _dest_key), ev in latest.items():
        is_known = ev.evento in TERMINAL_EVENTS or ev.evento in OPEN_EVENTS
        is_terminal = ev.evento in TERMINAL_EVENTS
        stale = False
        if ev.evento in STALE_TRIGGER_EVENTS and ev.ts is not None:
            stale = (now - ev.ts).total_seconds() > stale_hours * 3600
        balls.append(
            BallState(
                frente=frente,
                pkg=pkg,
                dest=ev.dest or "(sin-dest)",
                evento=ev.evento or "(sin-evento)",
                ts_raw=ev.ts_raw,
                ts=ev.ts,
                ev=ev.ev,
                nota=ev.nota,
                fuente=f"{ev.repo}/{ev.ledger_file}:{ev.line_no}",
                is_terminal=is_terminal,
                is_known_event=is_known,
                stale=stale,
                next_inferido=infer_next(ev.evento, ev.dest, ev.nota),
                opcionales_descartados=list(ev.opcionales_descartados),
                **{key: getattr(ev, key) for key in OPTIONAL_STRING_FIELDS},
                **{key: list(getattr(ev, key)) for key in OPTIONAL_LIST_FIELDS},
            )
        )

    balls.sort(key=lambda b: (b.frente, b.pkg, b.dest))

    meta = {
        "root": str(root),
        "ledgers_scanned": scanned_files,
        "ledger_count": len(ledger_paths),
        "events_total": len(all_events),
        "events_skipped_malformed": total_skipped,
        # Solo pelotas VIGENTES (no todas las líneas leídas) — refleja el
        # tablero actual, no el histórico del ledger.
        "optionals_type_mismatch": sum(len(b.opcionales_descartados) for b in balls),
        "stale_hours": stale_hours,
        "generated_at": now.isoformat(),
    }
    return balls, meta


def fetch_open_prs(repo_dir: Path) -> Dict[str, Any]:
    """Best-effort: gh infiere el remoto desde cwd=repo_dir. Nunca lanza — un
    fallo de red/auth/gh-ausente es un 'gap honesto', no un abort del tablero."""
    try:
        result = subprocess.run(
            ["gh", "pr", "list", "--state", "open", "--json", "number,title,headRefName,updatedAt"],
            cwd=str(repo_dir),
            capture_output=True,
            text=True,
            timeout=15,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {"ok": False, "error": str(exc)}
    if result.returncode != 0:
        return {"ok": False, "error": (result.stderr or result.stdout or "").strip()[:300]}
    try:
        prs = json.loads(result.stdout or "[]")
    except json.JSONDecodeError:
        return {"ok": False, "error": "gh devolvio JSON invalido"}
    return {"ok": True, "prs": prs}


def _ball_to_dict(b: BallState) -> Dict[str, Any]:
    return {
        "frente": b.frente,
        "pkg": b.pkg,
        "dest": b.dest,
        "evento": b.evento,
        "ts": b.ts_raw,
        "ev": b.ev,
        "nota": b.nota,
        "fuente": b.fuente,
        "terminal": b.is_terminal,
        "evento_conocido": b.is_known_event,
        "stale": b.stale,
        "next_inferido": b.next_inferido,
        # Opcionales 0.11.0 — SIEMPRE presentes; vacíos si la fuente no los trajo.
        **{key: getattr(b, key) for key in OPTIONAL_FIELDS},
        "opcionales_descartados": b.opcionales_descartados,
    }


def render_json(
    balls: List[BallState], meta: Dict[str, Any], pr_info: Optional[Dict[str, Any]] = None
) -> str:
    payload: Dict[str, Any] = {
        "meta": meta,
        "pelotas": [_ball_to_dict(b) for b in balls],
    }
    if pr_info is not None:
        payload["prs"] = pr_info
    return json.dumps(payload, ensure_ascii=False, indent=2)


def render_human(
    balls: List[BallState], meta: Dict[str, Any], pr_info: Optional[Dict[str, Any]] = None
) -> str:
    lines: List[str] = []
    lines.append("TABLERO DE REINGRESO — generado on-demand (no es SoT, deriva de ledgers)")
    lines.append(
        f"root={meta['root']}  ledgers={meta['ledger_count']}  eventos={meta['events_total']}  "
        f"descartados={meta['events_skipped_malformed']}  generado={meta['generated_at']}"
    )
    lines.append("")

    if not balls:
        lines.append("(sin ledgers o sin eventos bajo ese root — nada que mostrar)")
        return "\n".join(lines)

    open_balls = [b for b in balls if not b.is_terminal]
    stale_balls = [b for b in open_balls if b.stale]

    by_frente: Dict[str, List[BallState]] = {}
    for b in balls:
        by_frente.setdefault(b.frente, []).append(b)

    for frente in sorted(by_frente):
        lines.append(f"=== {frente} ===")
        by_pkg: Dict[str, List[BallState]] = {}
        for b in by_frente[frente]:
            by_pkg.setdefault(b.pkg, []).append(b)
        for pkg in sorted(by_pkg):
            lines.append(f"  {pkg}")
            for b in sorted(by_pkg[pkg], key=lambda x: x.dest):
                flags = []
                if not b.is_known_event:
                    flags.append("DRIFT")
                if b.stale:
                    flags.append(f"STALE>{meta['stale_hours']}h")
                if b.is_terminal:
                    flags.append("CERRADO")
                flag_str = f"  [{','.join(flags)}]" if flags else ""
                ev_ref = b.ev or "-"
                lines.append(
                    f"    {b.dest:<14} {b.evento:<10} {(b.ts_raw or '(sin-ts)'):<20} "
                    f"{ev_ref:<20} {b.next_inferido}{flag_str}"
                )
        lines.append("")

    lines.append(
        f"RESUMEN: {len(balls)} pelotas trackeadas | {len(open_balls)} abiertas | "
        f"{len(stale_balls)} stale (>{meta['stale_hours']}h sin evento posterior a EMITIDO/ACK)"
    )
    if stale_balls:
        lines.append("STALE:")
        for b in stale_balls:
            lines.append(f"  - {b.frente}/{b.pkg}/{b.dest}: {b.evento} @ {b.ts_raw} ({b.fuente})")

    if pr_info:
        lines.append("")
        lines.append("PRs abiertos por repo (best-effort, gh pr list):")
        for repo, info in sorted(pr_info.items()):
            if not info.get("ok"):
                lines.append(f"  {repo}: gap honesto — {info.get('error')}")
                continue
            prs = info.get("prs") or []
            if not prs:
                lines.append(f"  {repo}: sin PRs abiertos")
                continue
            for pr in prs:
                lines.append(f"  {repo}: #{pr.get('number')} {pr.get('title')} ({pr.get('headRefName')})")

    return "\n".join(lines)


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Tablero de reingreso on-demand desde ledgers JSONL (cursor-orchestrator)."
    )
    parser.add_argument(
        "--root",
        type=Path,
        default=None,
        help="Carpeta que contiene los repos con docs/operations/ (default: carpeta padre de este repo)",
    )
    parser.add_argument("--json", action="store_true", help="Salida JSON en vez de tablero humano")
    parser.add_argument(
        "--with-prs",
        action="store_true",
        help="Consultar 'gh pr list --state open' por repo con ledger (requiere red + gh autenticado)",
    )
    parser.add_argument(
        "--stale-hours",
        type=int,
        default=DEFAULT_STALE_HOURS,
        help=f"Horas sin evento posterior para marcar EMITIDO/ACK como stale (default {DEFAULT_STALE_HOURS})",
    )
    parser.add_argument(
        "--now",
        type=str,
        default=None,
        help="Timestamp ISO a usar como 'ahora' (para pruebas); default = hora actual UTC",
    )
    args = parser.parse_args(argv)

    # En consolas Windows con codepage legacy (cp1252/cp850), imprimir "—" sin
    # esto degenera en mojibake. reconfigure() no existe en streams no reales
    # (p. ej. los que usa pytest capsys) — se ignora silenciosamente ahí.
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except (ValueError, OSError):
            pass

    repo_root = Path(__file__).resolve().parent.parent
    root = args.root if args.root is not None else repo_root.parent

    if args.now:
        now = parse_ts(args.now)
        if now is None:
            print(f"error: --now invalido: {args.now}", file=sys.stderr)
            return 2
    else:
        now = datetime.now(timezone.utc).replace(tzinfo=None)

    balls, meta = build_board(root, args.stale_hours, now)

    pr_info: Optional[Dict[str, Any]] = None
    if args.with_prs:
        pr_info = {}
        for path in discover_ledgers(root):
            repo_dir = path.parent.parent.parent
            repo_name = repo_dir.name
            if repo_name in pr_info:
                continue
            pr_info[repo_name] = fetch_open_prs(repo_dir)

    if args.json:
        print(render_json(balls, meta, pr_info))
    else:
        print(render_human(balls, meta, pr_info))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
