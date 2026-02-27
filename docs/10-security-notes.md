# 10 — Notas de Seguridad

## Reglas Fundamentales

### 1. No exponer paneles a internet

- OpenClaw Control UI (`18789`) NUNCA debe ser accesible desde internet.
- Acceso exclusivamente por:
  - **SSH port-forwarding** (preferido)
  - **Tailscale** (aceptable, es red privada)

### 2. OpenClaw en loopback

OpenClaw debe escuchar solo en `127.0.0.1` (loopback) en el VPS. El acceso remoto se logra a través de SSH tunnel, no exponiendo el puerto.

### 3. Proteger archivos de configuración

```bash
# VPS: permisos restrictivos en env file
chmod 600 ~/.config/openclaw/env
```

### 4. Repositorio: plantillas, nunca secretos

- Todos los archivos de configuración en el repo usan **placeholders**: `CHANGE_ME_*`.
- NUNCA commitear:
  - Archivos `.env` con valores reales
  - `auth-profiles.json`
  - Carpetas `sessions/`
  - Tokens, API keys, o credenciales
- El `.gitignore` está configurado para prevenir commits accidentales.

### 5. Worker Token

- El `WORKER_TOKEN` se define como variable de entorno, nunca hardcodeado.
- El worker rechaza requests con 401 si el token no coincide.
- El worker devuelve 500 si el token no está configurado (fail-safe).

## Advertencia: bash history y tokens con `!`

> **⚠️ CUIDADO**: Si un token contiene el carácter `!`, bash lo interpreta como history expansion y puede:
> 1. Expandir a un comando previo del historial.
> 2. Enviar un token incorrecto al servidor.
> 3. Mostrar "event not found" y fallar.
>
> **Siempre usar comillas simples en curl**:
> ```bash
> curl -H 'Authorization: Bearer token_con_!_aqui'
> ```

## Antigravity — Riesgo Documentado

> **⚠️ Decisión del usuario**: Antigravity se mantiene activo en el sistema por decisión explícita del usuario.
>
> **Riesgos conocidos**:
> - Consumo de recursos adicional (CPU, memoria, red).
> - Superficie de ataque adicional si el componente tiene vulnerabilidades.
> - Requiere monitoreo y actualizaciones propios.
>
> **Mitigación**: El usuario acepta estos riesgos y monitorea el componente de forma independiente.

## Checklist de Seguridad

- [ ] `.env` no está en el repo (verificar `.gitignore`)
- [ ] `auth-profiles.json` no está en el repo
- [ ] `sessions/` no está en el repo
- [ ] Puertos 18789/18791 no están en firewall público
- [ ] `~/.config/openclaw/env` tiene permisos 600
- [ ] WORKER_TOKEN es una cadena aleatoria fuerte (mín. 32 caracteres)
- [ ] SSH keys usadas para acceso al VPS (no password)
- [ ] Tailscale ACLs revisadas (si aplica)

## Rotación de Secretos

Para rotar el WORKER_TOKEN:

1. Generar nuevo token:
   ```bash
   python3 -c "import secrets; print(secrets.token_urlsafe(32))"
   ```
2. Actualizar en VPS (`~/.config/openclaw/env`) y reiniciar OpenClaw.
3. Actualizar en Windows (variable de entorno NSSM) y reiniciar worker.
4. Verificar conectividad.
