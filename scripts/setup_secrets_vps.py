#!/usr/bin/env python3
"""
One-time script to set up encrypted secrets on the VPS.
Reads current env file, generates Fernet key, encrypts secrets.
Run on VPS: python scripts/setup_secrets_vps.py
"""
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

ENV_FILE = Path.home() / ".config" / "openclaw" / "env"
SECRETS_DIR = Path.home() / ".config" / "umbral"
SECRETS_JSON = SECRETS_DIR / "secrets.json"
SECRETS_ENC = SECRETS_DIR / "secrets.enc"
KEY_FILE = SECRETS_DIR / ".fernet_key"


def parse_env_file(path: Path) -> dict:
    secrets = {}
    if not path.exists():
        print(f"Env file not found: {path}")
        return secrets
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" in line:
            k, v = line.split("=", 1)
            k = k.strip()
            v = v.strip().strip('"').strip("'")
            if k and v:
                secrets[k] = v
    return secrets


def main():
    from cryptography.fernet import Fernet

    print("=== Setup Secrets Encryption ===")

    data = parse_env_file(ENV_FILE)
    if not data:
        print("No secrets found in env file. Exiting.")
        return

    print(f"Found {len(data)} secrets: {', '.join(data.keys())}")

    SECRETS_DIR.mkdir(parents=True, exist_ok=True)

    key = Fernet.generate_key().decode()

    f = Fernet(key.encode())
    raw = json.dumps(data, indent=2).encode()
    encrypted = f.encrypt(raw)

    SECRETS_ENC.write_bytes(encrypted)
    os.chmod(str(SECRETS_ENC), 0o600)

    KEY_FILE.write_text(key)
    os.chmod(str(KEY_FILE), 0o600)

    print(f"Encrypted secrets -> {SECRETS_ENC}")
    print(f"Fernet key saved  -> {KEY_FILE}")
    print(f"Key value: {key}")
    print()
    print("Add to your shell profile or systemd service:")
    print(f'  export UMBRAL_SECRETS_KEY="{key}"')
    print()

    f2 = Fernet(key.encode())
    decrypted = json.loads(f2.decrypt(SECRETS_ENC.read_bytes()))
    assert decrypted == data, "Verification failed!"
    print(f"Verification OK: {len(decrypted)} secrets decrypted correctly.")


if __name__ == "__main__":
    main()
