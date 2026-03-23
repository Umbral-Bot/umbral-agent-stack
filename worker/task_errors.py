"""Structured task execution errors for Worker handlers."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class TaskExecutionError(RuntimeError):
    """Typed task failure that the Worker can translate into an HTTP response."""

    detail: str
    status_code: int = 500
    error_code: str = "task_execution_failed"
    error_kind: str = "execution"
    retryable: bool = False
    provider: str | None = None
    upstream_status: int | None = None

    def __post_init__(self) -> None:
        super().__init__(self.detail)

    def response_payload(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "detail": self.detail,
            "error_code": self.error_code,
            "error_kind": self.error_kind,
            "retryable": self.retryable,
        }
        if self.provider:
            payload["provider"] = self.provider
        if self.upstream_status is not None:
            payload["upstream_status"] = self.upstream_status
        return payload

    def log_message(self) -> str:
        return f"[{self.error_code}] {self.detail}"
