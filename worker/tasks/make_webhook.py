"""
Tasks: Make.com Webhook Integration.

- make.post_webhook: envía datos a un webhook de Make.com.
"""

import json
import logging
import urllib.request
import urllib.error
from typing import Any, Dict

logger = logging.getLogger("worker.tasks.make_webhook")

# Allowed URL prefixes for webhook destinations (security)
ALLOWED_URL_PREFIXES = (
    "https://hook.make.com/",
    "https://hook.eu1.make.com/",
    "https://hook.eu2.make.com/",
    "https://hook.us1.make.com/",
    "https://hook.us2.make.com/",
)


def handle_make_post_webhook(input_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Envía datos a un webhook de Make.com via HTTP POST.

    Input:
        webhook_url (str, required): URL del webhook de Make.com.
        payload (dict, required): datos a enviar como JSON body.
        timeout (int, optional): timeout en segundos (default: 30).

    Returns:
        {"ok": bool, "status_code": int, "response": str}
    """
    webhook_url = str(input_data.get("webhook_url", "")).strip()
    if not webhook_url:
        raise ValueError("'webhook_url' is required and cannot be empty")

    # Validate URL is a Make.com webhook
    if not any(webhook_url.startswith(prefix) for prefix in ALLOWED_URL_PREFIXES):
        raise ValueError(
            f"webhook_url must start with one of: {', '.join(ALLOWED_URL_PREFIXES)}"
        )

    payload = input_data.get("payload")
    if payload is None:
        raise ValueError("'payload' is required")
    if not isinstance(payload, dict):
        raise ValueError("'payload' must be a dict")

    timeout = int(input_data.get("timeout", 30))
    if timeout < 1 or timeout > 120:
        raise ValueError("'timeout' must be between 1 and 120 seconds")

    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")

    req = urllib.request.Request(
        webhook_url,
        data=body,
        method="POST",
        headers={
            "Content-Type": "application/json",
            "User-Agent": "UmbralWorker/0.4.0",
        },
    )

    logger.info(
        "Posting to Make.com webhook: %s (%d bytes)",
        webhook_url[:60] + "...",
        len(body),
    )

    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            status_code = resp.status
            response_text = resp.read().decode("utf-8", errors="replace")
            logger.info(
                "Make.com webhook responded: %d (%d chars)",
                status_code,
                len(response_text),
            )
            return {
                "ok": True,
                "status_code": status_code,
                "response": response_text[:2000],
            }
    except urllib.error.HTTPError as exc:
        error_body = ""
        try:
            error_body = exc.read().decode("utf-8", errors="replace")[:500]
        except Exception:
            pass
        logger.warning(
            "Make.com webhook HTTP error %d: %s", exc.code, error_body[:200]
        )
        return {
            "ok": False,
            "status_code": exc.code,
            "response": error_body,
        }
    except urllib.error.URLError as exc:
        logger.error("Make.com webhook URL error: %s", exc.reason)
        raise RuntimeError(f"Webhook connection failed: {exc.reason}") from exc
    except TimeoutError:
        logger.error("Make.com webhook timed out after %ds", timeout)
        raise RuntimeError(f"Webhook timed out after {timeout}s")
