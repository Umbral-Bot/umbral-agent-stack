"""
smoke_agenteub_kb.py — O16.2/051 smoke "bot cita KB version + URL".

Invoca el AgenteUB productivo (`umbralbim-resource`) vía Responses API con un
prompt sobre IFC 4.3 / IfcWall y valida que la respuesta contenga:
  (a) substring `aeco-kb-es-v` (version KB visible en la cita).
  (b) ≥1 URL HTTP/HTTPS (cita a fuente buildingSMART o seed equivalente).

Auth: DefaultAzureCredential con scope `https://ai.azure.com/.default`.

Exit 0 si pasa, 1 si no cumple criterios.

Uso:
    python scripts/aeco-kb/smoke_agenteub_kb.py
"""

from __future__ import annotations

import argparse
import logging
import re
import sys

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("aeco-smoke-agenteub")

DEFAULT_ENDPOINT = (
    "https://umbralbim-resource.services.ai.azure.com"
    "/api/projects/umbralbim/applications/AgenteUB/protocols/openai/responses"
)
DEFAULT_PROMPT = "¿Qué dice IFC 4.3 sobre IfcWall según buildingSMART? Citá fuente y versión KB."

VERSION_PATTERN = re.compile(r"aeco-kb-es-v\d{8}")
URL_PATTERN = re.compile(r"https?://[^\s)\]]+")


def extract_text(payload: dict) -> str:
    chunks: list[str] = []
    for item in payload.get("output", []):
        for content in item.get("content", []):
            t = content.get("text")
            if t:
                chunks.append(t)
    return "\n".join(chunks)


def run(endpoint: str, prompt: str) -> int:
    import httpx
    from azure.identity import DefaultAzureCredential

    cred = DefaultAzureCredential()
    token = cred.get_token("https://ai.azure.com/.default").token

    body = {
        "model": "AgenteUB",
        "input": [{"role": "user", "content": prompt}],
        "stream": False,
    }

    log.info("Smoke prompt: %s", prompt)
    with httpx.Client(timeout=120) as client:
        r = client.post(endpoint, headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }, json=body)
        if r.status_code >= 400:
            log.error("Responses API failed: %d %s", r.status_code, r.text[:500])
            return 1
        text = extract_text(r.json())

    if not text:
        log.error("Bot returned empty text.")
        return 1

    log.info("Bot response (%d chars):\n%s", len(text), text[:1500])

    failures: list[str] = []
    if not VERSION_PATTERN.search(text):
        failures.append("missing KB version tag (aeco-kb-es-vYYYYMMDD)")
    urls = URL_PATTERN.findall(text)
    if not urls:
        failures.append("no source URL cited")
    else:
        log.info("URLs cited: %s", urls)

    if failures:
        log.error("SMOKE FAIL: %s", "; ".join(failures))
        return 1

    log.info("SMOKE PASS — bot cita versión KB + URL fuente.")
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--endpoint", default=DEFAULT_ENDPOINT)
    p.add_argument("--prompt", default=DEFAULT_PROMPT)
    args = p.parse_args(argv)
    return run(args.endpoint, args.prompt)


if __name__ == "__main__":
    sys.exit(main())
