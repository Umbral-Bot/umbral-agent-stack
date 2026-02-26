# 02 — Log de Implementación

> Cronología de la implementación real con timestamps aproximados, errores encontrados y resoluciones.

---

## 2026-02-26

### Fase 1.0 — VPS + OpenClaw + Telegram

- **SSH acceso al VPS**: Conexión inicial al VPS Hostinger (Ubuntu 24 LTS) por SSH.

- **Port-forwarding para Control UI**:
  ```bash
  ssh -N -L 18789:127.0.0.1:18789 -L 18791:127.0.0.1:18791 rick@VPS_PUBLIC_IP
  ```
  - UI accesible en `http://localhost:18789` desde el PC local.

- **Error: "gateway token missing"**:
  - 🔴 La UI de OpenClaw mostraba "unauthorized: gateway token missing".
  - ✅ **Solución**: Configurar `gateway.auth.token` en OpenClaw y reiniciar el servicio systemd.

- **Plugins — Telegram**:
  ```bash
  openclaw plugins enable telegram
  ```
  - Configuración de `allowlist` usando **ID numérico** del sender (no username).
  - `DM policy` configurado con `allowFrom` por sender ID.

- **LLM — Auth setup**:
  - `openclaw models status` para verificar providers disponibles.
  - OpenAI Codex: auth via OAuth nativo.
  - Anthropic: `setup-token` configurado pero dejado como fallback.
  - 🔴 **Error**: Intentó `openclaw plugins install @openclaw/openai` → E404 (no disponible en npm).
  - ✅ **Solución**: Los providers vienen como plugins nativos; se usan `auth setup-token` / OAuth directamente.

### Fase 1.5 — Tailscale + Worker

- **Tailscale — VPS**:
  ```bash
  curl -fsSL https://tailscale.com/install.sh | sh
  sudo tailscale up --ssh
  tailscale status
  tailscale ip -4
  ```
  - ✅ VPS obtiene IP Tailscale.

- **Tailscale — Windows**:
  - Instalación del cliente Tailscale, login en la misma account.
  - `tailscale ip -4` obtiene IP del Windows.
  - ✅ `ping` desde Windows al VPS Tailscale IP → OK.

- **Worker Windows — Setup**:
  ```powershell
  pip install fastapi uvicorn pydantic
  python -m uvicorn app:app --host 0.0.0.0 --port 8088 --log-level info
  ```
  - Firewall rule:
    ```powershell
    New-NetFirewallRule -DisplayName "OpenClaw Worker 8088" -Direction Inbound -LocalPort 8088 -Protocol TCP -Action Allow
    ```

- **Worker — Prueba desde VPS**:
  ```bash
  curl http://WINDOWS_TAILSCALE_IP:8088/health
  ```
  - ✅ Respuesta: `{"ok": true, "ts": ...}`

- **Error: WORKER_TOKEN not set**:
  - 🔴 `POST /run` devolvía 500 "WORKER_TOKEN not set".
  - ✅ **Solución**: Definir `$env:WORKER_TOKEN` en PowerShell antes de iniciar Uvicorn, o configurarlo en el servicio NSSM.

- **Error: 401 Unauthorized**:
  - 🔴 `POST /run` devolvía 401 incluso con token correcto.
  - ✅ **Solución**: Header debe ser exactamente `Authorization: Bearer <token>` (sin espacios extra ni formato incorrecto).

- **Error: bash "event not found"**:
  - 🔴 En bash, tokens con `!` causan "event not found" por history expansion.
  - ✅ **Solución**: Usar comillas simples en el header de curl:
    ```bash
    curl -H 'Authorization: Bearer token_con_!_especiales'
    ```
  - Alternativa: `set +H` para desactivar history expansion.

- **Scripts wrapper — worker-run/worker-call**:
  - Creación de scripts en `/openclaw/bin/` para invocar el worker de forma segura.
  - Problema inicial de "Extra data" al pasar JSON — resuelto leyendo de stdin si no hay argumento.

- **NSSM — Servicio Windows**:
  - Instalación como servicio `openclaw-worker` con NSSM.
  - Configuración de logs `stdout`/`stderr` en `C:\openclaw-worker\`.
  - Verificación: `nssm status openclaw-worker` + `netstat -ano | findstr :8088`.

- **systemd env — VPS**:
  - Variables `WORKER_URL` y `WORKER_TOKEN` agregadas en `~/.config/openclaw/env`.
  - `EnvironmentFile` referenciado en el unit systemd.
  - `daemon-reload` + `restart`.
  - Validación: `cat /proc/$PID/environ | tr '\0' '\n'` confirma variables cargadas.
