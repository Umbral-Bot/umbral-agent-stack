"""
S7 — Gestión de secretos para Umbral Agent Stack.

SecretStore carga secretos con esta prioridad:
  1. Variables de entorno (siempre disponible, dev-friendly).
  2. Archivo cifrado .secrets.enc (Fernet, para producción sin vault externo).
  3. Archivo plano .secrets (solo para dev local, nunca en producción).

Uso:
  from infra.secrets import secrets
  token = secrets.get("WORKER_TOKEN")
  token = secrets.require("WORKER_TOKEN")  # raise si no existe
"""
from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger("infra.secrets")

_DEFAULT_SECRETS_DIR = Path.home() / ".config" / "umbral"
_SECRETS_FILE = "secrets.json"
_SECRETS_ENC_FILE = "secrets.enc"


class SecretStore:
    """
    Gestor de secretos con múltiples backends.

    Prioridad de lectura (mayor a menor):
      1. Variable de entorno
      2. Archivo cifrado (.secrets.enc + UMBRAL_SECRETS_KEY)
      3. Archivo plano (secrets.json, solo dev)
    """

    def __init__(self, secrets_dir: Optional[Path] = None):
        self._dir = secrets_dir or Path(os.environ.get("UMBRAL_SECRETS_DIR", str(_DEFAULT_SECRETS_DIR)))
        self._cache: Dict[str, str] = {}
        self._loaded = False

    def _load_file_secrets(self) -> None:
        """Carga secretos desde archivo (cifrado o plano)."""
        if self._loaded:
            return
        self._loaded = True

        enc_path = self._dir / _SECRETS_ENC_FILE
        plain_path = self._dir / _SECRETS_FILE

        if enc_path.exists():
            key = os.environ.get("UMBRAL_SECRETS_KEY")
            if not key:
                logger.warning("Found %s but UMBRAL_SECRETS_KEY not set; skipping encrypted secrets", enc_path)
            else:
                try:
                    from cryptography.fernet import Fernet
                    f = Fernet(key.encode())
                    data = enc_path.read_bytes()
                    decrypted = f.decrypt(data)
                    self._cache = json.loads(decrypted)
                    logger.info("Loaded %d secrets from %s", len(self._cache), enc_path)
                    return
                except ImportError:
                    logger.warning("cryptography package not installed; cannot decrypt %s", enc_path)
                except Exception as e:
                    logger.error("Failed to decrypt %s: %s", enc_path, e)

        if plain_path.exists():
            try:
                self._cache = json.loads(plain_path.read_text(encoding="utf-8"))
                logger.info("Loaded %d secrets from %s (plaintext, dev only)", len(self._cache), plain_path)
            except Exception as e:
                logger.error("Failed to load %s: %s", plain_path, e)

    def get(self, key: str, default: Optional[str] = None) -> Optional[str]:
        """Obtiene un secreto. Prioridad: env > encrypted file > plain file."""
        env_val = os.environ.get(key)
        if env_val is not None:
            return env_val

        self._load_file_secrets()
        return self._cache.get(key, default)

    def require(self, key: str) -> str:
        """Obtiene un secreto o lanza RuntimeError."""
        val = self.get(key)
        if val is None:
            raise RuntimeError(f"Secret '{key}' not found in env, encrypted file, or plain file")
        return val

    def list_keys(self) -> list[str]:
        """Lista las claves disponibles (sin valores, para auditoría)."""
        self._load_file_secrets()
        file_keys = set(self._cache.keys())
        env_keys = {k for k in os.environ if k.startswith(("WORKER_", "NOTION_", "REDIS_", "LANGFUSE_", "UMBRAL_"))}
        return sorted(file_keys | env_keys)

    @staticmethod
    def generate_key() -> str:
        """Genera una clave Fernet para cifrar secretos."""
        from cryptography.fernet import Fernet
        return Fernet.generate_key().decode()

    def encrypt_to_file(self, data: Dict[str, str], key: str) -> Path:
        """Cifra un dict de secretos y lo guarda en .secrets.enc."""
        from cryptography.fernet import Fernet
        f = Fernet(key.encode())
        raw = json.dumps(data, indent=2).encode()
        encrypted = f.encrypt(raw)

        self._dir.mkdir(parents=True, exist_ok=True)
        out = self._dir / _SECRETS_ENC_FILE
        out.write_bytes(encrypted)
        out.chmod(0o600)
        logger.info("Encrypted %d secrets to %s", len(data), out)
        return out

    def audit(self) -> Dict[str, Any]:
        """Auditoría: qué secretos están configurados y desde dónde."""
        self._load_file_secrets()
        result: Dict[str, Any] = {"keys": {}, "sources": []}

        enc_exists = (self._dir / _SECRETS_ENC_FILE).exists()
        plain_exists = (self._dir / _SECRETS_FILE).exists()

        if enc_exists:
            result["sources"].append("encrypted_file")
        if plain_exists:
            result["sources"].append("plain_file")
        result["sources"].append("environment")

        for key in self.list_keys():
            source = "env" if os.environ.get(key) else "file"
            result["keys"][key] = {"source": source, "set": self.get(key) is not None}

        return result


secrets = SecretStore()
