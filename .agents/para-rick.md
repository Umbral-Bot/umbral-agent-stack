# Mensajes para Rick (David / Cursor)

> Rick: cuando hagas `git pull` en la VPS, revisá este archivo por si hay instrucciones o avisos para vos.

---

## 2026-03-07 — Podés usar SSH a la VM

Rick, desde la **VPS** podés conectarte por SSH a la VM (Execution Plane) **sin contraseña**. La clave de la VPS (`vps-umbral`) ya está en la VM.

**Comando en la VPS:**
```bash
ssh rick@100.109.16.40 "hostname"
```
Debería responder `PCRick` sin pedir contraseña.

**Ejemplos de uso:**
- Ejecutar un comando en la VM: `ssh rick@100.109.16.40 "comando"`
- Entrar a una sesión en la VM: `ssh rick@100.109.16.40`
- Correr un script del repo en la VM: `ssh rick@100.109.16.40 "cd C:/GitHub/umbral-agent-stack && powershell -File scripts/algo.ps1"`

La IP `100.109.16.40` es la de la VM (PCRick) por Tailscale. Si la VM está apagada o Tailscale desconectado, el SSH hará timeout.

Documentación: [62-operational-runbook.md](../docs/62-operational-runbook.md) sección 7.2.1.
