#!/usr/bin/env python3
"""One-off: fix authorized_keys on VM (VPS key + David key). Run from PC when VM is reachable.
   If Connect fails with timeout: VM may be off or Tailscale disconnected; try again when VM is on.
   Usage: $env:VM_PASS='password'; python scripts/fix-vm-authorized-keys.py
"""
import io
import os
import sys

host = "100.109.16.40"
user = "rick"
pw = os.environ.get("VM_PASS", "")
if not pw:
    print("Set VM_PASS env var with VM password, then run again.", file=sys.stderr)
    sys.exit(1)

vps_key = "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIO27PG0bWHu73Dfg+qHuzDIQujpB5VDnlAx5zJ7F+rnA vps-umbral"
david_key_path = os.path.expanduser(os.path.join("~", ".ssh", "id_rsa.pub"))
with open(david_key_path) as f:
    david_key = f.read().strip()

content = vps_key + "\n" + david_key + "\n"
remote_path = "C:/Users/rick/.ssh/authorized_keys"

import paramiko
client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
try:
    client.connect(host, username=user, password=pw, timeout=15)
except Exception as e:
    print(f"Connect failed: {e}", file=sys.stderr)
    sys.exit(2)

sftp = client.open_sftp()
try:
    sftp.putfo(io.BytesIO(content.encode("utf-8")), remote_path)
    print("authorized_keys written (LF, no BOM).")
except Exception as e:
    print(f"Write failed: {e}", file=sys.stderr)
    sftp.close()
    client.close()
    sys.exit(3)

# Try to fix permissions and restart sshd (may need Admin on VM)
stdin, stdout, stderr = client.exec_command(
    'powershell -Command "icacls C:\\Users\\rick\\.ssh\\authorized_keys /grant pcrick\\rick:(R); Restart-Service sshd"'
)
err = stderr.read().decode(errors="replace")
out = stdout.read().decode(errors="replace")
if err and "denegado" in err.lower():
    print("Note: icacls/restart may need Admin. Run on VM as Admin: icacls ... /grant pcrick\\rick:(R); Restart-Service sshd")
else:
    print(out or "icacls and sshd restart sent.")
sftp.close()
client.close()
print("Done. Test from PC: ssh -i $env:USERPROFILE\\.ssh\\id_rsa -o IdentitiesOnly=yes rick@100.109.16.40 hostname")
