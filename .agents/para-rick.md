# Mensajes para Rick (David / Cursor)

> Rick: cuando hagas `git pull` en la VPS, revisá este archivo por si hay instrucciones o avisos para vos.

---

## 2026-03-07 — Conectarte a la VM desde la VPS por SSH

Rick, conectate a la VM **desde la VPS** usando SSH. No necesitás contraseña; la clave `vps-umbral` ya está configurada en la VM.

### Cómo conectarte

**1. Abrí una terminal en la VPS** (SSH a rick@srv1431451 o `rick@100.113.249.25`).

**2. Ejecutá:**
```bash
ssh rick@100.109.16.40
```
Debería entrar directo (sin pedir contraseña). El prompt pasará a ser de la VM (ej. `rick@PCRick` o similar).

**3. Para salir de la VM:** escribí `exit`.

### Comandos útiles

| Acción | Comando |
|--------|---------|
| Entrar a una sesión en la VM | `ssh rick@100.109.16.40` |
| Ejecutar un solo comando sin entrar | `ssh rick@100.109.16.40 "hostname"` |
| Ejecutar PowerShell en la VM | `ssh rick@100.109.16.40 "powershell -Command \"Get-ComputerName\""` |

**IP de la VM:** `100.109.16.40` (PCRick por Tailscale). Si la VM está apagada o Tailscale desconectado, el SSH hará timeout.

Documentación: [62-operational-runbook.md](../docs/62-operational-runbook.md) sección 7.2.1.
