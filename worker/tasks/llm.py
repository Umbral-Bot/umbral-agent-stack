"""
Tasks: multi-provider LLM generation.

- llm.generate: generate text using Gemini, OpenAI, or Anthropic.
"""

from __future__ import annotations

import json
import logging
import os
import urllib.error
import urllib.request
from typing import Any, Callable, Dict

logger = logging.getLogger("worker.tasks.llm")

DEFAULT_MODEL = "gemini-2.5-flash"
GEMINI_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/models"
OPENAI_CHAT_COMPLETIONS_URL = "https://api.openai.com/v1/chat/completions"
ANTHROPIC_MESSAGES_URL = "https://api.anthropic.com/v1/messages"

# Router aliases (quota providers) -> concrete API models.
MODEL_ALIASES = {
    "gemini_pro": "gemini-2.5-flash",
    "chatgpt_plus": "gpt-4o",
    "claude_pro": "claude-sonnet-4-20250514",
    "copilot_pro": "gpt-4o-mini",
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
    provider = _detect_provider(model)

    max_tokens = int(input_data.get("max_tokens", 1024))
    temperature = float(input_data.get("temperature", 0.7))
    system_prompt = str(input_data.get("system", ""))

    provider_fn = PROVIDERS.get(provider, _call_gemini)
    return provider_fn(
        prompt=prompt,
        model=model,
        max_tokens=max_tokens,
        temperature=temperature,
        system_prompt=system_prompt,
    )


def _detect_provider(model: str) -> str:
    """Infer provider from model name."""
    model_lc = (model or "").lower()
    if "gemini" in model_lc:
        return "gemini"
    if "gpt" in model_lc or "o1" in model_lc or "o3" in model_lc or "chatgpt" in model_lc or "copilot" in model_lc:
        return "openai"
    if "claude" in model_lc:
        return "anthropic"
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


PROVIDERS: Dict[str, Callable[..., Dict[str, Any]]] = {
    "gemini": _call_gemini,
    "openai": _call_openai,
    "anthropic": _call_anthropic,
}
