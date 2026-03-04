"""
Tasks: multi-provider LLM generation.

- llm.generate: generate text via múltiples proveedores LLM.

Inventario de modelos disponibles:

  Anthropic (ANTHROPIC_API_KEY — token de sesión Pro):
    claude-haiku-4-5, claude-opus-4-6, claude-sonnet-4-6

  OpenAI (AZURE_OPENAI_* o GITHUB_TOKEN como fallback):
    gpt-5.2, gpt-5.3-codex (default/prioridad máxima)

  Google AI Studio (GOOGLE_API_KEY):
    gemini-3.1-pro-preview-customtools (mejor), gemini-3.1-pro-preview,
    gemini-flash-latest, gemini-flash-lite-latest

  Google Vertex AI (GOOGLE_API_KEY_RICK_UMBRAL + GOOGLE_CLOUD_PROJECT_RICK_UMBRAL):
    gemini-3.1-pro-preview

  Azure AI Foundry (AZURE_OPENAI_ENDPOINT + AZURE_OPENAI_API_KEY):
    gpt-5.3-codex (deployment dedicado con cuota Azure)

Provider selection:
  OpenAI/Codex: azure_foundry → openai nativo (OPENAI_API_KEY)
              NOTA: gpt-5.3-codex y gpt-5.2 vía OAuth de ChatGPT Plus solo funcionan
              en OpenClaw (Telegram). El Worker los accede por Azure AI Foundry.
  Claude:       anthropic nativo (ANTHROPIC_API_KEY — token sesión Pro)
  Gemini:       gemini (AI Studio) o vertex (si alias contiene "vertex")
"""

from __future__ import annotations

import json
import logging
import os
import time
import urllib.error
import urllib.request
from typing import Any, Callable, Dict

from worker.tracing import trace_llm_call

logger = logging.getLogger("worker.tasks.llm")

DEFAULT_MODEL = "gemini-3.1-pro-preview-customtools"
GEMINI_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/models"
OPENAI_CHAT_COMPLETIONS_URL = "https://api.openai.com/v1/chat/completions"
ANTHROPIC_MESSAGES_URL = "https://api.anthropic.com/v1/messages"
AZURE_OPENAI_DEFAULT_API_VERSION = "2024-12-01-preview"
# Vertex AI: {REGION}-aiplatform.googleapis.com
VERTEX_DEFAULT_REGION = "us-central1"

# Router aliases → modelos reales.
# Cada alias mapea a un nombre de modelo concreto que el provider entiende.
MODEL_ALIASES = {
    # --- OpenAI / Codex (Worker: Azure Foundry → OPENAI_API_KEY) ---
    "azure_foundry": "gpt-5.3-codex",
    # --- Anthropic (ANTHROPIC_API_KEY — token de sesión Pro) ---
    "claude_pro":    "claude-sonnet-4-6",
    "claude_opus":   "claude-opus-4-6",
    "claude_haiku":  "claude-haiku-4-5",
    # --- Google AI Studio (GOOGLE_API_KEY) ---
    "gemini_pro":       "gemini-3.1-pro-preview-customtools",   # mejor Gemini
    "gemini_flash":     "gemini-flash-latest",
    "gemini_flash_lite": "gemini-flash-lite-latest",
    # --- Google Vertex AI (GOOGLE_API_KEY_RICK_UMBRAL + PROJECT) ---
    "gemini_vertex":    "gemini-3.1-pro-preview",
}


