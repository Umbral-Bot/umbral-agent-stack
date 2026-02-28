#!/usr/bin/env python3
"""
S7 — CLI para gestionar secretos cifrados.

Uso:
  python scripts/manage_secrets.py genkey              # genera clave Fernet
  python scripts/manage_secrets.py encrypt             # cifra secrets.json -> secrets.enc
  python scripts/manage_secrets.py audit               # audita qué secretos existen
  python scripts/manage_secrets.py list                # lista claves disponibles
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


def cmd_genkey(_args):
    """Genera una clave Fernet para cifrar secretos."""
    try:
        from cryptography.fernet import Fernet
        key = Fernet.generate_key().decode()
        print(f"Nueva clave Fernet (guardar como UMBRAL_SECRETS_KEY):\n{key}")
    except ImportError:
        print("Error: instalar 'cryptography' — pip install cryptography")
        sys.exit(1)


def cmd_encrypt(args):
    """Cifra un archivo JSON de secretos."""
    from infra.secrets import SecretStore

    key = os.environ.get("UMBRAL_SECRETS_KEY")
    if not key:
        print("Error: UMBRAL_SECRETS_KEY no definida en el entorno")
        sys.exit(1)

    plain_path = Path(args.input)
    if not plain_path.exists():
        print(f"Error: {plain_path} no existe")
        sys.exit(1)

    data = json.loads(plain_path.read_text(encoding="utf-8"))
    store = SecretStore(secrets_dir=plain_path.parent if not args.output_dir else Path(args.output_dir))
    out = store.encrypt_to_file(data, key)
    print(f"Cifrado {len(data)} secretos -> {out}")
    print("Puedes eliminar el archivo plano con seguridad.")


def cmd_audit(_args):
    """Audita qué secretos están disponibles."""
    from infra.secrets import secrets
    result = secrets.audit()
    print(json.dumps(result, indent=2))


def cmd_list(_args):
    """Lista claves de secretos disponibles."""
    from infra.secrets import secrets
    keys = secrets.list_keys()
    if keys:
        for k in keys:
            print(f"  {k}")
    else:
        print("(ningún secreto encontrado)")


def main():
    p = argparse.ArgumentParser(description="Gestión de secretos Umbral")
    sub = p.add_subparsers(dest="command")

    sub.add_parser("genkey", help="Genera clave Fernet")

    enc = sub.add_parser("encrypt", help="Cifra secrets.json")
    enc.add_argument("--input", default=str(Path.home() / ".config" / "umbral" / "secrets.json"))
    enc.add_argument("--output-dir", default=None)

    sub.add_parser("audit", help="Audita secretos")
    sub.add_parser("list", help="Lista claves")

    args = p.parse_args()
    if not args.command:
        p.print_help()
        sys.exit(1)

    cmds = {"genkey": cmd_genkey, "encrypt": cmd_encrypt, "audit": cmd_audit, "list": cmd_list}
    cmds[args.command](args)


if __name__ == "__main__":
    main()
