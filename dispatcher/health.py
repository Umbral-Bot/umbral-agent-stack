"""
Dispatcher — Health Monitor para el Execution Plane (VM Windows).

Vigila la disponibilidad del Worker cada N segundos.
Cuando la VM está offline, activa modo degradado.
Cuando la VM vuelve, re-encola tareas bloqueadas.
"""

import logging
import threading
import time
from enum import Enum
from typing import Callable, Dict, Optional

import httpx

logger = logging.getLogger("dispatcher.health")


class SystemLevel(str, Enum):
    """Niveles de operación del sistema (ADR-003)."""
    NORMAL = "normal"       # Todos los componentes UP
    PARTIAL = "partial"     # VM offline, solo LLM + Notion
    LIMITED = "limited"     # VM offline + proveedor caído
    MINIMAL = "minimal"     # Solo VPS + OpenClaw


class HealthMonitor:
    """
    Monitorea la salud del Worker (VM) vía GET /health.

    Emite callbacks cuando cambia el nivel del sistema.
    3 checks fallidos consecutivos → VM offline.
    1 check exitoso → VM online.
    """

    def __init__(
        self,
        worker_url: str,
        worker_token: str,
        check_interval: int = 60,
        failure_threshold: int = 3,
        on_level_change: Optional[Callable[[SystemLevel, SystemLevel], None]] = None,
        on_vm_back: Optional[Callable[[], None]] = None,
    ):
        """
        Args:
            worker_url: URL base del worker (e.g. http://100.109.16.40:8088)
            worker_token: Bearer token para autenticar
            check_interval: segundos entre checks (default 60)
            failure_threshold: checks fallidos para declarar VM offline (default 3)
            on_level_change: callback(old_level, new_level) cuando cambia nivel
            on_vm_back: callback() cuando VM vuelve a estar online
        """
        self.worker_url = worker_url.rstrip("/")
        self.worker_token = worker_token
        self.check_interval = check_interval
        self.failure_threshold = failure_threshold
        self.on_level_change = on_level_change
        self.on_vm_back = on_vm_back

        self._consecutive_failures = 0
        self._level = SystemLevel.NORMAL
        self._vm_online = True
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._last_check: Optional[float] = None
        self._last_worker_version: Optional[str] = None

    @property
    def level(self) -> SystemLevel:
        return self._level

    @property
    def vm_online(self) -> bool:
        return self._vm_online

    @property
    def status(self) -> Dict:
        return {
            "level": self._level.value,
            "vm_online": self._vm_online,
            "consecutive_failures": self._consecutive_failures,
            "last_check": self._last_check,
            "last_worker_version": self._last_worker_version,
            "check_interval": self.check_interval,
            "failure_threshold": self.failure_threshold,
        }

    def check_once(self) -> bool:
        """
        Ejecuta un health check. Retorna True si el worker respondió OK.
        """
        self._last_check = time.time()
        try:
            resp = httpx.get(
                f"{self.worker_url}/health",
                timeout=10.0,
            )
            if resp.status_code == 200:
                data = resp.json()
                self._last_worker_version = data.get("version")
                self._on_success()
                return True
            else:
                logger.warning("Health check HTTP %d", resp.status_code)
                self._on_failure()
                return False
        except Exception as exc:
            logger.warning("Health check failed: %s", exc)
            self._on_failure()
            return False

    def _on_success(self):
        was_offline = not self._vm_online
        self._consecutive_failures = 0
        self._vm_online = True

        if was_offline:
            logger.info("✅ VM is back online!")
            self._set_level(SystemLevel.NORMAL)
            if self.on_vm_back:
                try:
                    self.on_vm_back()
                except Exception as exc:
                    logger.error("on_vm_back callback failed: %s", exc)

    def _on_failure(self):
        self._consecutive_failures += 1
        logger.warning(
            "Health check failure %d/%d",
            self._consecutive_failures,
            self.failure_threshold,
        )

        if self._consecutive_failures >= self.failure_threshold:
            if self._vm_online:
                logger.error(
                    "❌ VM declared OFFLINE after %d consecutive failures",
                    self._consecutive_failures,
                )
                self._vm_online = False
                self._set_level(SystemLevel.PARTIAL)

    def _set_level(self, new_level: SystemLevel):
        if new_level != self._level:
            old_level = self._level
            self._level = new_level
            logger.info("System level: %s → %s", old_level.value, new_level.value)
            if self.on_level_change:
                try:
                    self.on_level_change(old_level, new_level)
                except Exception as exc:
                    logger.error("on_level_change callback failed: %s", exc)

    # --- Background thread ---

    def start(self):
        """Inicia el monitor en un thread de background."""
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()
        logger.info(
            "Health monitor started (interval=%ds, threshold=%d)",
            self.check_interval,
            self.failure_threshold,
        )

    def stop(self):
        """Detiene el monitor."""
        self._running = False
        if self._thread:
            self._thread.join(timeout=self.check_interval + 5)
        logger.info("Health monitor stopped")

    def _loop(self):
        while self._running:
            self.check_once()
            time.sleep(self.check_interval)
