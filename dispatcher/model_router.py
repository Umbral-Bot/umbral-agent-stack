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
from typing import Any, Dict, List, Optional

from .quota_tracker import QuotaTracker

logger = logging.getLogger("dispatcher.model_router")

# Default si no hay YAML (doc 15)
DEFAULT_ROUTING = {
    "coding": {"preferred": "chatgpt_plus", "fallback_chain": ["copilot_pro", "claude_pro", "gemini_pro"]},
    "ms_stack": {"preferred": "copilot_pro", "fallback_chain": ["chatgpt_plus", "claude_pro", "gemini_pro"]},
    "writing": {"preferred": "claude_pro", "fallback_chain": ["chatgpt_plus", "gemini_pro"]},
    "research": {"preferred": "gemini_pro", "fallback_chain": ["chatgpt_plus", "claude_pro"]},
    "critical": {"preferred": "claude_pro", "fallback_chain": ["chatgpt_plus"]},
    "general": {"preferred": "chatgpt_plus", "fallback_chain": ["claude_pro", "gemini_pro"]},
}

HIGH_PRIORITY_TASK_TYPES = ("critical",)  # pueden usar preferido hasta restrict


@dataclass
class ModelSelectionDecision:
    model: str
    reason: str
    requires_approval: bool = False


def _load_quota_policy() -> tuple[Dict[str, Dict], Dict[str, Dict]]:
    """Carga config/quota_policy.yaml; devuelve (routing, providers)."""
    try:
        import yaml
    except ImportError:
        return DEFAULT_ROUTING, {}

    repo_root = Path(__file__).resolve().parent.parent
    path = repo_root / "config" / "quota_policy.yaml"
    if not path.is_file():
        return DEFAULT_ROUTING, {}

    try:
        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
    except Exception as e:
        logger.warning("Failed to load quota_policy.yaml: %s", e)
        return DEFAULT_ROUTING, {}

    if not isinstance(data, dict):
        return DEFAULT_ROUTING, {}
    routing = data.get("routing") or DEFAULT_ROUTING
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
    return routing, providers


def load_quota_policy() -> tuple[Dict[str, Dict], Dict[str, Dict]]:
    """Carga routing y providers desde config; para uso en servicio (QuotaTracker)."""
    return _load_quota_policy()


class ModelRouter:
    """
    Selecciona modelo según task_type y cuotas.
    Usa QuotaTracker para estado actual y aplica fallback chain.
    """

    def __init__(self, quota_tracker: QuotaTracker):
        self.quota = quota_tracker
        self.routing, self.provider_config = _load_quota_policy()
        self._default_model = os.environ.get("UMBRAL_DEFAULT_MODEL", "").strip() or None
        if self._default_model:
            logger.info("UMBRAL_DEFAULT_MODEL override active: %s", self._default_model)

    def _thresholds(self, provider: str) -> tuple[float, float]:
        warn = 0.8
        restrict = 0.9
        if provider in self.provider_config:
            cfg = self.provider_config[provider]
            warn = cfg.get("warn", warn)
            restrict = cfg.get("restrict", restrict)
        return warn, restrict

    def select_model(
        self,
        task_type: str,
        quota_state: Optional[Dict[str, float]] = None,
    ) -> ModelSelectionDecision:
        """
        Elige modelo para task_type. Si quota_state es None, usa QuotaTracker.get_all_quota_states().
        """
        task_type = task_type or "general"
        if task_type not in self.routing:
            task_type = "general"
        route = self.routing[task_type]
        preferred = route.get("preferred", "chatgpt_plus")
        fallback_chain: List[str] = route.get("fallback_chain") or []

        # UMBRAL_DEFAULT_MODEL override: swap preferred, keep original as first fallback
        if self._default_model and self._default_model != preferred:
            if self._default_model in self.provider_config:
                if preferred not in fallback_chain:
                    fallback_chain = [preferred] + fallback_chain
                preferred = self._default_model
            else:
                logger.warning(
                    "UMBRAL_DEFAULT_MODEL='%s' not in provider config; ignoring override",
                    self._default_model,
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
            # Probar fallback
            for model in fallback_chain:
                s = quota_state.get(model, 0.0)
                _, r = self._thresholds(model)
                if s < r:
                    return ModelSelectionDecision(model=model, reason="fallback_under_restrict")
            # Ningún fallback bajo restrict → usar preferido igual (degradado)
            return ModelSelectionDecision(model=preferred, reason="fallback_over_restrict_use_preferred")

        # Preferido >= restrict
        if task_type in HIGH_PRIORITY_TASK_TYPES:
            if state_preferred < 1.0:
                return ModelSelectionDecision(model=preferred, reason="high_priority_override")
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
        return ModelSelectionDecision(
            model=preferred,
            reason="quota_exceeded",
            requires_approval=True,
        )
