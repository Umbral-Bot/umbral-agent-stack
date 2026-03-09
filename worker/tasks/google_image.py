"""
Tasks: image generation via Google's Gemini image-capable models.

- google.image.generate: generate one or more images with Gemini image models.
"""

from __future__ import annotations

import base64
import json
import logging
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any, Dict, Iterable

from .llm import _safe_http_error_body

logger = logging.getLogger("worker.tasks.google_image")

GOOGLE_API_URL_TMPL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
DEFAULT_MODEL = "gemini-3-pro-image-preview"
DEFAULT_SIZE = "1024x1024"
DEFAULT_OUTPUT_DIR = "artifacts/generated_images"
MODEL_ALIASES = {
    "nano-banana-pro-preview": DEFAULT_MODEL,
    "nano-banana-pro": DEFAULT_MODEL,
    "nano_banana_pro": DEFAULT_MODEL,
    "gemini-3-pro-image-preview": DEFAULT_MODEL,
    "gemini-3.1-pro-image-preview": DEFAULT_MODEL,
    "gemini-3.1-flash-image-preview": "gemini-3.1-flash-image-preview",
    "gemini-2.5-flash-image": "gemini-2.5-flash-image",
    "gemini-2.0-flash-exp-image-generation": "gemini-2.0-flash-exp-image-generation",
}


def _resolve_api_key() -> str:
    key = os.environ.get("GOOGLE_API_KEY_NANO", "").strip() or os.environ.get("GOOGLE_API_KEY", "").strip()
    if not key:
        raise RuntimeError("Google image API no configurada (GOOGLE_API_KEY_NANO / GOOGLE_API_KEY)")
    return key


def _resolve_model(model: str) -> str:
    clean = (model or "").strip()
    if not clean:
        return DEFAULT_MODEL
    return MODEL_ALIASES.get(clean.lower(), clean)


def _image_extension(mime_type: str) -> str:
    mime = (mime_type or "").lower()
    if "jpeg" in mime or "jpg" in mime:
        return ".jpg"
    if "webp" in mime:
        return ".webp"
    return ".png"


def _build_payload(prompt: str, size: str) -> Dict[str, Any]:
    return {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "responseModalities": ["TEXT", "IMAGE"],
            "imageConfig": {"aspectRatio": _size_to_aspect_ratio(size)},
        },
    }


def _size_to_aspect_ratio(size: str) -> str:
    clean = (size or DEFAULT_SIZE).strip().lower()
    mapping = {
        "1024x1024": "1:1",
        "1536x1024": "3:2",
        "1024x1536": "2:3",
        "1792x1024": "16:9",
        "1024x1792": "9:16",
    }
    return mapping.get(clean, "1:1")


def _iter_inline_images(payload: Dict[str, Any]) -> Iterable[Dict[str, str]]:
    for candidate in payload.get("candidates", []):
        content = candidate.get("content", {})
        if not isinstance(content, dict):
            continue
        for part in content.get("parts", []):
            if not isinstance(part, dict):
                continue
            inline = part.get("inlineData")
            if isinstance(inline, dict) and inline.get("data"):
                yield {
                    "mime_type": str(inline.get("mimeType") or "image/png"),
                    "b64_json": str(inline["data"]),
                }


def _generate_single(prompt: str, model: str, size: str) -> Dict[str, str]:
    api_key = _resolve_api_key()
    url = (
        GOOGLE_API_URL_TMPL.format(model=urllib.parse.quote(model, safe=""))
        + f"?key={urllib.parse.quote(api_key)}"
    )
    req = urllib.request.Request(
        url,
        data=json.dumps(_build_payload(prompt, size)).encode("utf-8"),
        method="POST",
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            data = json.loads(resp.read().decode())
    except urllib.error.HTTPError as exc:
        body_str = _safe_http_error_body(exc)
        raise RuntimeError(f"Google image API error {exc.code}: {body_str}")
    except Exception as exc:
        raise RuntimeError(f"Google image generation failed: {str(exc)[:300]}")

    images = list(_iter_inline_images(data))
    if not images:
        raise RuntimeError(f"No images returned by Google image API: {json.dumps(data)[:500]}")
    return images[0]


def handle_google_image_generate(input_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Generate images through Google's Gemini image-capable models.

    Input:
        prompt (str, required): Prompt text for image generation.
        model (str, optional): Image model. Default gemini-3-pro-image-preview.
        size (str, optional): Output size hint, e.g. 1024x1024 or 1536x1024.
        n (int, optional): Number of images, 1-4. Implemented as repeated calls.
        output_dir (str, optional): Directory where generated files are saved.
        filename_prefix (str, optional): Prefix for saved files.
        return_b64 (bool, optional): Include base64 in the response. Default false.
    """
    prompt = str(input_data.get("prompt", "")).strip()
    if not prompt:
        raise ValueError("'prompt' is required and cannot be empty")

    n = int(input_data.get("n", 1))
    if n < 1 or n > 4:
        raise ValueError("'n' must be between 1 and 4")

    model = _resolve_model(str(input_data.get("model") or DEFAULT_MODEL))
    size = str(input_data.get("size") or DEFAULT_SIZE).strip()
    output_dir = str(input_data.get("output_dir") or DEFAULT_OUTPUT_DIR).strip()
    filename_prefix = str(input_data.get("filename_prefix") or "generated-image").strip() or "generated-image"
    return_b64 = bool(input_data.get("return_b64", False))

    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = int(time.time())
    images = []
    for idx in range(1, n + 1):
        item = _generate_single(prompt, model, size)
        image_bytes = base64.b64decode(item["b64_json"])
        mime_type = item["mime_type"]
        output_path = out_dir / f"{filename_prefix}-{stamp}-{idx}{_image_extension(mime_type)}"
        output_path.write_bytes(image_bytes)
        entry: Dict[str, Any] = {
            "index": idx,
            "output_path": str(output_path),
            "mime_type": mime_type,
            "size_bytes": len(image_bytes),
        }
        if return_b64:
            entry["b64_json"] = item["b64_json"]
        images.append(entry)

    logger.info(
        "Google image generated: model=%s n=%d size=%s output_dir=%s",
        model,
        len(images),
        size,
        out_dir,
    )
    return {
        "ok": True,
        "model": model,
        "size": size,
        "count": len(images),
        "images": images,
    }
