# 09 — Troubleshooting

## Casos Documentados

---

### 1. UI "unauthorized: gateway token missing"

**Síntoma**: Al acceder a la Control UI (`localhost:18789`), aparece error de autenticación.

**Causa**: OpenClaw requiere un gateway token configurado.

**Solución**:
1. Pegar el token en Control UI → Settings → Gateway Token.
2. O configurar en archivo/env:
   ```bash
   # En el env file del servicio
   OPENCLAW_GATEWAY_TOKEN=CHANGE_ME_GATEWAY_TOKEN
   ```
3. Reiniciar:
   ```bash
   systemctl --user restart openclaw
   ```

---

### 2. "No provider plugins found"

**Síntoma**: OpenClaw no muestra providers LLM disponibles.

**Causa**: Algunos providers vienen como plugins nativos y necesitan auth setup, no instalación npm.

**Nota (error documentado)**:
- Se intentó `openclaw plugins install @openclaw/openai` → **E404** (no disponible en npm).
- Los providers se habilitan con `auth setup-token` o OAuth nativo de OpenClaw.

**Solución**:
```bash
# Ver providers disponibles
openclaw models status

# Configurar auth para un provider
openclaw auth setup-token openai
# o
openclaw auth oauth openai
```

---

### 3. curl 401 — header mal formado

**Síntoma**: `POST /run` devuelve 401 aunque el token sea correcto.

**Causa**: El header `Authorization` está mal formado. Variantes incorrectas:
- `Authorization: Bearer ` (vacío después de Bearer)
- `Authorization:Bearer token` (falta espacio después de `:`)
- Token con espacios extra

**Solución**: Asegurarse del formato exacto:
```bash
-H 'Authorization: Bearer MI_TOKEN_AQUI'
```

---

### 4. bash "event not found" — tokens con `!`

**Síntoma**: Al ejecutar curl con un token que contiene `!`, bash muestra:
```
bash: !_especiales: event not found
```

**Causa**: Bash interpreta `!` como history expansion dentro de comillas dobles.

**Solución**:
1. **Usar comillas simples** (recomendado):
   ```bash
   curl -H 'Authorization: Bearer token_con_!_especiales'
   ```

2. **Desactivar history expansion** (alternativa):
   ```bash
   set +H
   curl -H "Authorization: Bearer token_con_!_especiales"
   set -H
   ```

3. **Escapar el `!`**:
   ```bash
   curl -H "Authorization: Bearer token_con_\!_especiales"
   ```

---

### 5. Uvicorn no puede bind puerto 8088

**Síntoma**:
```
ERROR: [Errno 10048] error while attempting to bind on address ('0.0.0.0', 8088)
```

**Causa**: Otro proceso ya está usando el puerto 8088.

**Solución (Windows)**:
```powershell
# Encontrar qué proceso usa el puerto
netstat -ano | findstr :8088

# Matar el proceso (reemplazar PID)
taskkill /PID <PID> /F

# O reiniciar el servicio NSSM
nssm restart openclaw-worker
```

---

### 6. Telegram 409 — getUpdates conflict

**Síntoma**:
```
409 Conflict: terminated by other getUpdates request
```

**Causa**: Dos instancias del bot intentan hacer polling simultáneamente.

**Solución**:
1. Verificar que NO hay instancias de OpenClaw corriendo en Windows con Telegram habilitado.
2. Solo una instancia debe tener Telegram activo (la del VPS).
3. Reiniciar la instancia del VPS:
   ```bash
   systemctl --user restart openclaw
   ```

---

### 7. Worker devuelve 500 "WORKER_TOKEN not configured"

**Síntoma**: `POST /run` devuelve 500.

**Causa**: La variable de entorno `WORKER_TOKEN` no está definida.

**Solución (dev)**:
```powershell
$env:WORKER_TOKEN="CHANGE_ME_WORKER_TOKEN"
python -m uvicorn app:app --host 0.0.0.0 --port 8088
```

**Solución (servicio NSSM)**: Reinstalar con el script que configura la variable, o:
```powershell
nssm set openclaw-worker AppEnvironmentExtra "WORKER_TOKEN=CHANGE_ME_WORKER_TOKEN"
nssm restart openclaw-worker
```

---

### 8. Tailscale — ping funciona pero curl no

**Posibles causas**:
1. Firewall de Windows bloquea el puerto → [crear regla](06-setup-worker-windows.md#firewall)
2. Uvicorn escucha en `127.0.0.1` en vez de `0.0.0.0` → usar `--host 0.0.0.0`
3. Worker no está corriendo → `nssm status openclaw-worker`