def handle_llm_generate(input_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Generate text using Gemini/OpenAI/Anthropic.

    Input:
        prompt (str, required): Prompt text for the model.
        model (str, optional): Model name (provider is inferred from this value).
        selected_model (str, optional): Backward-compat alias from Dispatcher.
        max_tokens (int, optional): Response token limit (default: 1024).
        temperature (float, optional): Sampling temperature (default: 0.7).
        system (str, optional): System prompt.

    Returns:
        {"text": "...", "model": "...", "usage": {...}}
    """
    prompt = str(input_data.get("prompt", "")).strip()
    if not prompt:
        raise ValueError("'prompt' is required and cannot be empty")

    requested_model = str(
        input_data.get("model")
        or input_data.get("selected_model")
        or DEFAULT_MODEL
    ).strip()
    model = _resolve_model_alias(requested_model)
    provider = _detect_provider(model, requested_alias=requested_model)

    max_tokens = int(input_data.get("max_tokens", 1024))
    temperature = float(input_data.get("temperature", 0.7))
    system_prompt = str(input_data.get("system", ""))

    provider_fn = PROVIDERS.get(provider, _call_gemini)
    t0 = time.monotonic()
    result = provider_fn(
        prompt=prompt,
        model=model,
        max_tokens=max_tokens,
        temperature=temperature,
        system_prompt=system_prompt,
    )
    duration_ms = (time.monotonic() - t0) * 1000.0

    try:
        trace_llm_call(
            model=model,
            provider=provider,
            prompt=prompt,
            system=system_prompt,
            response_text=str(result.get("text", "")),
            usage=result.get("usage", {}) or {},
            duration_ms=duration_ms,
            task_id=input_data.get("_task_id"),
            task_type=input_data.get("_task_type"),
        )
    except Exception:
        logger.warning("Tracing call failed unexpectedly", exc_info=True)

    return result


def _detect_provider(model: str, *, requested_alias: str = "") -> str:
    """
    Infer provider from model name + optional alias hint.

    Gemini:   alias contiene "vertex" → vertex; sino → gemini (AI Studio)
    OpenAI:   azure_foundry → openai nativo (OPENAI_API_KEY)
              NOTA: GITHUB_TOKEN es solo para git (pull/push), NO para LLM.
              gpt-5.3-codex y gpt-5.2 son accesibles vía OAuth de ChatGPT Plus
              (OpenClaw), pero el Worker solo los alcanza vía Azure AI Foundry.
    Claude:   anthropic nativo (ANTHROPIC_API_KEY — token sesión Pro)
    """
    model_lc = (model or "").lower()
    alias_lc = (requested_alias or "").lower()

    if "gemini" in model_lc:
        if "vertex" in alias_lc or "vertex" in model_lc:
            return "vertex"
        return "gemini"

    is_openai_model = (
        "gpt" in model_lc
        or "o1" in model_lc
        or "o3" in model_lc
        or "codex" in model_lc
        or "chatgpt" in model_lc
        or "copilot" in model_lc
    )
    is_anthropic_model = "claude" in model_lc

    if is_openai_model:
        if (os.environ.get("AZURE_OPENAI_ENDPOINT", "").strip()
                and os.environ.get("AZURE_OPENAI_API_KEY", "").strip()):
            return "azure_foundry"
        if os.environ.get("OPENAI_API_KEY", "").strip():
            return "openai"
        raise RuntimeError(
            "Modelos OpenAI/Codex requieren Azure AI Foundry (AZURE_OPENAI_ENDPOINT + "
            "AZURE_OPENAI_API_KEY) o OPENAI_API_KEY. "
            "gpt-5.3-codex vía OAuth de ChatGPT Plus solo funciona en OpenClaw, "
            "no directamente desde el Worker."
        )

    if is_anthropic_model:
        if os.environ.get("ANTHROPIC_API_KEY", "").strip():
            return "anthropic"
        raise RuntimeError(
            "Modelos Claude requieren ANTHROPIC_API_KEY (token de sesión Pro). "
            "Agregála en ~/.config/openclaw/env"
        )

    return "gemini"


def _resolve_model_alias(model: str) -> str:
    if not model:
        return DEFAULT_MODEL
    return MODEL_ALIASES.get(model.lower(), model)


def _call_gemini(
    *,
    prompt: str,
    model: str,
    max_tokens: int,
    temperature: float,
    system_prompt: str,
) -> Dict[str, Any]:
    key = os.environ.get("GOOGLE_API_KEY", "").strip()
    if not key:
        raise RuntimeError("GOOGLE_API_KEY not configured")

    contents = []
    if system_prompt:
        contents.append({"role": "user", "parts": [{"text": system_prompt}]})
        contents.append({"role": "model", "parts": [{"text": "Entendido."}]})
    contents.append({"role": "user", "parts": [{"text": prompt}]})

    payload = {
        "contents": contents,
        "generationConfig": {
            "maxOutputTokens": max_tokens,
            "temperature": temperature,
        },
    }

    url = f"{GEMINI_BASE_URL}/{model}:generateContent?key={key}"
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        method="POST",
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = json.loads(resp.read().decode())
    except urllib.error.HTTPError as exc:
        body_str = _safe_http_error_body(exc)
        raise RuntimeError(f"Gemini API error {exc.code}: {body_str}")
    except Exception as exc:
        raise RuntimeError(f"Gemini generation failed: {str(exc)[:300]}")

    candidates = data.get("candidates", [])
    if not candidates:
        raise RuntimeError("No candidates in Gemini response")
    text = ""
    for part in candidates[0].get("content", {}).get("parts", []):
        text += part.get("text", "")

    usage = data.get("usageMetadata", {})
    return {
        "text": text,
        "model": model,
        "usage": {
            "prompt_tokens": usage.get("promptTokenCount", 0),
            "completion_tokens": usage.get("candidatesTokenCount", 0),
            "total_tokens": usage.get("totalTokenCount", 0),
        },
    }


def _call_openai(
    *,
    prompt: str,
    model: str,
    max_tokens: int,
    temperature: float,
    system_prompt: str,
) -> Dict[str, Any]:
    key = os.environ.get("OPENAI_API_KEY", "").strip()
    if not key:
        raise RuntimeError("OPENAI_API_KEY not configured")

    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})

    payload: Dict[str, Any] = {
        "model": model,
        "messages": messages,
        "max_tokens": max_tokens,
        "temperature": temperature,
    }
    # Reasoning models commonly use max_completion_tokens and ignore temperature.
    if model.startswith("o1") or model.startswith("o3"):
        payload.pop("max_tokens", None)
        payload.pop("temperature", None)
        payload["max_completion_tokens"] = max_tokens

    req = urllib.request.Request(
        OPENAI_CHAT_COMPLETIONS_URL,
        data=json.dumps(payload).encode("utf-8"),
        method="POST",
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {key}",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = json.loads(resp.read().decode())
    except urllib.error.HTTPError as exc:
        body_str = _safe_http_error_body(exc)
        raise RuntimeError(f"OpenAI API error {exc.code}: {body_str}")
    except Exception as exc:
        raise RuntimeError(f"OpenAI generation failed: {str(exc)[:300]}")

    choices = data.get("choices", [])
    if not choices:
        raise RuntimeError("No choices in OpenAI response")
    message = choices[0].get("message", {})
    text = _extract_openai_text(message.get("content", ""))

    usage = data.get("usage", {})
    return {
        "text": text,
        "model": model,
        "usage": {
            "prompt_tokens": usage.get("prompt_tokens", 0),
            "completion_tokens": usage.get("completion_tokens", 0),
            "total_tokens": usage.get("total_tokens", 0),
        },
    }


def _call_anthropic(
    *,
    prompt: str,
    model: str,
    max_tokens: int,
    temperature: float,
    system_prompt: str,
) -> Dict[str, Any]:
    key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
    if not key:
        raise RuntimeError("ANTHROPIC_API_KEY not configured")

    payload: Dict[str, Any] = {
        "model": model,
        "max_tokens": max_tokens,
        "temperature": temperature,
        "messages": [{"role": "user", "content": prompt}],
    }
    if system_prompt:
        payload["system"] = system_prompt

    req = urllib.request.Request(
        ANTHROPIC_MESSAGES_URL,
        data=json.dumps(payload).encode("utf-8"),
        method="POST",
        headers={
            "Content-Type": "application/json",
            "x-api-key": key,
            "anthropic-version": "2023-06-01",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = json.loads(resp.read().decode())
    except urllib.error.HTTPError as exc:
        body_str = _safe_http_error_body(exc)
        raise RuntimeError(f"Anthropic API error {exc.code}: {body_str}")
    except Exception as exc:
        raise RuntimeError(f"Anthropic generation failed: {str(exc)[:300]}")

    text_parts = []
    for block in data.get("content", []):
        if isinstance(block, dict) and block.get("type") == "text":
            text_parts.append(block.get("text", ""))
    text = "".join(text_parts)
    if not text:
        raise RuntimeError("No text in Anthropic response")

    usage = data.get("usage", {})
    prompt_tokens = usage.get("input_tokens", 0)
    completion_tokens = usage.get("output_tokens", 0)
    return {
        "text": text,
        "model": model,
        "usage": {
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": prompt_tokens + completion_tokens,
        },
    }


def _extract_openai_text(content: Any) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for item in content:
            if isinstance(item, dict):
                if item.get("type") == "text":
                    parts.append(str(item.get("text", "")))
                elif "content" in item:
                    parts.append(str(item.get("content", "")))
            else:
                parts.append(str(item))
        return "".join(parts)
    return str(content)


def _safe_http_error_body(exc: urllib.error.HTTPError) -> str:
    try:
        return exc.read().decode()[:300]
    except Exception:
        return ""


def _call_azure_foundry(
    *,
    prompt: str,
    model: str,
    max_tokens: int,
    temperature: float,
    system_prompt: str,
) -> Dict[str, Any]:
    """
    Azure AI Foundry (Azure OpenAI Service).

    Variables de entorno requeridas:
        AZURE_OPENAI_ENDPOINT  — endpoint del recurso, p.ej.:
            https://mi-recurso.openai.azure.com/
            https://mi-hub.services.ai.azure.com/
        AZURE_OPENAI_API_KEY   — API key del recurso
    Opcionales:
        AZURE_OPENAI_DEPLOYMENT — nombre del deployment (default = nombre del modelo)
        AZURE_OPENAI_API_VERSION — versión de la API (default: 2024-12-01-preview)
    """
    endpoint = os.environ.get("AZURE_OPENAI_ENDPOINT", "").strip().rstrip("/")
    api_key = os.environ.get("AZURE_OPENAI_API_KEY", "").strip()
    if not endpoint or not api_key:
        raise RuntimeError(
            "AZURE_OPENAI_ENDPOINT y AZURE_OPENAI_API_KEY requeridos para Azure AI Foundry. "
            "Agregálos en ~/.config/openclaw/env"
        )

    # Deployment: usar env var si está, sino el nombre del modelo
    deployment = os.environ.get("AZURE_OPENAI_DEPLOYMENT", model).strip() or model
    api_version = os.environ.get("AZURE_OPENAI_API_VERSION", AZURE_OPENAI_DEFAULT_API_VERSION)

    # Construir URL según tipo de endpoint
    if "services.ai.azure.com" in endpoint:
        # Azure AI Foundry Hub endpoint (nuevo)
        url = f"{endpoint}/models/{deployment}/chat/completions?api-version={api_version}"
    elif "/openai/deployments/" in endpoint:
        # Endpoint ya incluye el path del deployment
        url = f"{endpoint}?api-version={api_version}"
    else:
        # Azure OpenAI clásico
        url = f"{endpoint}/openai/deployments/{deployment}/chat/completions?api-version={api_version}"

    messages: list = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})

    payload: Dict[str, Any] = {
        "messages": messages,
        "max_tokens": max_tokens,
        "temperature": temperature,
    }
    # AI Foundry Hub requiere el campo "model" en el body
    if "services.ai.azure.com" in endpoint:
        payload["model"] = deployment
    # Reasoning models (o1, o3) no soportan temperature ni max_tokens estándar
    if any(x in model.lower() for x in ["o1", "o3"]):
        payload.pop("temperature", None)
        payload.pop("max_tokens", None)
        payload["max_completion_tokens"] = max_tokens

    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        method="POST",
        headers={
            "Content-Type": "application/json",
            "api-key": api_key,
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = json.loads(resp.read().decode())
    except urllib.error.HTTPError as exc:
        body_str = _safe_http_error_body(exc)
        raise RuntimeError(f"Azure Foundry API error {exc.code}: {body_str}")
    except Exception as exc:
        raise RuntimeError(f"Azure Foundry generation failed: {str(exc)[:300]}")

    choices = data.get("choices", [])
    if not choices:
        raise RuntimeError("No choices in Azure Foundry response")
    message = choices[0].get("message", {})
    text = _extract_openai_text(message.get("content", ""))

    usage = data.get("usage", {})
    return {
        "text": text,
        "model": deployment,
        "provider": "azure_foundry",
        "usage": {
            "prompt_tokens": usage.get("prompt_tokens", 0),
            "completion_tokens": usage.get("completion_tokens", 0),
            "total_tokens": usage.get("total_tokens", 0),
        },
    }


def _call_vertex(
    *,
    prompt: str,
    model: str,
    max_tokens: int,
    temperature: float,
    system_prompt: str,
) -> Dict[str, Any]:
    """
    Google Vertex AI — usa GOOGLE_API_KEY_RICK_UMBRAL + GOOGLE_CLOUD_PROJECT_RICK_UMBRAL.
    Endpoint REST: {REGION}-aiplatform.googleapis.com
    Misma interfaz generateContent que AI Studio pero autenticado con API key de Vertex.
    """
    api_key = os.environ.get("GOOGLE_API_KEY_RICK_UMBRAL", "").strip()
    project = os.environ.get("GOOGLE_CLOUD_PROJECT_RICK_UMBRAL", "").strip()
    if not api_key or not project:
        raise RuntimeError(
            "GOOGLE_API_KEY_RICK_UMBRAL y GOOGLE_CLOUD_PROJECT_RICK_UMBRAL requeridos para Vertex AI. "
            "Configurálos en ~/.config/openclaw/env"
        )

    region = os.environ.get("VERTEX_REGION", VERTEX_DEFAULT_REGION)
    # Limpiar prefijo "vertex:" si lo tiene
    clean_model = model.replace("vertex:", "").strip()
    if not clean_model:
        clean_model = "gemini-3.1-pro-preview"

    url = (
        f"https://{region}-aiplatform.googleapis.com/v1beta1/"
        f"projects/{project}/locations/{region}/"
        f"publishers/google/models/{clean_model}:generateContent"
    )

    contents = []
    if system_prompt:
        contents.append({"role": "user", "parts": [{"text": system_prompt}]})
        contents.append({"role": "model", "parts": [{"text": "Entendido."}]})
    contents.append({"role": "user", "parts": [{"text": prompt}]})

    payload = {
        "contents": contents,
        "generationConfig": {
            "maxOutputTokens": max_tokens,
            "temperature": temperature,
        },
    }

    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        method="POST",
        headers={
            "Content-Type": "application/json",
            "x-goog-api-key": api_key,
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = json.loads(resp.read().decode())
    except urllib.error.HTTPError as exc:
        body_str = _safe_http_error_body(exc)
        raise RuntimeError(f"Vertex AI API error {exc.code}: {body_str}")
    except Exception as exc:
        raise RuntimeError(f"Vertex AI generation failed: {str(exc)[:300]}")

    candidates = data.get("candidates", [])
    if not candidates:
        raise RuntimeError("No candidates in Vertex AI response")
    text = ""
    for part in candidates[0].get("content", {}).get("parts", []):
        text += part.get("text", "")

    usage = data.get("usageMetadata", {})
    return {
        "text": text,
        "model": clean_model,
        "provider": "vertex",
        "usage": {
            "prompt_tokens": usage.get("promptTokenCount", 0),
            "completion_tokens": usage.get("candidatesTokenCount", 0),
            "total_tokens": usage.get("totalTokenCount", 0),
        },
    }


PROVIDERS: Dict[str, Callable[..., Dict[str, Any]]] = {
    "gemini": _call_gemini,
    "vertex": _call_vertex,
    "azure_foundry": _call_azure_foundry,
    "openai": _call_openai,
    "anthropic": _call_anthropic,
}
