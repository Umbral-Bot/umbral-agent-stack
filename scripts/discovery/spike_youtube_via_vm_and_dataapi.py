"""Spike 013-K: validate two paths to bypass VPS IP block on YouTube.

Read-only. Does NOT write SQLite. Does NOT call Notion API.

VIA A — Worker Windows VM (residential IP):
    Probe each YouTube watch page from the VM via the worker's `browser.navigate`
    + `browser.read_page` tasks (no `yt-dlp` task is registered on the VM yet —
    that would be 013-K implementation work). The signal is whether the residential
    IP receives the real player HTML (`ytInitialPlayerResponse`) instead of the
    bot challenge ("Sign in to confirm you're not a bot"). If true, 013-K can
    safely add a yt-dlp task to the VM worker.

VIA B — YouTube Data API v3:
    Plain HTTPS calls to `https://www.googleapis.com/youtube/v3/videos` with a
    server-side API key. Returns title, description, tags, duration, channelId,
    publishedAt, statistics. Transcripts are NOT covered by Data API.

Usage:
    python -m scripts.discovery.spike_youtube_via_vm_and_dataapi \
        [--source-report reports/spike-youtube-20260507T055904Z.json] \
        [--limit 8] \
        [--output reports/spike-youtube-vm-dataapi-<TS>.json]

Env:
    WORKER_URL_VM, WORKER_TOKEN — required for VIA A.
    YOUTUBE_DATA_API_KEY — required for VIA B (otherwise blocker logged + skipped).
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx

DEFAULT_SOURCE = Path("reports/spike-youtube-20260507T055904Z.json")
DEFAULT_LIMIT = 8
DATA_API_URL = "https://www.googleapis.com/youtube/v3/videos"
BOT_CHALLENGE_MARKERS = (
    "Sign in to confirm you",
    "confirm you're not a bot",
    "consent.youtube.com",
    # Google interstitial captcha (returned when egress IP is rate-limited):
    "google.com/sorry",
    "/sorry/index",
    "g-recaptcha",
    "solveSimpleChallenge",
)
PLAYER_MARKER = "ytInitialPlayerResponse"


def _now_ms() -> int:
    return int(time.monotonic() * 1000)


# --------------------------------------------------------------------------- #
# Targets
# --------------------------------------------------------------------------- #


def load_targets(source_report: Path, limit: int) -> list[dict[str, Any]]:
    """Load the same video_ids used in the prior 013-J spike."""
    data = json.loads(source_report.read_text())
    targets: list[dict[str, Any]] = []
    for it in data.get("items", []):
        vid = it.get("video_id")
        if not vid:
            continue
        targets.append(
            {
                "sqlite_id": it.get("sqlite_id"),
                "video_id": vid,
                "url": it.get("url") or f"https://www.youtube.com/watch?v={vid}",
                "titulo": it.get("titulo"),
                "referente_id": it.get("referente_id"),
            }
        )
        if len(targets) >= limit:
            break
    return targets


# --------------------------------------------------------------------------- #
# VIA A — VM browser.navigate
# --------------------------------------------------------------------------- #


def vm_health(worker_url_vm: str, token: str, timeout: float = 5.0) -> dict[str, Any]:
    start = _now_ms()
    try:
        r = httpx.get(
            f"{worker_url_vm.rstrip('/')}/health",
            timeout=timeout,
            headers={"Authorization": f"Bearer {token}"} if token else None,
        )
        r.raise_for_status()
        body = r.json()
        return {
            "ok": True,
            "worker_url_vm": worker_url_vm,
            "version": body.get("version"),
            "tasks_registered_count": len(body.get("tasks_registered") or []),
            "has_browser_navigate": "browser.navigate" in (body.get("tasks_registered") or []),
            "has_yt_dlp_task": any(
                t.startswith("youtube.") for t in (body.get("tasks_registered") or [])
            ),
            "elapsed_ms": _now_ms() - start,
        }
    except Exception as exc:
        return {
            "ok": False,
            "worker_url_vm": worker_url_vm,
            "error": f"{type(exc).__name__}: {exc}"[:300],
            "elapsed_ms": _now_ms() - start,
        }


def vm_probe_watch_page(
    worker_url_vm: str,
    token: str,
    video_id: str,
    timeout: float = 60.0,
) -> dict[str, Any]:
    """Use VM browser.navigate + browser.read_page to fetch a YouTube watch page.

    Returns observability fields: html length, presence of player marker, presence
    of bot challenge. This is a residential-IP signal, not a full extraction.
    """
    start = _now_ms()
    base = worker_url_vm.rstrip("/")
    url = f"https://www.youtube.com/watch?v={video_id}"
    page_id = f"spike-013k-{video_id}"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }
    try:
        with httpx.Client(timeout=timeout) as client:
            nav = client.post(
                f"{base}/run",
                headers=headers,
                json={
                    "task": "browser.navigate",
                    "input": {
                        "url": url,
                        "wait_until": "domcontentloaded",
                        "page_id": page_id,
                        "timeout_ms": 30000,
                    },
                },
            )
            nav.raise_for_status()
            read = client.post(
                f"{base}/run",
                headers=headers,
                json={
                    "task": "browser.read_page",
                    "input": {"page_id": page_id, "include_html": True},
                },
            )
            read.raise_for_status()
            payload = read.json()
            # Worker envelopes vary; try common shapes.
            data = payload.get("result") or payload.get("output") or payload
            if isinstance(data, dict) and "html" not in data and "result" in data:
                data = data["result"]
            html = ""
            text = ""
            final_url = ""
            if isinstance(data, dict):
                html = data.get("html") or ""
                text = data.get("text") or ""
                final_url = data.get("url") or ""
            page_blob = (html or "") + "\n" + (text or "") + "\n" + (final_url or "")
            has_player = PLAYER_MARKER in page_blob
            has_bot = any(m in page_blob for m in BOT_CHALLENGE_MARKERS)
            # Useful description heuristic: ytInitialPlayerResponse + length suggests
            # the player JSON (which contains shortDescription) is in-band.
            desc_block_present = '"shortDescription"' in page_blob
            return {
                "ok": True,
                "html_bytes": len(html),
                "text_bytes": len(text),
                "final_url": final_url[:200],
                "redirected_to_sorry": "google.com/sorry" in (final_url or ""),
                "has_player_marker": has_player,
                "has_bot_challenge": has_bot,
                "has_short_description_field": desc_block_present,
                # Treat "useful" as: the player JSON is present AND no bot wall.
                "useful_for_extraction": bool(has_player and not has_bot),
                "elapsed_ms": _now_ms() - start,
            }
    except httpx.HTTPStatusError as exc:
        return {
            "ok": False,
            "error": f"HTTP {exc.response.status_code}: {exc.response.text[:200]}",
            "elapsed_ms": _now_ms() - start,
        }
    except Exception as exc:
        return {
            "ok": False,
            "error": f"{type(exc).__name__}: {exc}"[:300],
            "elapsed_ms": _now_ms() - start,
        }


# --------------------------------------------------------------------------- #
# VIA B — YouTube Data API v3
# --------------------------------------------------------------------------- #

# ISO-8601 duration parser (PT#H#M#S). Pure-Python, no extra deps.
_ISO_DURATION_RE = re.compile(
    r"^PT(?:(?P<h>\d+)H)?(?:(?P<m>\d+)M)?(?:(?P<s>\d+)S)?$"
)


def parse_iso_duration(raw: str | None) -> int | None:
    """Parse YouTube Data API ISO-8601 duration (e.g. PT1H2M3S) to seconds."""
    if not raw or not isinstance(raw, str):
        return None
    m = _ISO_DURATION_RE.match(raw.strip())
    if not m:
        return None
    h = int(m.group("h") or 0)
    mi = int(m.group("m") or 0)
    s = int(m.group("s") or 0)
    return h * 3600 + mi * 60 + s


def parse_data_api_response(payload: dict[str, Any]) -> dict[str, Any]:
    """Parse a single-video Data API response into normalized fields.

    Input: full JSON body from `videos?part=snippet,contentDetails,statistics&id=...`.
    Output: dict with `found`, `fields`, and per-field availability flags.
    """
    items = payload.get("items") or []
    if not items:
        return {"found": False, "fields": {}}
    item = items[0]
    snippet = item.get("snippet") or {}
    content = item.get("contentDetails") or {}
    stats = item.get("statistics") or {}
    description = snippet.get("description") or ""
    tags = snippet.get("tags") or []
    duration_seconds = parse_iso_duration(content.get("duration"))
    fields = {
        "title": snippet.get("title"),
        "description": description,
        "description_len": len(description),
        "tags": tags,
        "tags_count": len(tags),
        "channel_id": snippet.get("channelId"),
        "channel_title": snippet.get("channelTitle"),
        "published_at": snippet.get("publishedAt"),
        "duration_iso": content.get("duration"),
        "duration_seconds": duration_seconds,
        "view_count": stats.get("viewCount"),
        "like_count": stats.get("likeCount"),
        "comment_count": stats.get("commentCount"),
        "default_language": snippet.get("defaultLanguage"),
        "default_audio_language": snippet.get("defaultAudioLanguage"),
        "category_id": snippet.get("categoryId"),
    }
    return {
        "found": True,
        "fields": fields,
        "has_long_description": fields["description_len"] > 500,
        "has_tags": fields["tags_count"] > 0,
        "has_duration": duration_seconds is not None,
    }


def data_api_fetch(
    api_key: str,
    video_id: str,
    timeout: float = 15.0,
) -> dict[str, Any]:
    start = _now_ms()
    try:
        r = httpx.get(
            DATA_API_URL,
            params={
                "part": "snippet,contentDetails,statistics",
                "id": video_id,
                "key": api_key,
            },
            timeout=timeout,
        )
        if r.status_code != 200:
            # Don't leak api_key in error text.
            text = r.text[:300].replace(api_key, "***")
            return {
                "ok": False,
                "error": f"HTTP {r.status_code}: {text}",
                "elapsed_ms": _now_ms() - start,
            }
        parsed = parse_data_api_response(r.json())
        return {
            "ok": parsed["found"],
            "elapsed_ms": _now_ms() - start,
            **parsed,
        }
    except Exception as exc:
        return {
            "ok": False,
            "error": f"{type(exc).__name__}: {exc}"[:300],
            "elapsed_ms": _now_ms() - start,
        }


# --------------------------------------------------------------------------- #
# Reporting
# --------------------------------------------------------------------------- #


def summarize(items: list[dict[str, Any]]) -> dict[str, Any]:
    n = len(items)

    def _avg(key: str, sub: str = "elapsed_ms") -> float | None:
        vals = [
            it[key][sub]
            for it in items
            if isinstance(it.get(key), dict) and it[key].get(sub) is not None
        ]
        return round(sum(vals) / len(vals), 1) if vals else None

    via_a_useful = sum(
        1
        for it in items
        if isinstance(it.get("via_a_vm_browser"), dict)
        and it["via_a_vm_browser"].get("useful_for_extraction")
    )
    via_a_ok = sum(
        1
        for it in items
        if isinstance(it.get("via_a_vm_browser"), dict)
        and it["via_a_vm_browser"].get("ok")
    )
    via_a_redirect = sum(
        1
        for it in items
        if isinstance(it.get("via_a_vm_browser"), dict)
        and it["via_a_vm_browser"].get("redirected_to_sorry")
    )
    via_a_bot = sum(
        1
        for it in items
        if isinstance(it.get("via_a_vm_browser"), dict)
        and it["via_a_vm_browser"].get("has_bot_challenge")
    )
    via_b_ok = sum(
        1
        for it in items
        if isinstance(it.get("via_b_data_api"), dict)
        and it["via_b_data_api"].get("ok")
    )
    via_b_long_desc = sum(
        1
        for it in items
        if isinstance(it.get("via_b_data_api"), dict)
        and it["via_b_data_api"].get("has_long_description")
    )
    return {
        "sample_size": n,
        "via_a_vm_browser": {
            "navigate_ok": via_a_ok,
            "useful_for_extraction": via_a_useful,
            "redirected_to_sorry": via_a_redirect,
            "redirected_to_sorry_pct": round(via_a_redirect / n * 100, 1) if n else 0,
            "bot_challenge_count": via_a_bot,
            "bot_challenge_pct": round(via_a_bot / n * 100, 1) if n else 0,
            "avg_elapsed_ms": _avg("via_a_vm_browser"),
        },
        "via_b_data_api": {
            "ok_count": via_b_ok,
            "has_long_desc_count": via_b_long_desc,
            "avg_elapsed_ms": _avg("via_b_data_api"),
        },
    }


def comparison_table_md(summary: dict[str, Any], blockers: dict[str, list[str]]) -> str:
    n = summary["sample_size"] or 1
    a = summary["via_a_vm_browser"]
    b = summary["via_b_data_api"]

    def _pct(x: int) -> str:
        return f"{x / n * 100:.0f}%"

    rows = [
        "| alt | sample_size | success% | has_transcript | has_long_desc | avg_latency_ms | blockers |",
        "| --- | --- | --- | --- | --- | --- | --- |",
        (
            f"| VIA A — VM browser (residential IP probe) | {n} | "
            f"{_pct(a['useful_for_extraction'])} | n/a (probe-only) | n/a (probe-only) | "
            f"{a['avg_elapsed_ms']} | {'; '.join(blockers['via_a']) or '—'} |"
        ),
        (
            f"| VIA B — YouTube Data API v3 | {n} | "
            f"{_pct(b['ok_count'])} | NO (Data API does not expose transcripts) | "
            f"{_pct(b['has_long_desc_count'])} | {b['avg_elapsed_ms']} | "
            f"{'; '.join(blockers['via_b']) or '—'} |"
        ),
    ]
    return "\n".join(rows)


def build_recommendation(summary: dict[str, Any], blockers: dict[str, list[str]]) -> str:
    n = summary["sample_size"] or 1
    a_useful_pct = summary["via_a_vm_browser"]["useful_for_extraction"] / n * 100
    a_redirect_pct = summary["via_a_vm_browser"].get("redirected_to_sorry_pct") or 0
    a_bot_pct = summary["via_a_vm_browser"].get("bot_challenge_pct") or 0
    b_ok_pct = summary["via_b_data_api"]["ok_count"] / n * 100
    b_long_pct = summary["via_b_data_api"]["has_long_description_count"] / n * 100 if "has_long_description_count" in summary["via_b_data_api"] else summary["via_b_data_api"]["has_long_desc_count"] / n * 100

    a_blocked = bool(blockers["via_a"])
    b_blocked = bool(blockers["via_b"])

    # Special case (highest priority): VM reachable but its egress IP is ALSO
    # captcha-walled by Google. Evaluate BEFORE generic blocker checks because
    # the redirect itself is a blocker we still want to report on with numbers.
    if a_redirect_pct >= 50:
        if b_blocked:
            return (
                f"RECOMENDACIÓN 013-K: VIA A INVALIDADA. La VM está reachable y "
                f"`browser.navigate` funciona, pero {a_redirect_pct:.0f}% de los "
                "requests son redirigidos a `google.com/sorry/index?...` con un "
                "reCAPTCHA — el IP de egreso de la VM también está marcado por "
                "Google. Conclusión: cambiar de IP residencial NO es la solución; "
                "el problema es 'cualquier IP que ya pegó suficientes requests a "
                "YouTube'. **Próximo paso obligatorio:** desbloquear VIA B "
                "(YouTube Data API v3). David debe crear la API key — sin eso, "
                "Stage 2 para canal=youtube queda en stub. NO implementar yt-dlp "
                "en la VM hasta resolver el captcha del lado VM (cookies de un "
                "browser real, rotación de IP, o proxy residencial pago)."
            )
        if b_ok_pct >= 75:
            return (
                f"RECOMENDACIÓN 013-K: implementar SOLO VIA B (YouTube Data API v3). "
                f"VIA A invalidada: {a_redirect_pct:.0f}% de requests desde la VM "
                "son redirigidos a `google.com/sorry` (reCAPTCHA) — el IP de la VM "
                "también está flagged por Google. Data API entrega "
                f"{b_long_pct:.0f}% de descripciones >500c, suficiente para evitar "
                "created_no_body. Sin transcript: aceptable para Stage 2 v1."
            )
        return (
            f"RECOMENDACIÓN 013-K: bloqueado. VIA A invalidada "
            f"({a_redirect_pct:.0f}% redirect a `/sorry`); VIA B accesible "
            f"({b_ok_pct:.0f}% ok) pero por debajo de threshold 75%. Investigar "
            "errores Data API y reintentar."
        )

    if not a_blocked and a_useful_pct >= 75 and not b_blocked and b_ok_pct >= 75:
        return (
            "RECOMENDACIÓN 013-K: combinación A + B. Usar VIA A (VM con yt-dlp + "
            "youtube-transcript-api) como fuente PRIMARIA porque entrega transcript "
            "+ chapters; usar VIA B (Data API) como fuente de FALLBACK y para enriquecer "
            "metadata (tags, statistics, defaultLanguage). Costo: implementar tarea "
            "`youtube.fetch` en el worker de la VM y un cliente Data API en VPS."
        )
    if not a_blocked and a_useful_pct >= 75:
        return (
            "RECOMENDACIÓN 013-K: implementar VIA A (Worker VM). El IP residencial de "
            "la VM no recibe el bot wall, por lo que Stage 2 puede ejecutar yt-dlp + "
            "youtube-transcript-api desde la VM. Próximo paso: agregar tarea "
            "`youtube.fetch` al worker Windows y enrutar canal=youtube vía VM."
        )
    if not b_blocked and b_ok_pct >= 75:
        long_note = (
            f"Useful descriptions ({b_long_pct:.0f}% > 500c) — suficiente para evitar "
            "created_no_body."
            if b_long_pct >= 50
            else f"Descripciones largas escasas ({b_long_pct:.0f}% > 500c) — bueno para "
            "metadata pero NO sustituye transcript; el cuerpo del Notion seguirá siendo "
            "limitado."
        )
        return (
            "RECOMENDACIÓN 013-K: implementar VIA B (YouTube Data API v3) primero. "
            f"{long_note} Costo: API key restringida por IP de la VPS, cuota gratis "
            "10k unidades/día (1 unidad por videos.list). Sin transcript: si el "
            "transcript es requisito duro, complementar con VIA A más adelante."
        )
    if not a_blocked and a_useful_pct >= 50:
        return (
            "RECOMENDACIÓN 013-K: VIA A parcial. Cobertura "
            f"{a_useful_pct:.0f}% < 75% — implementar VIA A pero con fallback a stub "
            "controlado por video. Resolver bloqueos antes de declarar canal=youtube "
            "production-ready."
        )
    return (
        "RECOMENDACIÓN 013-K: bloqueado. Ninguna vía supera 75% de cobertura útil con "
        "la muestra disponible. Resolver blockers listados abajo (API key Data API, "
        "estado VM) antes de implementar Stage 2 para canal=youtube."
    )


# --------------------------------------------------------------------------- #
# Main
# --------------------------------------------------------------------------- #


def render_markdown(report: dict[str, Any]) -> str:
    summary = report["summary"]
    blockers = report["blockers"]
    lines: list[str] = []
    lines.append("# Spike 013-K — VM + YouTube Data API")
    lines.append("")
    lines.append(f"- Started: `{report['started']}`")
    lines.append(f"- Finished: `{report['finished']}`")
    lines.append(f"- Source sample (013-J ids): `{report['source_report']}`")
    lines.append(f"- Sample size: {summary['sample_size']}")
    lines.append(
        f"- VM health: ok={report['vm_health'].get('ok')} "
        f"version={report['vm_health'].get('version')} "
        f"has_browser_navigate={report['vm_health'].get('has_browser_navigate')} "
        f"has_yt_dlp_task={report['vm_health'].get('has_yt_dlp_task')}"
    )
    lines.append(
        f"- Data API key present: {report['data_api_key_present']}"
    )
    lines.append("")
    lines.append("## Comparison")
    lines.append("")
    lines.append(comparison_table_md(summary, blockers))
    lines.append("")
    lines.append("## Blockers")
    lines.append("")
    if blockers["via_a"]:
        lines.append("**VIA A:**")
        for b in blockers["via_a"]:
            lines.append(f"- {b}")
    else:
        lines.append("**VIA A:** ninguno detectado.")
    lines.append("")
    if blockers["via_b"]:
        lines.append("**VIA B:**")
        for b in blockers["via_b"]:
            lines.append(f"- {b}")
    else:
        lines.append("**VIA B:** ninguno detectado.")
    lines.append("")
    lines.append("## Useful fields by source")
    lines.append("")
    lines.append(
        "- VIA A (residential-IP signal via `browser.navigate`): presence of "
        "`ytInitialPlayerResponse`, absence of bot wall. NOT a full extraction; "
        "confirms that adding a `youtube.fetch` task on the VM (yt-dlp + "
        "youtube-transcript-api) would have access to the real player + transcripts."
    )
    lines.append(
        "- VIA B (Data API `videos?part=snippet,contentDetails,statistics`): "
        "title, description, tags, channelId, channelTitle, publishedAt, "
        "duration (ISO 8601 → seconds), viewCount, likeCount, commentCount, "
        "defaultLanguage, defaultAudioLanguage, categoryId. Does **not** include "
        "captions/transcript (separate Captions API endpoint with different scopes)."
    )
    lines.append("")
    lines.append("## Recommendation")
    lines.append("")
    lines.append(report["recommendation"])
    lines.append("")
    lines.append("## Per-video results")
    lines.append("")
    lines.append("| sqlite_id | video_id | VIA A useful | VIA A bot_wall | VIA B ok | VIA B desc_len | VIA B duration_s |")
    lines.append("| --- | --- | --- | --- | --- | --- | --- |")
    for it in report["items"]:
        a = it.get("via_a_vm_browser") or {}
        b = it.get("via_b_data_api") or {}
        bf = (b.get("fields") or {}) if isinstance(b, dict) else {}
        lines.append(
            f"| {it.get('sqlite_id')} | `{it.get('video_id')}` | "
            f"{a.get('useful_for_extraction', '-')} | {a.get('has_bot_challenge', '-')} | "
            f"{b.get('ok', '-')} | {bf.get('description_len', '-')} | "
            f"{bf.get('duration_seconds', '-')} |"
        )
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--source-report", default=str(DEFAULT_SOURCE))
    ap.add_argument("--limit", type=int, default=DEFAULT_LIMIT)
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    ap.add_argument("--output", default=f"reports/spike-youtube-vm-dataapi-{ts}.json")
    ap.add_argument(
        "--skip-vm",
        action="store_true",
        help="Skip VIA A even if WORKER_URL_VM is set (for offline reruns).",
    )
    args = ap.parse_args(argv)

    source = Path(args.source_report)
    if not source.exists():
        print(f"Source report not found: {source}", file=sys.stderr)
        return 1
    targets = load_targets(source, args.limit)
    if not targets:
        print("No targets found in source report.", file=sys.stderr)
        return 1

    worker_url_vm = os.environ.get("WORKER_URL_VM", "")
    worker_token = os.environ.get("WORKER_TOKEN", "")
    api_key = os.environ.get("YOUTUBE_DATA_API_KEY", "")

    blockers: dict[str, list[str]] = {"via_a": [], "via_b": []}

    # VM health probe.
    vm_h: dict[str, Any]
    if args.skip_vm or not worker_url_vm:
        vm_h = {"ok": False, "skipped": True, "reason": "no WORKER_URL_VM or --skip-vm"}
        blockers["via_a"].append(
            "WORKER_URL_VM no configurado en el entorno o --skip-vm activo. "
            "Owner: Rick (verificar `~/.config/openclaw/env`)."
        )
    else:
        vm_h = vm_health(worker_url_vm, worker_token)
        if not vm_h.get("ok"):
            blockers["via_a"].append(
                f"VM worker /health falla: {vm_h.get('error')}. Owner: Rick "
                "(verificar VM Tailscale + servicio worker en Windows)."
            )
        else:
            if not vm_h.get("has_browser_navigate"):
                blockers["via_a"].append(
                    "VM worker no expone `browser.navigate` — no se puede probar "
                    "residential-IP signal. Owner: Rick."
                )
            if not vm_h.get("has_yt_dlp_task"):
                blockers["via_a"].append(
                    "VM worker no tiene tarea `youtube.fetch` registrada — esto es "
                    "la implementación esperada de 013-K (no es bloqueo del spike, "
                    "es el work-item resultante)."
                )

    if not api_key:
        blockers["via_b"].append(
            "YOUTUBE_DATA_API_KEY no presente. Owner: David — crear API key en "
            "Google Cloud Console (proyecto nuevo o existente), habilitar 'YouTube "
            "Data API v3', restringir por IP de la VPS, y exportar la variable en "
            "el systemd unit del dispatcher."
        )

    started = datetime.now(timezone.utc).isoformat()
    items: list[dict[str, Any]] = []
    can_run_via_a = vm_h.get("ok") and vm_h.get("has_browser_navigate") and not args.skip_vm
    for t in targets:
        vid = t["video_id"]
        print(f"  [{t['sqlite_id']}] {vid} ...", flush=True)
        item: dict[str, Any] = dict(t)
        if can_run_via_a:
            item["via_a_vm_browser"] = vm_probe_watch_page(
                worker_url_vm, worker_token, vid
            )
        else:
            item["via_a_vm_browser"] = {"ok": False, "skipped": True}
        if api_key:
            item["via_b_data_api"] = data_api_fetch(api_key, vid)
        else:
            item["via_b_data_api"] = {"ok": False, "skipped": True}
        items.append(item)

    finished = datetime.now(timezone.utc).isoformat()
    summary = summarize(items)

    # Post-run blocker derived from results: if the VM IP is also captcha-walled,
    # VIA A is INVALIDATED (not just "not implemented yet"). Record it as a
    # first-class blocker so the .md is unambiguous.
    via_a_redirect_pct = summary["via_a_vm_browser"].get("redirected_to_sorry_pct") or 0
    if can_run_via_a and via_a_redirect_pct >= 50:
        blockers["via_a"].insert(
            0,
            f"VM IP también bloqueado por Google: "
            f"{summary['via_a_vm_browser']['redirected_to_sorry']}/"
            f"{summary['sample_size']} requests redirigidos a "
            "`google.com/sorry/index?...` (reCAPTCHA). El supuesto 'IP residencial "
            "de la VM destraba YouTube' NO se cumple con esta VM. Owner: Rick — "
            "evaluar proxy residencial pago, cookies de browser real, o descartar "
            "VIA A definitivamente. Mientras tanto, VIA A NO es una solución para "
            "013-K.",
        )

    report = {
        "spike": "013-K",
        "started": started,
        "finished": finished,
        "source_report": str(source),
        "sample_limit": args.limit,
        "vm_health": vm_h,
        "data_api_key_present": bool(api_key),
        "summary": summary,
        "blockers": blockers,
        "recommendation": build_recommendation(summary, blockers),
        "items": items,
    }

    out_json = Path(args.output)
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(json.dumps(report, indent=2, ensure_ascii=False))
    out_md = out_json.with_suffix(".md")
    out_md.write_text(render_markdown(report))

    print(json.dumps(summary, indent=2))
    print()
    print(report["recommendation"])
    print(f"\nReport JSON: {out_json}")
    print(f"Report MD:   {out_md}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
