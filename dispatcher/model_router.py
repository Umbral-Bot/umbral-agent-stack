"""
ModelRouter — S4: selección de LLM por task_type y estado de cuotas.

Usa config/quota_policy.yaml (routing + umbrales). Fallback chain cuando
el preferido está en warn/restrict. Opción requires_approval cuando supera restrict.

Env vars:
    UMBRAL_DEFAULT_MODEL — override del modelo preferido para todos los task_types.
        Ejemplo: UMBRAL_DEFAULT_MODEL=claude_pro fuerza Claude como preferido.
        El fallback chain sigue aplicando si el override está en restrict.
        Si no se define, se usa el routing de quota_policy.yaml.
"""

import logging
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

from .quota_tracker import QuotaTracker

logger = logging.getLogger("dispatcher.model_router")


_PROVIDER_ENV_REQUIREMENTS: Dict[str, List[str]] = {
    "azure_foundry": ["AZURE_OPENAI_ENDPOINT", "AZURE_OPENAI_API_KEY"],
    "openclaw_proxy": ["OPENCLAW_GATEWAY_TOKEN"],
    "claude_pro":    ["ANTHROPIC_API_KEY"],
    "claude_opus":   ["ANTHROPIC_API_KEY"],
    "claude_haiku":  ["ANTHROPIC_API_KEY"],
    "gemini_pro":    ["GOOGLE_API_KEY"],
    "gemini_flash":  ["GOOGLE_API_KEY"],
    "gemini_flash_lite": ["GOOGLE_API_KEY"],
    "gemini_vertex": ["GOOGLE_API_KEY_RICK_UMBRAL", "GOOGLE_CLOUD_PROJECT_RICK_UMBRAL"],
}


def _is_truthy_env(name: str) -> bool:
    return os.environ.get(name, "").strip().lower() in {"1", "true", "yes", "on"}


def _get_disabled_providers() -> Set[str]:
    disabled: Set[str] = set()
    if _is_truthy_env("UMBRAL_DISABLE_CLAUDE"):
        disabled.update({"claude_pro", "claude_opus", "claude_haiku", "openclaw_proxy"})
    return disabled


def get_configured_providers() -> Set[str]:
    """Return providers whose required env vars are all set (non-empty)."""
    available: Set[str] = set()
    disabled = _get_disabled_providers()
    for provider, env_vars in _PROVIDER_ENV_REQUIREMENTS.items():
        if provider in disabled:
            continue
        if all(os.environ.get(v, "").strip() for v in env_vars):
            available.add(provider)
    return available

# Default si no hay YAML (doc 15)
DEFAULT_ROUTING = {
    "coding": {"preferred": "azure_foundry", "fallback_chain": ["claude_pro", "gemini_pro", "gemini_flash"]},
    "ms_stack": {"preferred": "azure_foundry", "fallback_chain": ["claude_pro", "gemini_pro"]},
    "writing": {"preferred": "claude_pro", "fallback_chain": ["azure_foundry", "gemini_pro"]},
    "research": {"preferred": "gemini_pro", "fallback_chain": ["azure_foundry", "gemini_vertex", "claude_pro", "gemini_flash"]},
    "critical": {"preferred": "claude_opus", "fallback_chain": ["azure_foundry", "claude_pro", "gemini_pro"]},
    "general": {"preferred": "azure_foundry", "fallback_chain": ["claude_pro", "gemini_pro", "gemini_flash"]},
    "light": {"preferred": "gemini_flash", "fallback_chain": ["gemini_flash_lite", "azure_foundry", "claude_haiku"]},
}

HIGH_PRIORITY_TASK_TYPES = ("critical",)  # pueden usar preferido hasta restrict


@dataclass
class ModelSelectionDecision:
    model: str
    reason: str
    requires_approval: bool = False


def _load_quota_policy() -> tuple[Dict[str, Dict], Dict[str, Dict], bool]:
    """Carga config/quota_policy.yaml; devuelve (routing, providers, auto_approve_quota)."""
    try:
        import yaml
    except ImportError:
        return DEFAULT_ROUTING, {}, False

    repo_root = Path(__file__).resolve().parent.parent
    path = repo_root / "config" / "quota_policy.yaml"
    if not path.is_file():
        return DEFAULT_ROUTING, {}, False

    try:
        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
    except Exception as e:
        logger.warning("Failed to load quota_policy.yaml: %s", e)
        return DEFAULT_ROUTING, {}, False

    if not isinstance(data, dict):
        return DEFAULT_ROUTING, {}, False
    routing = data.get("routing") or DEFAULT_ROUTING
    auto_approve = bool(data.get("auto_approve_quota", False))
    providers_raw = data.get("providers") or {}
    providers = {}
    for pid, cfg in providers_raw.items():
        if isinstance(cfg, dict):
            providers[pid] = {
                "limit_requests": cfg.get("limit_requests", 100),
                "window_seconds": cfg.get("window_seconds", 3600),
                "warn": float(cfg.get("warn", 0.8)),
                "restrict": float(cfg.get("restrict", 0.9)),
            }
    return routing, providers, auto_approve


def load_quota_policy() -> tuple[Dict[str, Dict], Dict[str, Dict]]:
    """Carga routing y providers desde config; para uso en servicio (QuotaTracker)."""
    routing, providers, _auto = _load_quota_policy()
    return routing, providers


class ModelRouter:
    """
    Selecciona modelo según task_type y cuotas.
    Usa QuotaTracker para estado actual y aplica fallback chain.
    """

    def __init__(self, quota_tracker: QuotaTracker):
        self.quota = quota_tracker
        self.routing, self.provider_config, self.auto_approve_quota = _load_quota_policy()
        self._configured = get_configured_providers()
        self._default_model = os.environ.get("UMBRAL_DEFAULT_MODEL", "").strip() or None
        if self._default_model:
            logger.info("UMBRAL_DEFAULT_MODEL override active: %s", self._default_model)
        if self.auto_approve_quota:
            logger.info("auto_approve_quota enabled — quota blocks will be auto-approved")
        logger.info("Configured providers: %s", sorted(self._configured) or "(none detected)")
        unconfigured = set(self.provider_config.keys()) - self._configured
        if unconfigured:
            logger.info("Unconfigured providers (will be skipped): %s", sorted(unconfigured))

    def _thresholds(self, provider: str) -> tuple[float, float]:
        warn = 0.8
        restrict = 0.9
        if provider in self.provider_config:
            cfg = self.provider_config[provider]
            warn = cfg.get("warn", warn)
            restrict = cfg.get("restrict", restrict)
        return warn, restrict

    def _normalize_task_type(self, task_type: str) -> str:
        task_type = task_type or "general"
        if task_type not in self.routing:
            return "general"
        return task_type

    def get_effective_route(self, task_type: str) -> Dict[str, Any]:
        """
        Return the route actually usable with the providers configured in env vars.

        The returned route keeps declared providers for observability, but promotes
        the first configured fallback when the declared preferred provider is absent.
        """
        normalized_task_type = self._normalize_task_type(task_type)
        route = self.routing[normalized_task_type]
        declared_preferred = route.get("preferred", "claude_pro")
        declared_fallback_chain: List[str] = list(route.get("fallback_chain") or [])

        preferred = declared_preferred
        fallback_chain = list(declared_fallback_chain)

        if self._default_model and self._default_model != preferred:
            if self._default_model in self._configured:
                if preferred not in fallback_chain:
                    fallback_chain = [preferred] + fallback_chain
                preferred = self._default_model
            else:
                logger.warning(
                    "UMBRAL_DEFAULT_MODEL='%s' is not configured; keeping declared route for task_type '%s'",
                    self._default_model,
                    normalized_task_type,
                )

        declared_candidates = [preferred] + fallback_chain
        unavailable = [provider for provider in declared_candidates if provider not in self._configured]

        if preferred not in self._configured:
            preferred = next((provider for provider in fallback_chain if provider in self._configured), "")

        effective_fallback_chain = [
            provider for provider in fallback_chain
            if provider in self._configured and provider != preferred
        ]

        return {
            "task_type": normalized_task_type,
            "declared_preferred": declared_preferred,
            "declared_fallback_chain": declared_fallback_chain,
            "preferred": preferred or None,
            "fallback_chain": effective_fallback_chain,
            "unconfigured": unavailable,
            "has_configured_route": bool(preferred),
        }

    def get_routing_snapshot(self) -> Dict[str, Dict[str, Any]]:
        """Return the effective route for every known task_type."""
        return {
            task_type: self.get_effective_route(task_type)
            for task_type in sorted(self.routing.keys())
        }

    def select_model(
        self,
        task_type: str,
        quota_state: Optional[Dict[str, float]] = None,
    ) -> ModelSelectionDecision:
        """
        Elige modelo para task_type. Si quota_state es None, usa QuotaTracker.get_all_quota_states().
        """
        route = self.get_effective_route(task_type)
        task_type = route["task_type"]
        preferred = route["preferred"] or ""
        fallback_chain: List[str] = route["fallback_chain"]

        if not preferred:
            logger.warning(
                "No configured providers available for task_type '%s' (declared preferred=%s, declared fallback=%s)",
                task_type,
                route["declared_preferred"],
                route["declared_fallback_chain"],
            )
            return ModelSelectionDecision(
                model="",
                reason="no_configured_provider",
                requires_approval=True,
            )

        if quota_state is None:
            quota_state = self.quota.get_all_quota_states()

        # Preferido bajo warn → usar
        state_preferred = quota_state.get(preferred, 0.0)
        warn_p, restrict_p = self._thresholds(preferred)
        if state_preferred < warn_p:
            return ModelSelectionDecision(model=preferred, reason="under_quota")
        if state_preferred < restrict_p:
            if task_type in HIGH_PRIORITY_TASK_TYPES:
                return ModelSelectionDecision(model=preferred, reason="high_priority_override")
            for model in fallback_chain:
                s = quota_state.get(model, 0.0)
                _, r = self._thresholds(model)
                if s < r:
                    return ModelSelectionDecision(model=model, reason="fallback_under_restrict")
            return ModelSelectionDecision(model=preferred, reason="fallback_over_restrict_use_preferred")

        # Preferido >= restrict
        if task_type in HIGH_PRIORITY_TASK_TYPES:
            if state_preferred < 1.0:
                return ModelSelectionDecision(model=preferred, reason="high_priority_override")
            if self.auto_approve_quota:
                logger.warning("Auto-approved quota-exceeded task (critical, model=%s)", preferred)
                return ModelSelectionDecision(model=preferred, reason="auto_approved_over_quota")
            return ModelSelectionDecision(
                model=preferred,
                reason="quota_exceeded",
                requires_approval=True,
            )
        for model in fallback_chain:
            s = quota_state.get(model, 0.0)
            _, r = self._thresholds(model)
            if s < r:
                return ModelSelectionDecision(model=model, reason="fallback_under_restrict")
        if self.auto_approve_quota:
            logger.warning("Auto-approved quota-exceeded task (model=%s)", preferred)
            return ModelSelectionDecision(model=preferred, reason="auto_approved_over_quota")
        return ModelSelectionDecision(
            model=preferred,
            reason="quota_exceeded",
            requires_approval=True,
        )
