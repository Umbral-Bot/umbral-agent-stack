---
fuente: Copilot VPS (operador GO MIN read-only en srv1431451)
prompt_origen: Prompt 6 (docs/plans/sys-diag-capture-prompts-2026-07-17.md)
fecha_captura: 2026-07-17 (según David; confirmar al pegar)
superficie: procesos, unidades, crons, gateway, worker, logs, env por nombre, clones VPS
modo: read-only
estado_completitud: COMPLETE (ingerido verbatim por orquestador Cursor desde transcript de-9d13c3, linea 4342)
redacciones_por_ingesta: 0
---

## Salida final de la IA (verbatim)

Updated todo list

Voy a operar en modo estrictamente read-only sobre la VPS actual, primero cargando el protocolo del operador y verificando identidad/host, rama y superficies activas. Después recolectaré la evidencia en bloques acotados, sanitizaré secretos y cerraré con el YAML solicitado sin modificar runtime, Redis ni archivos.

Antes de tocar el runtime estoy leyendo las reglas operativas específicas de este repositorio y el historial de higiene de la VPS. Eso fija qué observaciones son seguras y cómo separar estado real, intención del repo y clones auxiliares.

Read [](file:///home/rick/umbral-agent-stack/.agents/instructions/coordinador-de-agentes.md#1-1), lines 1 to 320

Read [](file:///home/rick/umbral-agent-stack/.agents/PROTOCOL.md)

Read skill [windows-vps-execution-split](file:///home/rick/umbral-agent-stack/.agents/skills/windows-vps-execution-split/SKILL.md?vscodeLinkType%3Dskill)

Read skill [openclaw-foundry-activation](file:///home/rick/umbral-agent-stack/.agents/skills/openclaw-foundry-activation/SKILL.md?vscodeLinkType%3Dskill)

Read skill [openclaw-vps-operator](file:///home/rick/umbral-agent-stack/.claude/skills/openclaw-vps-operator/SKILL.md?vscodeLinkType%3Dskill)

Read memory [](file:///home/rick/.vscode-server/data/User/workspaceStorage/39b1fa01bfa14cf278419e89905f37c9/GitHub.copilot-chat/memory-tool/memories/repo/workspace-hygiene-vps.md)

Las reglas confirman que esta sesión está en la superficie correcta y que el mandato encaja en diagnóstico read-only. También hay un antecedente importante: el canónico debería ser `~/umbral-agent-stack`, pero en julio quedaron worktrees archivados y drift de skills pendiente; lo voy a comprobar de nuevo sin asumir que ese estado sigue vigente.

Ahora fijo el guard de sanitización y el runbook de estado, y en paralelo hago el preflight mínimo de host/usuario/hora. El resultado esperado es confirmar `srv1431451`/`rick` antes de ejecutar cualquier consulta de procesos o servicios.

Ran terminal command:  printf 'host='; hostname; printf 'user='; id -un; printf 'uid='; id -u; printf 'time_utc='; date -u '+%Y-%m-%dT%H:%M:%SZ'; printf 'cwd='; pwd

Searched for files matching `umbral-agent-stack` · `.agents/skills/**/SKILL.md`, 5 matches

Read [](file:///home/rick/umbral-agent-stack/runbooks/runbook-openclaw-status.md)

Read [](file:///home/rick/umbral-agent-stack/.agents/board.md#1-1), lines 1 to 220

Read skill [openclaw-vps-operator](file:///home/rick/umbral-agent-stack/.agents/skills/openclaw-vps-operator/SKILL.md?vscodeLinkType%3Dskill)

El preflight coincide: `srv1431451`, usuario `rick`, UID 1001. Voy a aplicar el guard del repo antes de observar salidas potencialmente sensibles; en particular, procesos se listarán sin argumentos y los entornos se leerán únicamente como nombres.

Read skill [secret-output-guard](file:///home/rick/umbral-agent-stack/.agents/skills/secret-output-guard/SKILL.md?vscodeLinkType%3Dskill)

Paso a la foto viva de bajo riesgo: procesos sin `args`, cgroups/CWD para atribución, inventario completo de unidades y timers, y capacidad del host. Con esto podré distinguir servicios productivos, procesos de VS Code y ruido no gestionado sin exponer líneas de comando.

Ran terminal command:  for pid in $(ps -eo pid=,comm= | awk 'tolower($2) ~ /(poller|worker|openclaw|node|python|n8n)/ {print $1}'); do process=$(ps -p "$pid" -o comm= | awk '{$1=$1;print}'); started=$(ps -p "$pid" -o lstart= | awk '{$1=$1;print}'); unit=$(awk -F/ 'NF {last=$NF} END {print last}' "/proc/$pid/cgroup" 2>/dev/null); cwd=$(readlink -f "/proc/$pid/cwd" 2>/dev/null || true); printf 'pid=%s | proceso=%s | desde=%s | cgroup=%s | cwd=%s\n' "$pid" "$process" "$started" "${unit:-unknown}" "${cwd:-unknown}"; done

Ran terminal command:  systemctl --user list-units --all --no-pager --plain

Ran terminal command:  systemctl --user list-timers --all --no-pager --plain

Ran terminal command:  df -h /; uptime; free -h

La primera foto de procesos incluyó falsos positivos del kernel porque `kworker` contiene “worker”; ya quedó claro el criterio correcto y la repetiré con coincidencia estricta. La capacidad está holgada (disco 38%, carga <0.4, 4.3 GiB disponibles) y solo apareció un timer de usuario, así que el scheduling principal probablemente está en cron y no en systemd timers.

Ran terminal command:  for pid in $(ps -eo pid=,comm= | awk '{name=tolower($2)} name ~ /^(python|python3|node|n8n|openclaw)/ || (name ~ /poller/ && name !~ /^kworker/) {print $1}'); do process=$(ps -p "$pid" -o comm= | awk '{$1=$1;print}'); started=$(ps -p "$pid" -o lstart= | awk '{$1=$1;print}'); unit=$(awk -F/ 'NF {last=$NF} END {print last}' "/proc/$pid/cgroup" 2>/dev/null); cwd=$(readlink -f "/proc/$pid/cwd" 2>/dev/null || true); printf '%s\t%s\t%s\t%s\t%s\n' "$pid" "$process" "$started" "${unit:-unknown}" "${cwd:-unknown}"; done

Ran terminal command:  systemctl --user show openclaw-gateway openclaw-dispatcher umbral-worker mission-control --property=Id,LoadState,ActiveState,SubState,MainPID,ExecMainStartTimestamp,WorkingDirectory,FragmentPath --no-pager 2>&1

Read [](file:///home/rick/.vscode-server/data/User/workspaceStorage/39b1fa01bfa14cf278419e89905f37c9/GitHub.copilot-chat/chat-session-resources/577529f5-4031-413b-9214-14df916f8591/call_2rnZHOvS7PIek3OoLOwhVtpo__vscode-1784304320297/content.txt)

La atribución ya identifica dispatcher, worker y Mission Control en el repo canónico; el gateway está activo desde el 13 de julio y trabaja desde `$HOME`, como corresponde al binario global. Falta capturar el PID real de gateway/n8n con una coincidencia más directa y contrastar salud/modelos/crons, que es el siguiente bloque.

Ran terminal command:  ps -eo pid=,comm=,lstart= | awk 'tolower($2) ~ /^(python|python3|node|node-remote|n8n|openclaw)/ || (tolower($2) ~ /poller/ && tolower($2) !~ /^kworker/) {print}'

Ran terminal command:  systemctl --user show n8n openclaw-gateway --property=Id,LoadState,ActiveState,SubState,MainPID,ExecMainStartTimestamp,WorkingDirectory,FragmentPath --no-pager 2>&1

Ran terminal command:  crontab -l 2>&1 | awk '{line=$0; if (line ~ /^[[:space:]]*[A-Za-z_][A-Za-z0-9_]*=/) sub(/=.*/, "=<REDACTED>", line); printf "%03d %s\n", NR, line}' | sed -E -e 's/(Bearer|Basic)[[:space:]]+[^[:space:]]+/\1 <REDACTED>/Ig' -e 's/(gh[pso]_|ghs_|github_pat_|sk-|sk_(test|live)_|ntn_|secret_|ya29\.|1//0|AIza)[A-Za-z0-9._/+==-]+/<REDACTED>/g' -e 's/((client_secret|refresh_token|AccountKey|[A-Za-z0-9_]*(KEY|TOKEN|SECRET|PASSWORD|CREDENTIAL)[A-Za-z0-9_]*)[=:])[A-Za-z0-9._/+==-]+/\1<REDACTED>/Ig' -e 's#(https?://)[^/@[:space:]]+:[^/@[:space:]]+@#\1<REDACTED>@#g' -e 's/([?&](token|key|api_key|access_token|code)=)[^&[:space:]]+/\1<REDACTED>/Ig'

Ran terminal command:  openclaw status --all 2>&1 | sed -E -e 's/(Bearer|Basic)[[:space:]]+[^[:space:]]+/\1 <REDACTED>/Ig' -e 's/(gh[pso]_|ghs_|github_pat_|sk-|sk_(test|live)_|ntn_|secret_|ya29\.|1//0|AIza)[A-Za-z0-9._/+==-]+/<REDACTED>/g' -e 's/((client_secret|refresh_token|AccountKey|[A-Za-z0-9_]*(KEY|TOKEN|SECRET|PASSWORD|CREDENTIAL)[A-Za-z0-9_]*)[=:])[A-Za-z0-9._/+==-]+/\1<REDACTED>/Ig' -e 's#(https?://)[^/@[:space:]]+:[^/@[:space:]]+@#\1<REDACTED>@#g'

Ran terminal command:  openclaw models status 2>&1 | sed -E -e 's/(Bearer|Basic)[[:space:]]+[^[:space:]]+/\1 <REDACTED>/Ig' -e 's/(gh[pso]_|ghs_|github_pat_|sk-|sk_(test|live)_|ntn_|secret_|ya29\.|1//0|AIza)[A-Za-z0-9._/+==-]+/<REDACTED>/g' -e 's/((client_secret|refresh_token|AccountKey|[A-Za-z0-9_]*(KEY|TOKEN|SECRET|PASSWORD|CREDENTIAL)[A-Za-z0-9_]*)[=:])[A-Za-z0-9._/+==-]+/\1<REDACTED>/Ig' -e 's#(https?://)[^/@[:space:]]+:[^/@[:space:]]+@#\1<REDACTED>@#g'

Detecté un problema del propio CLI: `openclaw models status` emitió un fingerprint parcialmente enmascarado de una credencial Google Vertex. No lo reproduciré ni usaré en la evidencia; queda etiquetado `SECURITY_RISK` y, siguiendo el guard del repo, la credencial debería rotarse fuera de este mandato read-only. Desde aquí usaré una lista permitida de campos y redacción también de valores parcialmente enmascarados.

El runtime muestra 16 entradas activas de cron y una pausada, todas apuntando al canónico; systemd no contiene un poller daemon separado, pero sí hay un proceso Python bajo `cron.service` desde las 09:35. Voy a correlacionar ahora cada entrada con su script/log, obtener el health del worker y construir la matriz de nombres de entorno sin leer ningún valor.

Ran terminal command:  openclaw status --all 2>&1 | sed -E -e 's/(Bearer|Basic)[[:space:]]+[^[:space:]]+/\1 <REDACTED>/Ig' -e 's/(gh[pso]_|ghs_|github_pat_|sk-|sk_(test|live)_|ntn_|secret_|ya29\.|1//0|AIza)[A-Za-z0-9._/+==-]+/<REDACTED>/g' -e 's/((client_secret|refresh_token|AccountKey|[A-Za-z0-9_]*(KEY|TOKEN|SECRET|PASSWORD|CREDENTIAL)[A-Za-z0-9_]*)[=:])[A-Za-z0-9._/+==-]+/\1<REDACTED>/Ig' -e 's#(https?://)[^/@[:space:]]+:[^/@[:space:]]+@#\1<REDACTED>@#g' -e 's/[A-Za-z0-9._/+==-]{3,}\.\.\.[A-Za-z0-9._/+==-]{3,}/<REDACTED_PARTIAL>/g' -e 's/[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}/<REDACTED_EMAIL>/g'

Ran terminal command:  curl -fsS http://127.0.0.1:8088/health | jq .

Ran terminal command:  crontab -l 2>/dev/null | while IFS= read -r line; do script=$(printf '%s\n' "$line" | grep -oE '(\$HOME|~|/home/rick)/[^[:space:]]+\.sh' | head -1 || true); [[ -z "$script" ]] && continue; expanded=${script/\$HOME/$HOME}; expanded=${expanded/#\~/$HOME}; log=$(printf '%s\n' "$line" | grep -oE '/tmp/[A-Za-z0-9._-]+\.log' | head -1 || true); if [[ -f "$expanded" ]]; then exists=yes; else exists=no; fi; if [[ "$line" =~ ^[[:space:]]*# ]]; then enabled=no; else enabled=yes; fi; if [[ -n "$log" && -e "$log" ]]; then log_state=$(stat -c 'mtime=%y size=%s' "$log"); elif [[ -n "$log" ]]; then log_state=missing; else log_state=none; fi; printf 'script=%s | enabled=%s | exists=%s | log=%s | %s\n' "$expanded" "$enabled" "$exists" "${log:-none}" "$log_state"; done

Ran terminal command:  printf '%s\n' 'OPENCLAW_ENV_RELEVANT_NAMES'; cut -d= -f1 /home/rick/.config/openclaw/env 2>/dev/null | sed -E 's/^[[:space:]]*export[[:space:]]+//' | grep -E '^(GOOGLE_API_KEY|ANTHROPIC_API_KEY|UMBRAL_DISABLE_CLAUDE|NOTION_POLLER_ENABLE_V2_CLASSIFY|AZURE_[A-Za-z0-9_]*|OPENAI_[A-Za-z0-9_]*)$' | sort -u; printf '%s\n' 'WORKER_ENV_RELEVANT_NAMES'; worker_pid=$(systemctl --user show umbral-worker -p MainPID --value); tr '\0' '\n' < "/proc/$worker_pid/environ" | cut -d= -f1 | grep -E '^(GOOGLE_API_KEY|ANTHROPIC_API_KEY|UMBRAL_DISABLE_CLAUDE|NOTION_POLLER_ENABLE_V2_CLASSIFY|AZURE_[A-Za-z0-9_]*|OPENAI_[A-Za-z0-9_]*)$' | sort -u

El worker responde `ok`, versión 0.4.0, con un catálogo amplio; calcularé el conteo exacto por familia en vez de inferirlo a mano. Los 16 scripts activos existen, pero el log del snapshot OpenClaw está vacío y no cambia desde el 23 de junio; eso requiere contrastar ejecución real antes de llamarlo roto. La matriz de entorno solo contiene `UMBRAL_DISABLE_CLAUDE` en ambas superficies; las credenciales de modelos viven en el auth store, no en esos envs.

Read [](file:///home/rick/.vscode-server/data/User/workspaceStorage/39b1fa01bfa14cf278419e89905f37c9/GitHub.copilot-chat/chat-session-resources/577529f5-4031-413b-9214-14df916f8591/call_BcN1LVbup9kmkVqNPer2n9ug__vscode-1784304320308/content.txt)

OpenClaw está alcanzable en loopback, gateway activo, Telegram OK y 8 agentes/30 sesiones; también hay dos señales de mantenimiento: versión 2026.6.10 con 2026.7.1 disponible y un path de plugin redundante. Ahora voy a medir ruido real de 48 horas por origen y a verificar cron desde el journal del sistema, manteniendo solo mensajes sanitizados y nombres de scripts.

Ran terminal command:  journalctl --user -u umbral-worker --since '48 hours ago' --no-pager -o short-iso 2>&1 | sed -E -e 's/(Bearer|Basic)[[:space:]]+[^[:space:]]+/\1 <REDACTED>/Ig' -e 's/(gh[pso]_|ghs_|github_pat_|sk-|sk_(test|live)_|ntn_|secret_|ya29\.|1//0|AIza)[A-Za-z0-9._/+==-]+/<REDACTED>/g' -e 's/((client_secret|refresh_token|AccountKey|[A-Za-z0-9_]*(KEY|TOKEN|SECRET|PASSWORD|CREDENTIAL)[A-Za-z0-9_]*)[=:])[A-Za-z0-9._/+==-]+/\1<REDACTED>/Ig' -e 's/[A-Za-z0-9._/+==-]{3,}\.\.\.[A-Za-z0-9._/+==-]{3,}/<REDACTED_PARTIAL>/g' -e 's/[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}/<REDACTED_EMAIL>/g' | grep -Ei 'error|exception|traceback|failed|failure|critical|timeout|timed out|(^|[^0-9])429([^0-9]|$)|(^|[^0-9])5[0-9][0-9]([^0-9]|$)' | tail -80

Ran terminal command:  journalctl --user -u openclaw-gateway --since '48 hours ago' --no-pager -o short-iso 2>&1 | sed -E -e 's/(Bearer|Basic)[[:space:]]+[^[:space:]]+/\1 <REDACTED>/Ig' -e 's/(gh[pso]_|ghs_|github_pat_|sk-|sk_(test|live)_|ntn_|secret_|ya29\.|1//0|AIza)[A-Za-z0-9._/+==-]+/<REDACTED>/g' -e 's/((client_secret|refresh_token|AccountKey|[A-Za-z0-9_]*(KEY|TOKEN|SECRET|PASSWORD|CREDENTIAL)[A-Za-z0-9_]*)[=:])[A-Za-z0-9._/+==-]+/\1<REDACTED>/Ig' -e 's/[A-Za-z0-9._/+==-]{3,}\.\.\.[A-Za-z0-9._/+==-]{3,}/<REDACTED_PARTIAL>/g' -e 's/[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}/<REDACTED_EMAIL>/g' | grep -Ei 'error|exception|traceback|failed|failure|critical|timeout|timed out|(^|[^0-9])429([^0-9]|$)|(^|[^0-9])5[0-9][0-9]([^0-9]|$)' | tail -80

Ran terminal command:  if [[ -r /tmp/notion_poller_cron.log ]]; then tail -200 /tmp/notion_poller_cron.log | sed -E -e 's/(Bearer|Basic)[[:space:]]+[^[:space:]]+/\1 <REDACTED>/Ig' -e 's/(gh[pso]_|ghs_|github_pat_|sk-|sk_(test|live)_|ntn_|secret_|ya29\.|1//0|AIza)[A-Za-z0-9._/+==-]+/<REDACTED>/g' -e 's/((client_secret|refresh_token|AccountKey|[A-Za-z0-9_]*(KEY|TOKEN|SECRET|PASSWORD|CREDENTIAL)[A-Za-z0-9_]*)[=:])[A-Za-z0-9._/+==-]+/\1<REDACTED>/Ig' -e 's/[A-Za-z0-9._/+==-]{3,}\.\.\.[A-Za-z0-9._/+==-]{3,}/<REDACTED_PARTIAL>/g'; else printf '%s\n' 'poller log unavailable'; fi

Ran terminal command:  journalctl -u cron --since '48 hours ago' --no-pager 2>/dev/null | grep -oE '(\$HOME|~|/home/rick)/umbral-agent-stack/scripts/vps/[A-Za-z0-9._-]+\.sh' | sed -E 's#^(\$HOME|~|/home/rick)/umbral-agent-stack/scripts/vps/##' | sort | uniq -c | sort -k2

Ran terminal command:  curl -fsS http://127.0.0.1:8088/health | jq '{ok, version, registered_count: (.tasks_registered | length), tasks_in_memory, families: ([.tasks_registered[] | split(".")[0]] | group_by(.) | map({familia: .[0], conteo: length}))}'

El volumen de logs confirma que no alcanza con “últimas 80 líneas”: necesito agrupar firmas para no confundir repetición con variedad ni arrastrar payloads. Haré una normalización agresiva de IDs, URLs, correos, números y cadenas largas, y mostraré solo las firmas agregadas con su frecuencia.

Ran terminal command:  journalctl --user -u umbral-worker --since '48 hours ago' --no-pager -o cat 2>&1 | grep -Ei 'error|exception|traceback|failed|failure|critical|timeout|timed out|rate.limit|unauthori|forbidden' | sed -E -e 's/(Bearer|Basic)[[:space:]]+[^[:space:]]+/\1 <REDACTED>/Ig' -e 's/[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}/<EMAIL>/g' -e 's#https?://[^[:space:]]+#<URL>#g' -e 's/[0-9a-fA-F]{8}-[0-9a-fA-F-]{27,}/<UUID>/g' -e 's/[A-Za-z0-9._/+==-]{3,}\.\.\.[A-Za-z0-9._/+==-]{3,}/<REDACTED_PARTIAL>/g' -e 's/(gh[pso]_|ghs_|github_pat_|sk-|sk_(test|live)_|ntn_|secret_|ya29\.|1//0|AIza)[A-Za-z0-9._/+==-]+/<REDACTED>/g' -e 's/([A-Za-z0-9_]*(KEY|TOKEN|SECRET|PASSWORD|CREDENTIAL)[A-Za-z0-9_]*[=:])[A-Za-z0-9._/+==-]+/\1<REDACTED>/Ig' -e 's/[A-Za-z0-9._/+==-]{24,}/<LONG>/g' -e 's/[0-9]+/<N>/g' -e 's/[[:space:]]+/ /g' | sort | uniq -c | sort -nr | head -20

Ran terminal command:  journalctl --user -u openclaw-gateway --since '48 hours ago' --no-pager -o cat 2>&1 | grep -Ei 'error|exception|traceback|failed|failure|critical|timeout|timed out|rate.limit|unauthori|forbidden' | sed -E -e 's/(Bearer|Basic)[[:space:]]+[^[:space:]]+/\1 <REDACTED>/Ig' -e 's/[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}/<EMAIL>/g' -e 's#https?://[^[:space:]]+#<URL>#g' -e 's/[0-9a-fA-F]{8}-[0-9a-fA-F-]{27,}/<UUID>/g' -e 's/[A-Za-z0-9._/+==-]{3,}\.\.\.[A-Za-z0-9._/+==-]{3,}/<REDACTED_PARTIAL>/g' -e 's/(gh[pso]_|ghs_|github_pat_|sk-|sk_(test|live)_|ntn_|secret_|ya29\.|1//0|AIza)[A-Za-z0-9._/+==-]+/<REDACTED>/g' -e 's/([A-Za-z0-9_]*(KEY|TOKEN|SECRET|PASSWORD|CREDENTIAL)[A-Za-z0-9_]*[=:])[A-Za-z0-9._/+==-]+/\1<REDACTED>/Ig' -e 's/[A-Za-z0-9._/+==-]{24,}/<LONG>/g' -e 's/[0-9]+/<N>/g' -e 's/[[:space:]]+/ /g' | sort | uniq -c | sort -nr | head -20

Ran terminal command:  tail -200 /tmp/notion_poller_cron.log 2>/dev/null | grep -Ei 'error|exception|traceback|failed|failure|critical|timeout|timed out|rate.limit|unauthori|forbidden' | sed -E -e 's#https?://[^[:space:]]+#<URL>#g' -e 's/[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}/<EMAIL>/g' -e 's/[A-Za-z0-9._/+==-]{24,}/<LONG>/g' -e 's/[0-9]+/<N>/g' | sort | uniq -c | sort -nr | head -20

Ran terminal command:  for unit in n8n openclaw-gateway openclaw-dispatcher umbral-worker mission-control; do systemctl --user show "$unit" -p Id -p ActiveState -p SubState -p MainPID -p ExecMainStartTimestamp --no-pager | paste -sd ' | ' -; done; systemctl --user list-timers --all --no-pager --plain | tail -n +1

Ran terminal command:  for unit in n8n openclaw-gateway openclaw-dispatcher umbral-worker mission-control; do pid=$(systemctl --user show "$unit" -p MainPID --value); printf 'unit=%s | ' "$unit"; ps -p "$pid" -o pid=,user=,comm=,lstart= | awk '{$1=$1;print}'; done; printf 'poller | '; ps -p 3016854 -o pid=,user=,comm=,lstart= | awk '{$1=$1;print}'

Los hallazgos ya son concretos: el worker genera fallas reales por credenciales de modelos ausentes (Google y Azure/OpenAI), mientras OpenClaw está operativo pero muy ruidoso: 4.850 cierres WebSocket antes de conectar y cientos de fallbacks porque `gpt-5.6-sol` exige un Codex más nuevo; además `gpt-5.3-codex` no es válido con la cuenta ChatGPT usada. Paso ahora a drift de Git, clones/worktrees, skills y Redis para separar deuda activa de residuos locales.

Ran terminal command:  cd /home/rick/umbral-agent-stack && printf '%s\n' 'BRANCH'; git branch --show-current; printf '%s\n' 'LOG_3'; git log --oneline -3; printf '%s\n' 'STATUS_SHORT'; git status --short; printf '%s\n' 'HEAD_LOCAL_REMOTE'; printf 'HEAD='; git rev-parse HEAD; printf 'origin_main_local='; git rev-parse origin/main; printf 'origin_main_network='; git ls-remote origin refs/heads/main | cut -f1

Ran terminal command:  printf '%s\n' 'REQUESTED_PATH_GLOB'; ls -d /home/rick/umbral-agent-stack* /tmp/*clean* /tmp/*-clean 2>/dev/null || true; printf '%s\n' 'REGISTERED_WORKTREES'; git -C /home/rick/umbral-agent-stack worktree list --porcelain

Ran terminal command:  diff -rq /home/rick/.openclaw/workspace/skills /home/rick/umbral-agent-stack/openclaw/workspace-templates/skills 2>&1 | head -40

Ran terminal command:  redis-cli --scan --pattern '*cursor*' 2>&1 | head -20

Ran terminal command:  openclaw models status 2>&1 | awk '/^Default[[:space:]]*:/ || /^Fallbacks \(/ || /^Aliases \(/ || /^Configured models \(/ {print} /^- anthropic effective=/ {print "provider_profile_present: anthropic"} /^- google effective=/ {print "provider_profile_present: google"} /^- google-vertex effective=/ {print "provider_profile_present: google-vertex"} /^- openai effective=/ {print "provider_profile_present: openai"} /^- openai via codex/ {print "runtime_provider: openai/codex"} /status=usable/ {print "runtime_status: usable"}'

Producción sí corre desde `main` limpio y exactamente alineado con `origin/main` remoto (`e908521`); esa parte no tiene drift. En cambio, el inventario revela 12 worktrees registrados, incluidos cuatro temporales bajo tmp del 13 de julio y seis archivados; voy a completar para cada uno suciedad, fecha, consumidores y recomendación, e incluir también clones archivados no registrados.

Ran terminal command:  git -C /home/rick/umbral-agent-stack worktree list --porcelain | awk '/^worktree / {sub(/^worktree /, ""); print}' | while IFS= read -r path; do branch=$(git -C "$path" symbolic-ref --quiet --short HEAD 2>/dev/null || printf 'DETACHED'); changes=$(git -C "$path" status --porcelain 2>/dev/null | wc -l); if [[ "$changes" -gt 0 ]]; then dirty=yes; else dirty=no; fi; commit=$(git -C "$path" log -1 --format='%h|%cI|%s' 2>/dev/null || printf 'UNKNOWN|UNKNOWN|UNKNOWN'); pids=''; for proc_cwd in /proc/[0-9]*/cwd; do cwd=$(readlink -f "$proc_cwd" 2>/dev/null || true); case "$cwd" in "$path"|"$path"/*) pids+="${proc_cwd#/proc/}"; pids="${pids%/cwd},";; esac; done; cron_refs=$(crontab -l 2>/dev/null | grep -F -c "$path" || true); printf 'path=%s\tbranch=%s\tdirty=%s\tchanges=%s\tcommit=%s\tprocess_pids=%s\tcron_refs=%s\n' "$path" "$branch" "$dirty" "$changes" "$commit" "${pids%,}" "$cron_refs"; done

Ran terminal command:  for path in /home/rick/archive/uas/*; do [[ -e "$path/.git" ]] || continue; registered=$(git -C /home/rick/umbral-agent-stack worktree list --porcelain | grep -Fxc "worktree $path" || true); [[ "$registered" -gt 0 ]] && continue; branch=$(git -C "$path" symbolic-ref --quiet --short HEAD 2>/dev/null || printf 'DETACHED'); changes=$(git -C "$path" status --porcelain 2>/dev/null | wc -l); commit=$(git -C "$path" log -1 --format='%h|%cI|%s' 2>/dev/null || printf 'UNKNOWN|UNKNOWN|UNKNOWN'); printf 'path=%s\tbranch=%s\tdirty=%s\tchanges=%s\tcommit=%s\n' "$path" "$branch" "$([[ "$changes" -gt 0 ]] && printf yes || printf no)" "$changes" "$commit"; done

Ran terminal command:  for unit in n8n openclaw-gateway openclaw-dispatcher umbral-worker mission-control; do printf '%s=' "$unit"; systemctl --user show "$unit" -p WorkingDirectory --value; done; printf 'cron_canonical_refs='; crontab -l 2>/dev/null | grep -F -c '/home/rick/umbral-agent-stack'

Ran terminal command:  printf 'registered_worktrees='; git -C /home/rick/umbral-agent-stack worktree list --porcelain | grep -c '^worktree '; printf 'archive_git_paths='; for path in /home/rick/archive/uas/*; do [[ -e "$path/.git" ]] && printf '%s\n' "$path"; done | wc -l; printf 'tmp_registered='; git -C /home/rick/umbral-agent-stack worktree list --porcelain | grep '^worktree /tmp/' | wc -l

El censo completo da 15 paths Git relevantes: 12 worktrees registrados y 3 clones archivados adicionales. El único checkout productivo está limpio; hay tres temporales dirty en tmp y un backup archivado con 29 cambios, por lo que esos cuatro son `DO_NOT_TOUCH`. Antes de cerrar sus etiquetas voy a comprobar el manifiesto de archivo, paths dirty y si los commits limpios ya están contenidos en `main`.

Ran terminal command:  for path in /tmp/openclaw-oauth-apply-wt /tmp/openclaw-oauth-only-urgent-wt /tmp/rick-hb-20260713-0143/wt-candidate /tmp/rick-hb-20260713-0143/wt-replay-on-origin /home/rick/archive/uas/umbral-agent-stack.backup-pre-cand001-20260629-174640; do printf 'path=%s\n' "$path"; git -C "$path" status --short 2>/dev/null; done

Ran terminal command:  git -C /home/rick/umbral-agent-stack worktree list --porcelain | awk '/^worktree / {sub(/^worktree /, ""); print}' | while IFS= read -r path; do head=$(git -C "$path" rev-parse HEAD 2>/dev/null || true); if git -C /home/rick/umbral-agent-stack merge-base --is-ancestor "$head" origin/main 2>/dev/null; then merged=yes; else merged=no; fi; printf 'path=%s\tcontained_in_origin_main=%s\n' "$path" "$merged"; done; for path in /home/rick/archive/uas/*; do [[ -e "$path/.git" ]] || continue; git -C /home/rick/umbral-agent-stack worktree list --porcelain | grep -Fqx "worktree $path" && continue; head=$(git -C "$path" rev-parse HEAD 2>/dev/null || true); if git -C /home/rick/umbral-agent-stack merge-base --is-ancestor "$head" origin/main 2>/dev/null; then merged=yes; else merged=no; fi; printf 'path=%s\tcontained_in_origin_main=%s\n' "$path" "$merged"; done

Ran terminal command:  for path in /home/rick/.openclaw/workspaces/rick-delivery/umbral-agent-stack-poller-hardening /tmp/openclaw-oauth-apply-wt /tmp/openclaw-oauth-only-urgent-wt /tmp/rick-hb-20260713-0143/wt-candidate /tmp/rick-hb-20260713-0143/wt-replay-on-origin; do printf 'path=%s | ' "$path"; stat -c 'mtime=%y' "$path" 2>/dev/null || printf 'missing\n'; done

Read [](file:///home/rick/archive/uas)

Read [](file:///home/rick/archive/uas/WHY.md)

El manifiesto confirma que los nueve paths de `~/archive/uas` están retenidos deliberadamente hasta un gate destructivo posterior a 30 días; hoy no corresponde borrarlos. En tmp, los dos worktrees OAuth modifican el mismo archivo de tarea y el replay contiene cambios de poller/tests; el candidato limpio no está contenido en `main`, así que tampoco es una eliminación automática. Cierro ahora las frecuencias exactas y las dos ambigüedades de cron silencioso.

Ran terminal command:  printf 'n8n_exe='; readlink -f /proc/969/exe; printf 'gateway_exe='; readlink -f /proc/2526932/exe; printf 'poller_exe='; readlink -f /proc/3016854/exe

Read [](file:///home/rick/umbral-agent-stack/scripts/vps/openclaw-runtime-snapshot-cron.sh)

Read [](file:///home/rick/umbral-agent-stack/scripts/vps/notion-poller-cron.sh)

Read [](file:///home/rick/umbral-agent-stack/scripts/vps/sim-daily-cron.sh)

Read [](file:///home/rick/umbral-agent-stack/scripts/vps/scheduled-tasks-cron.sh)

Ran terminal command:  printf 'poller_log='; stat -c 'mtime=%y size=%s' /tmp/notion_poller.log 2>/dev/null || printf 'missing\n'; tail -500 /tmp/notion_poller.log 2>/dev/null | grep -Ei 'error|exception|traceback|failed|failure|critical|timeout|timed out|rate.limit|unauthori|forbidden' | sed -E -e 's/(Bearer|Basic)[[:space:]]+[^[:space:]]+/\1 <REDACTED>/Ig' -e 's/[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}/<EMAIL>/g' -e 's#https?://[^[:space:]]+#<URL>#g' -e 's/[0-9a-fA-F]{8}-[0-9a-fA-F-]{27,}/<UUID>/g' -e 's/[A-Za-z0-9._/+==-]{3,}\.\.\.[A-Za-z0-9._/+==-]{3,}/<REDACTED_PARTIAL>/g' -e 's/(gh[pso]_|ghs_|github_pat_|sk-|sk_(test|live)_|ntn_|secret_|ya29\.|1//0|AIza)[A-Za-z0-9._/+==-]+/<REDACTED>/g' -e 's/([A-Za-z0-9_]*(KEY|TOKEN|SECRET|PASSWORD|CREDENTIAL)[A-Za-z0-9_]*[=:])[A-Za-z0-9._/+==-]+/\1<REDACTED>/Ig' -e 's/[A-Za-z0-9._/+==-]{24,}/<LONG>/g' -e 's/[0-9]+/<N>/g' | sort | uniq -c | sort -nr | head -20

Ran terminal command:  journalctl --user -u umbral-worker --since '48 hours ago' --no-pager -o cat 2>&1 | awk 'BEGIN{IGNORECASE=1} /GOOGLE_API_KEY not configured/{google++} /AZURE_OPENAI_ENDPOINT.*AZURE_OPENAI_API_KEY.*OPENAI_API_KEY/{openai++} /POST /run .* 500 Internal Server Error/{http500++} /Traceback \(most recent call last\)/{tracebacks++} /ConnectTimeout|ReadTimeout|PoolTimeout|ConnectError/{transport++} END{printf "google_key_missing_log_lines=%d\nopenai_or_azure_key_missing_log_lines=%d\nhttp_500_run_lines=%d\ntracebacks=%d\ntransport_error_lines=%d\n",google,openai,http500,tracebacks,transport}'

Ran terminal command:  journalctl --user -u openclaw-gateway --since '48 hours ago' --no-pager -o cat 2>&1 | awk 'BEGIN{IGNORECASE=1} /closed before connect/{ws++} /requires a newer version of Codex/{newer++} /not supported when using Codex with a ChatGPT account/{unsupported++} /rate.limit|rate limit|429/{rate++} /Embedded agent failed before reply/{embedded++} END{printf "ws_closed_before_connect_log_lines=%d\nmodel_requires_newer_codex_log_lines=%d\nmodel_unsupported_chatgpt_log_lines=%d\nrate_limit_log_lines=%d\nembedded_failures=%d\n",ws,newer,unsupported,rate,embedded}'

Ran terminal command:  printf 'snapshot_json='; stat -c 'mtime=%y size=%s' /home/rick/umbral-agent-stack/reports/runtime/generated/openclaw-runtime-snapshot-latest.json 2>/dev/null || printf 'missing\n'; printf 'snapshot_md='; stat -c 'mtime=%y size=%s' /home/rick/umbral-agent-stack/reports/runtime/generated/openclaw-runtime-snapshot-latest.md 2>/dev/null || printf 'missing\n'; printf 'sim_daily='; stat -c 'mtime=%y size=%s' /tmp/sim_daily.log 2>/dev/null || printf 'missing\n'; printf 'scheduled_tasks='; stat -c 'mtime=%y size=%s' /tmp/scheduled_tasks.log 2>/dev/null || printf 'missing\n'

Ran terminal command:  ps -eo pid=,user=,lstart=,comm=,args= | awk 'BEGIN{IGNORECASE=1} $0 ~ /(poller|worker|openclaw|node|python|n8n)/ && $5 !~ /^(awk|ps|bash|sh)$/ {pid=$1; user=$2; start=$3" "$4" "$5" "$6" "$7; comm=$8; print pid "\t" user "\t" start "\t" comm}' | sort -n

El snapshot silencioso sí corrió a las 06:20 y produjo JSON/Markdown, y SIM Daily escribió a las 08:00; no son fallas. El poller está activo y sin errores en sus últimas 500 líneas, pero su log ya mide ~102 MB, una oportunidad clara de rotación. Voy a cerrar con una foto de procesos depurada, asignación agente→modelo y conteo total del drift de skills.

Ran terminal command:  ps -eo pid=,user=,lstart=,comm=,args= | awk 'BEGIN{IGNORECASE=1} $0 ~ /(poller|worker|openclaw|node|python|n8n)/ && $8 !~ /^(kworker|awk|ps|bash|sh|cpuUsage.sh)$/ {print $1}' | while IFS= read -r pid; do user=$(ps -p "$pid" -o user= | awk '{$1=$1;print}'); started=$(ps -p "$pid" -o lstart= | awk '{$1=$1;print}'); comm=$(ps -p "$pid" -o comm= | awk '{$1=$1;print}'); exe=$(readlink -f "/proc/$pid/exe" 2>/dev/null || true); unit=$(awk -F/ 'NF {last=$NF} END {print last}' "/proc/$pid/cgroup" 2>/dev/null); cwd=$(readlink -f "/proc/$pid/cwd" 2>/dev/null || true); printf 'pid=%s | user=%s | proceso=%s | exe=%s | desde=%s | cgroup=%s | cwd=%s\n' "$pid" "$user" "$comm" "${exe:-unknown}" "$started" "${unit:-unknown}" "${cwd:-unknown}"; done

Ran terminal command:  jq '{default_model: .agents.defaults.model, agents: [.agents.list[] | {id: .id, model: .model}]}' /home/rick/.openclaw/openclaw.json

Ran terminal command:  cutoff=$(date -d '48 hours ago' '+%Y-%m-%d %H:%M:%S'); awk -v cutoff="$cutoff" 'BEGIN{IGNORECASE=1; in_window=0} match($0,/^20[0-9][0-9]-[0-9][0-9]-[0-9][0-9][ T][0-9][0-9]:[0-9][0-9]:[0-9][0-9]/){ts=substr($0,1,19); gsub(/T/," ",ts); in_window=(ts>=cutoff); if(in_window) last=ts} in_window{lines++; if($0 ~ /error|exception|traceback|failed|failure|critical|timeout|timed out|rate.limit|unauthori|forbidden/) errors++} END{printf "window_start=%s\nlast_timestamp=%s\nlines_in_window=%d\nerror_keyword_lines=%d\n",cutoff,last,lines,errors}' /tmp/notion_poller.log

Ran terminal command:  diff -rq /home/rick/.openclaw/workspace/skills /home/rick/umbral-agent-stack/openclaw/workspace-templates/skills 2>/dev/null | awk 'BEGIN{only_live=0; only_repo=0; differ=0} /^Only in /home/rick/\.openclaw/{only_live++} /^Only in /home/rick/umbral-agent-stack/{only_repo++} /^Files /{differ++} END{printf "only_live=%d\nonly_repo=%d\nfiles_differ=%d\ntotal_differences=%d\n",only_live,only_repo,differ,only_live+only_repo+differ}'

Ran terminal command:  printf 'redis_ping='; redis-cli ping 2>&1; printf 'cursor_key_count='; redis-cli --scan --pattern '*cursor*' 2>/dev/null | wc -l

El poller no está “sin errores”: en 48 horas produjo 61.272 líneas y 3.612 contienen términos de error, aunque sus últimas 500 ya estaban limpias. Voy a agrupar esas firmas con redacción de payloads para distinguir error funcional de mensajes históricos/reintentos, y revisar la lista depurada de procesos antes de etiquetarla.

Ran terminal command:  cutoff=$(date -d '48 hours ago' '+%Y-%m-%d %H:%M:%S'); awk -v cutoff="$cutoff" 'BEGIN{IGNORECASE=1; in_window=0} match($0,/^20[0-9][0-9]-[0-9][0-9]-[0-9][0-9][ T][0-9][0-9]:[0-9][0-9]:[0-9][0-9]/){ts=substr($0,1,19); gsub(/T/," ",ts); in_window=(ts>=cutoff)} in_window && $0 ~ /error|exception|traceback|failed|failure|critical|timeout|timed out|rate.limit|unauthori|forbidden/{print}' /tmp/notion_poller.log | sed -E -e 's/(Bearer|Basic)[[:space:]]+[^[:space:]]+/\1 <REDACTED>/Ig' -e 's/[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}/<EMAIL>/g' -e 's#https?://[^[:space:]]+#<URL>#g' -e 's/(comment|text|body|content|title|response|payload)=.*/\1=<REDACTED>/Ig' -e 's/"[^"]{8,}"/"<REDACTED>"/g' -e "s/'[^']{8,}'/'<REDACTED>'/g" -e 's/[0-9a-fA-F]{8}-[0-9a-fA-F-]{27,}/<UUID>/g' -e 's/[A-Za-z0-9._/+==-]{3,}\.\.\.[A-Za-z0-9._/+==-]{3,}/<REDACTED_PARTIAL>/g' -e 's/(gh[pso]_|ghs_|github_pat_|sk-|sk_(test|live)_|ntn_|secret_|ya29\.|1//0|AIza)[A-Za-z0-9._/+==-]+/<REDACTED>/g' -e 's/([A-Za-z0-9_]*(KEY|TOKEN|SECRET|PASSWORD|CREDENTIAL)[A-Za-z0-9_]*[=:])[A-Za-z0-9._/+==-]+/\1<REDACTED>/Ig' -e 's/[A-Za-z0-9._/+==-]{20,}/<LONG>/g' -e 's/[0-9]+/<N>/g' -e 's/[[:space:]]+/ /g' | sort | uniq -c | sort -nr | head -20

Ran terminal command:  cutoff=$(date -d '48 hours ago' '+%Y-%m-%d %H:%M:%S'); awk -v cutoff="$cutoff" 'BEGIN{IGNORECASE=1; in_window=0} match($0,/^20[0-9][0-9]-[0-9][0-9]-[0-9][0-9][ T][0-9][0-9]:[0-9][0-9]:[0-9][0-9]/){ts=substr($0,1,19); gsub(/T/," ",ts); in_window=(ts>=cutoff)} in_window{ if($0 ~ /GOOGLE_API_KEY not configured/) google++; if($0 ~ /scan|classif/) classify++; if($0 ~ /timeout|timed out/) timeout++; if($0 ~ /rate.limit|429/) rate++; if($0 ~ /unauthori|forbidden|401|403/) auth++; if($0 ~ /Traceback/) trace++; if($0 ~ /failed|failure/) failed++ } END{printf "google_key_missing_lines=%d\nclassification_related_lines=%d\ntimeout_lines=%d\nrate_limit_lines=%d\nauth_error_lines=%d\ntraceback_lines=%d\nfailed_keyword_lines=%d\n",google,classify,timeout,rate,auth,trace,failed}' /tmp/notion_poller.log

Read [](file:///home/rick/.vscode-server/data/User/workspaceStorage/39b1fa01bfa14cf278419e89905f37c9/GitHub.copilot-chat/chat-session-resources/577529f5-4031-413b-9214-14df916f8591/call_nccKRuqB97LwbZ9C0fFeLNl7__vscode-1784304320347/content.txt)

Las firmas del poller separan ruido de fallo: 3.520 líneas son resúmenes informativos que contienen la palabra “errors”; las fallas reales observables son 18 respuestas server-side con traceback, 10 iteraciones abortadas y 8 resoluciones de targets fallidas. Haré una última consolidación de procesos por ejecutable/cgroup y de fechas de los commits; luego ya puedo devolver el YAML completo sin más exploración.

Ran terminal command:  for procdir in /proc/[0-9]*; do pid=${procdir#/proc/}; exe=$(readlink -f "$procdir/exe" 2>/dev/null || true); base=${exe##*/}; comm=$(cat "$procdir/comm" 2>/dev/null || true); cgroup=$(awk -F/ 'NF {last=$NF} END {print last}' "$procdir/cgroup" 2>/dev/null); if [[ "$base" =~ ^(node|python|python3|python3\.12)$ || "$comm" =~ (poller|worker|openclaw|n8n) || "$cgroup" =~ ^(n8n|openclaw-gateway|openclaw-dispatcher|umbral-worker|mission-control)\.service$ ]]; then user=$(ps -p "$pid" -o user= | awk '{$1=$1;print}'); started=$(ps -p "$pid" -o lstart= | awk '{$1=$1;print}'); ppid=$(ps -p "$pid" -o ppid= | awk '{$1=$1;print}'); printf 'pid=%s | ppid=%s | user=%s | ejecutable=%s | proceso=%s | desde=%s | cgroup=%s\n' "$pid" "$ppid" "$user" "${base:-unknown}" "$comm" "$started" "${cgroup:-unknown}"; fi; done | sort -t= -k2,2n

Ran terminal command:  cd /home/rick/umbral-agent-stack && git log -3 --format='%h | %cI | %s'

Ran terminal command:  systemctl --user show umbral-worker -p EnvironmentFiles --value; systemctl --user show openclaw-gateway -p EnvironmentFiles --value

Ran terminal command:  cutoff=$(date -d '48 hours ago' '+%Y-%m-%d %H:%M:%S'); awk -v cutoff="$cutoff" 'match($0,/^20[0-9][0-9]-[0-9][0-9]-[0-9][0-9][ T][0-9][0-9]:[0-9][0-9]:[0-9][0-9]/){ts=substr($0,1,19); gsub(/T/," ",ts); in_window=(ts>=cutoff)} in_window{while(match($0,/HTTP/[0-9.]+" [0-9][0-9][0-9]/)){code=substr($0,RSTART+RLENGTH-3,3); counts[code]++; $0=substr($0,RSTART+RLENGTH)}} END{for(code in counts) printf "http_status_%s_lines=%d\n",code,counts[code]}' /tmp/notion_poller.log | sort

La comparación temporal añade un drift operativo importante: `main` recibió el fix del poller a las 09:34, el daemon se inició a las 09:35 y por tanto sí lo tomó; worker también arrancó después del commit Granola de las 02:01. Dispatcher y Mission Control, en cambio, siguen con procesos del 3 de julio aunque el repo ya avanzó, así que “main limpio” no implica que esos dos servicios hayan cargado el HEAD actual.

Read [](file:///home/rick/.vscode-server/data/User/workspaceStorage/39b1fa01bfa14cf278419e89905f37c9/GitHub.copilot-chat/chat-session-resources/577529f5-4031-413b-9214-14df916f8591/call_aj4Y55oioBak2xgIPmAOskXR__vscode-1784304320355/content.txt)

Me falta un requisito literal antes del cierre: inventariar todos los nombres de variables presentes, no solo la matriz crítica. Haré esa lectura nombre-only aprobada para el archivo OpenClaw y proc del worker; no se imprimirá ningún valor, longitud ni fingerprint.

Ran terminal command:  sed -E 's/^[[:space:]]*export[[:space:]]+//' /home/rick/.config/openclaw/env 2>/dev/null | awk -F= '/^[A-Za-z_][A-Za-z0-9_]*=/{print $1}' | sort -u

Ran terminal command:  worker_pid=$(systemctl --user show umbral-worker -p MainPID --value); tr '\0' '\n' < "/proc/$worker_pid/environ" | cut -d= -f1 | awk '/^[A-Za-z_][A-Za-z0-9_]*$/' | sort -u

Ran terminal command:  printf 'openclaw_env_name_count='; sed -E 's/^[[:space:]]*export[[:space:]]+//' /home/rick/.config/openclaw/env 2>/dev/null | awk -F= '/^[A-Za-z_][A-Za-z0-9_]*=/{print $1}' | sort -u | wc -l; worker_pid=$(systemctl --user show umbral-worker -p MainPID --value); printf 'worker_env_name_count='; tr '\0' '\n' < "/proc/$worker_pid/environ" | cut -d= -f1 | awk '/^[A-Za-z_][A-Za-z0-9_]*$/' | sort -u | wc -l

La auditoría read-only quedó completa: no se reinició, editó, desplegó ni escribió en Redis. El host y el repo canónico están sanos, pero el runtime queda `ACTIVE_DEGRADED` por modelos incompatibles, credenciales ausentes en el worker, procesos antiguos, logs ruidosos, drift de skills y checkouts temporales que requieren preservación; además se detectó y omitió un fingerprint parcial que exige rotación según la política local.

```yaml
auditoria_vps:
  meta:
    host: srv1431451
    usuario: rick
    inicio_utc: "2026-07-17T16:06:55Z"
    observado_hasta_local: "2026-07-17T12:20:00-04:00"
    modo: read-only
    cambios_realizados: ninguno
    secretos_impresos_en_este_informe: no
    veredicto: ACTIVE_DEGRADED
    resumen: "Host con recursos sanos y main limpio; runtime funcional pero degradado por modelos incompatibles, credenciales ausentes, procesos antiguos, logs ruidosos y drift de skills."

  procesos:
    evidencia:
      comando: "ps filtrado por poller|worker|openclaw|node|python|n8n; args omitidos; atribucion mediante /proc/<pid>/{exe,cgroup,cwd}"
      salida_sanitizada: "Se excluyeron kworker del kernel. Los PID listados no incluyen argumentos ni variables de entorno."
    items:
      - {proceso: "n8n (Node principal + hijo)", pid: [969, 1555], desde: "2026-06-23T00:03:52-04:00", etiqueta: ACTIVE_HEALTHY}
      - {proceso: "openclaw-dispatcher", pid: 1769618, desde: "2026-07-03T14:15:56-04:00", etiqueta: DRIFT_REPO_VPS, detalle: "Python 3.12 figura deleted; proceso anterior al HEAD actual."}
      - {proceso: "mission-control", pid: 1769623, desde: "2026-07-03T14:15:56-04:00", etiqueta: DRIFT_REPO_VPS, detalle: "Python 3.12 figura deleted; proceso anterior al HEAD actual."}
      - {proceso: "openclaw-gateway Node", pid: 2526932, desde: "2026-07-13T13:39:23-04:00", etiqueta: ACTIVE_NOISY}
      - {proceso: "OpenClaw Codex app-server children", pid: [2530054, 2530061, 2532591, 2532598, 2534698, 2534705, 2535144, 2535151, 3006222, 3006229, 3030977, 3030984], desde: "2026-07-13 a 2026-07-17", etiqueta: ACTIVE_NOISY}
      - {proceso: "umbral-worker", pid: 2972295, desde: "2026-07-17T02:02:07-04:00", etiqueta: ACTIVE_DEGRADED}
      - {proceso: "notion-poller daemon", pid: 3016854, desde: "2026-07-17T09:35:02-04:00", etiqueta: ACTIVE_DEGRADED}
      - {proceso: "VS Code Server Node", pid: [3035321, 3035348, 3035360, 3035371, 3035412, 3035748], desde: "2026-07-17T12:05:05-04:00", etiqueta: ACTIVE_HEALTHY}
      - {proceso: "Node en contenedor root no atribuible", pid: [1470, 1494], desde: "2026-06-23T00:03:54-04:00", etiqueta: UNKNOWN}

  unidades:
    evidencia:
      comando: "systemctl --user list-units --all --no-pager --plain; systemctl --user list-timers --all --no-pager --plain"
      salida_sanitizada: "180 unidades cargadas; 5 servicios de aplicacion activos; 1 timer de usuario."
    items:
      - {unidad: n8n.service, estado: "loaded/active/running; PID 969", etiqueta: ACTIVE_HEALTHY}
      - {unidad: openclaw-gateway.service, estado: "loaded/active/running; PID 2526932", etiqueta: ACTIVE_NOISY}
      - {unidad: openclaw-dispatcher.service, estado: "loaded/active/running; PID 1769618", etiqueta: DRIFT_REPO_VPS}
      - {unidad: umbral-worker.service, estado: "loaded/active/running; PID 2972295", etiqueta: ACTIVE_DEGRADED}
      - {unidad: mission-control.service, estado: "loaded/active/running; PID 1769623", etiqueta: DRIFT_REPO_VPS}
      - {unidad: redis.service, estado: "user unit not-found/inactive/dead; redis-cli responde PONG por otra superficie", etiqueta: UNKNOWN}
      - {unidad: launchpadlib-cache-clean.timer, estado: "active/waiting; ultima 2026-07-17T00:29:35-04:00", etiqueta: ACTIVE_HEALTHY}

  crons:
    evidencia:
      comando: "crontab -l; test -f sobre cada script; stat solamente sobre logs/artefactos"
      salida_sanitizada: "17 entradas: 16 activas y 1 comentada; todos los scripts existen."
    items:
      - {linea: "*/30 * * * * bash /home/rick/umbral-agent-stack/scripts/vps/health-check.sh >> /tmp/health_check.log 2>&1", script_existe: si, ultima_corrida_si_hay_log: "2026-07-17T12:00:02-04:00", etiqueta: ACTIVE_HEALTHY}
      - {linea: "*/5 * * * * bash /home/rick/umbral-agent-stack/scripts/vps/supervisor.sh >> /tmp/supervisor.log 2>&1", script_existe: si, ultima_corrida_si_hay_log: "2026-07-17T12:10:01-04:00", etiqueta: ACTIVE_HEALTHY}
      - {linea: "0 8,14,20 * * * bash ~/umbral-agent-stack/scripts/vps/sim-daily-cron.sh", script_existe: si, ultima_corrida_si_hay_log: "log interno /tmp/sim_daily.log: 2026-07-17T08:00:05-04:00", etiqueta: ACTIVE_HEALTHY}
      - {linea: "*/5 * * * * bash /home/rick/umbral-agent-stack/scripts/vps/notion-poller-cron.sh >> /tmp/notion_poller_cron.log 2>&1", script_existe: si, ultima_corrida_si_hay_log: "ultima salida 2026-07-17T09:35:03-04:00; luego wrapper silencioso con daemon vivo", etiqueta: ACTIVE_HEALTHY}
      - {linea: "30 8,14,20 * * * bash /home/rick/umbral-agent-stack/scripts/vps/sim-report-cron.sh >> /tmp/sim_report.log 2>&1", script_existe: si, ultima_corrida_si_hay_log: "2026-07-17T08:30:07-04:00", etiqueta: ACTIVE_HEALTHY}
      - {linea: "0 22 * * * bash /home/rick/umbral-agent-stack/scripts/vps/daily-digest-cron.sh >> /tmp/daily_digest.log 2>&1", script_existe: si, ultima_corrida_si_hay_log: "2026-07-16T22:00:12-04:00", etiqueta: ACTIVE_HEALTHY}
      - {linea: "0 9,15,21 * * * bash /home/rick/umbral-agent-stack/scripts/vps/sim-to-make-cron.sh >> /tmp/sim_to_make.log 2>&1", script_existe: si, ultima_corrida_si_hay_log: "2026-07-17T09:00:04-04:00", etiqueta: ACTIVE_HEALTHY}
      - {linea: "0 6 * * * bash /home/rick/umbral-agent-stack/scripts/vps/e2e-validation-cron.sh >> /tmp/e2e_validation.log 2>&1", script_existe: si, ultima_corrida_si_hay_log: "2026-07-17T06:00:14-04:00", etiqueta: ACTIVE_HEALTHY}
      - {linea: "0 7 * * 1 bash /home/rick/umbral-agent-stack/scripts/vps/ooda-report-cron.sh >> /tmp/ooda_report.log 2>&1", script_existe: si, ultima_corrida_si_hay_log: "2026-07-13T07:00:02-04:00", etiqueta: ACTIVE_HEALTHY}
      - {linea: "* * * * * bash /home/rick/umbral-agent-stack/scripts/vps/scheduled-tasks-cron.sh >> /tmp/scheduled_tasks.log 2>&1", script_existe: si, ultima_corrida_si_hay_log: "ultima escritura 2026-07-17T02:02:03-04:00; las corridas no-op son silenciosas", etiqueta: UNKNOWN}
      - {linea: "*/15 * * * * bash /home/rick/umbral-agent-stack/scripts/vps/quota-guard-cron.sh >> /tmp/quota_guard.log 2>&1", script_existe: si, ultima_corrida_si_hay_log: "2026-07-17T12:00:04-04:00", etiqueta: ACTIVE_HEALTHY}
      - {linea: "20 5 * * * bash /home/rick/umbral-agent-stack/scripts/vps/notion-curate-cron.sh >> /tmp/notion_curate.log 2>&1", script_existe: si, ultima_corrida_si_hay_log: "2026-07-17T05:20:23-04:00", etiqueta: ACTIVE_HEALTHY}
      - {linea: "20 */6 * * * bash /home/rick/umbral-agent-stack/scripts/vps/openclaw-runtime-snapshot-cron.sh >> /tmp/openclaw_runtime_snapshot.log 2>&1", script_existe: si, ultima_corrida_si_hay_log: "log directo vacio; artefactos JSON/MD actualizados 2026-07-17T06:20:02-04:00", etiqueta: ACTIVE_HEALTHY}
      - {linea: "0 * * * * /home/rick/umbral-agent-stack/scripts/vps/dashboard-rick-cron.sh >> /tmp/dashboard_rick_cron.log 2>&1", script_existe: si, ultima_corrida_si_hay_log: "2026-07-17T12:00:02-04:00", etiqueta: ACTIVE_HEALTHY}
      - {linea: "0 */6 * * * /home/rick/umbral-agent-stack/scripts/vps/openclaw-panel-cron.sh >> /tmp/openclaw_panel_cron.log 2>&1", script_existe: si, ultima_corrida_si_hay_log: "2026-07-17T12:00:02-04:00", etiqueta: ACTIVE_HEALTHY}
      - {linea: "# B1-paused 2026-05-24 15 */6 * * * bash /home/rick/umbral-agent-stack/scripts/vps/discovery-publish-cron.sh >> /tmp/discovery_publish.log 2>&1", script_existe: si, ultima_corrida_si_hay_log: "sin log", etiqueta: OBSOLETE}
      - {linea: "0 8 * * * bash $HOME/umbral-agent-stack/scripts/vps/granola-gap-check.sh >> /tmp/granola_gap_check.log 2>&1", script_existe: si, ultima_corrida_si_hay_log: "2026-07-17T08:00:05-04:00", etiqueta: ACTIVE_HEALTHY}

  disco_carga:
    evidencia:
      comando: "df -h /; uptime; free -h"
      salida_sanitizada: "root 96G/37G/60G; load 0.27/0.35/0.28; memoria disponible 4.3GiB."
    items:
      - {recurso: disco_raiz, estado: "96G total, 37G usados, 60G libres, 38%", etiqueta: ACTIVE_HEALTHY}
      - {recurso: carga, estado: "uptime 24d 12h; load 0.27, 0.35, 0.28", etiqueta: ACTIVE_HEALTHY}
      - {recurso: memoria, estado: "7.8GiB total, 3.4GiB usada, 4.3GiB disponible; sin swap", etiqueta: ACTIVE_HEALTHY}

  gateway:
    evidencia:
      comando: "openclaw status --all; openclaw models status con whitelist y secret-output-guard"
      salida_sanitizada: "Gateway reachable en loopback, Telegram OK, 8 agentes, 30 sesiones, OpenAI/Codex usable."
    estado:
      version: "2026.6.10; update 2026.7.1 disponible"
      endpoint: "loopback 127.0.0.1:18789"
      servicio: "enabled/running; PID 2526932"
      sesiones: 30
      agentes_totales: 8
      etiqueta: ACTIVE_NOISY
    warnings:
      - {detalle: "plugins.load.paths contiene una ruta bundled redundante", etiqueta: ACTIVE_DEGRADED}
      - {detalle: "models status emitio un fingerprint parcial Google Vertex; valor omitido", etiqueta: SECURITY_RISK}
      - {detalle: "bootstrap file figura ABSENT para los 8 agentes; no se determino si es intencional", etiqueta: UNKNOWN}
    providers:
      - {provider: openai, estado: "perfil presente; runtime Codex usable", clasificacion: provider_vivo, etiqueta: ACTIVE_HEALTHY}
      - {provider: anthropic, estado: "perfil presente; sin modelo configurado ni smoke; UMBRAL_DISABLE_CLAUDE existe pero su valor no fue leido", clasificacion: solo_definido, etiqueta: UNKNOWN}
      - {provider: google, estado: "perfil presente; sin modelo OpenClaw configurado ni smoke", clasificacion: solo_definido, etiqueta: UNKNOWN}
      - {provider: google-vertex, estado: "perfil presente; sin smoke; fingerprint parcial expuesto por CLI y omitido", clasificacion: solo_definido, etiqueta: SECURITY_RISK}
    modelos:
      - {modelo: openai/gpt-5.5, uso: default, estado: "provider vivo; sin smoke individual", etiqueta: ACTIVE_HEALTHY}
      - {modelo: openai/gpt-5.4, uso: fallback, estado: "provider vivo; sin smoke individual", etiqueta: ACTIVE_HEALTHY}
      - {modelo: openai/gpt-5.4-mini, uso: primario tracker/ops, estado: "provider vivo; sin smoke individual", etiqueta: ACTIVE_HEALTHY}
      - {modelo: openai/gpt-5.6-sol, uso: primario de 4 agentes, estado: "falla: requiere una version mas nueva de Codex", etiqueta: ACTIVE_DEGRADED}
      - {modelo: openai/gpt-5.3-codex, uso: primario delivery y fallback tracker/ops, estado: "falla: no soportado con la cuenta ChatGPT actual", etiqueta: ACTIVE_DEGRADED}
    agents:
      - {agent: main, modelo: openai/gpt-5.5, ultima_actividad: "46m", etiqueta: ACTIVE_HEALTHY}
      - {agent: rick-orchestrator, modelo: openai/gpt-5.6-sol, ultima_actividad: "29m", etiqueta: ACTIVE_DEGRADED}
      - {agent: rick-delivery, modelo: openai/gpt-5.3-codex, ultima_actividad: "4m", etiqueta: ACTIVE_DEGRADED}
      - {agent: rick-qa, modelo: openai/gpt-5.6-sol, ultima_actividad: "26m", etiqueta: ACTIVE_DEGRADED}
      - {agent: rick-tracker, modelo: openai/gpt-5.4-mini, ultima_actividad: "36m", etiqueta: ACTIVE_DEGRADED}
      - {agent: rick-ops, modelo: openai/gpt-5.4-mini, ultima_actividad: "11m", etiqueta: ACTIVE_DEGRADED}
      - {agent: rick-communication-director, modelo: openai/gpt-5.6-sol, ultima_actividad: "40m", etiqueta: ACTIVE_DEGRADED}
      - {agent: rick-linkedin-writer, modelo: openai/gpt-5.6-sol, ultima_actividad: "18d", etiqueta: ACTIVE_DEGRADED}

  worker:
    evidencia:
      comando: "curl -fsS http://127.0.0.1:8088/health | jq"
      salida_sanitizada: "ok=true; version=0.4.0; 118 handlers; tasks_in_memory=1000."
    estado: true
    version: "0.4.0"
    tasks_registered: 118
    tasks_in_memory: 1000
    familias:
      {azure: 1, browser: 6, client: 6, composite: 1, copilot_cli: 1, document: 3,
       figma: 5, github: 5, gmail: 2, google: 4, google_drive: 2, granola: 9,
       gui: 7, linear: 11, llm: 1, make: 1, n8n: 5, notion: 15, ping: 1,
       pit: 4, rag: 4, research: 1, rick: 1, system: 2, tournament: 1,
       tournament_lane: 5, web: 2, windows: 12}
    etiqueta: ACTIVE_DEGRADED

  logs_48h:
    evidencia:
      comando: "journalctl --user -u {umbral-worker,openclaw-gateway} --since '48 hours ago'; ventana equivalente sobre /tmp/notion_poller.log; firmas normalizadas"
      salida_sanitizada: "Frecuencias expresadas como lineas de log; una operacion puede producir varias lineas."
    items:
      - {origen: worker, error: "GOOGLE_API_KEY no configurada", frecuencia: "272 lineas", etiqueta: ACTIVE_DEGRADED}
      - {origen: worker, error: "Azure/OpenAI no configurado para llm.generate", frecuencia: "12 lineas", etiqueta: ACTIVE_DEGRADED}
      - {origen: worker, error: "POST /run devolvio HTTP 500", frecuencia: "27 lineas", etiqueta: ACTIVE_DEGRADED}
      - {origen: worker, error: "traceback", frecuencia: "37 lineas", etiqueta: ACTIVE_DEGRADED}
      - {origen: worker, error: "errores de transporte", frecuencia: "12 lineas", etiqueta: ACTIVE_DEGRADED}
      - {origen: notion-poller, error: "server errors con traceback", frecuencia: "18 lineas", etiqueta: ACTIVE_DEGRADED}
      - {origen: notion-poller, error: "poll iteration failed", frecuencia: "10 lineas", etiqueta: ACTIVE_DEGRADED}
      - {origen: notion-poller, error: "resolucion de review targets fallida", frecuencia: "8 lineas", etiqueta: ACTIVE_DEGRADED}
      - {origen: notion-poller, error: "log sin rotacion", frecuencia: "102170194 bytes; 61272 lineas en 48h", etiqueta: ACTIVE_NOISY}
      - {origen: gateway, error: "WebSocket closed before connect", frecuencia: "6722 lineas", etiqueta: ACTIVE_NOISY}
      - {origen: gateway, error: "gpt-5.6-sol requiere Codex mas nuevo", frecuencia: "1744 lineas", etiqueta: ACTIVE_DEGRADED}
      - {origen: gateway, error: "gpt-5.3-codex no soportado con cuenta ChatGPT", frecuencia: "416 lineas", etiqueta: ACTIVE_DEGRADED}
      - {origen: gateway, error: "rate limit/429", frecuencia: "136 lineas", etiqueta: ACTIVE_NOISY}
      - {origen: gateway, error: "embedded agent failed before reply", frecuencia: "192 lineas", etiqueta: ACTIVE_DEGRADED}

  env_nombres:
    evidencia:
      comando: "cut -d= -f1 ~/.config/openclaw/env; tr '\\0' '\\n' < /proc/$WORKER_PID/environ | cut -d= -f1"
      salida_sanitizada: "Solo nombres: 61 en openclaw/env y 82 en el proceso worker; ningun valor ni fingerprint."
    openclaw_env:
      cantidad: 61
      nombres:
        [BROWSER_HEADLESS, COPILOT_CLI_ALLOWED_REPO_ROOTS, DAVID_NOTION_USER_ID,
         EDITORIAL_BLOG_CANONICAL_BASE_URL, EDITORIAL_BLOG_FUNCTION_KEY,
         EDITORIAL_BLOG_FUNCTION_URL, ESCALATE_FAILURES_TO_LINEAR,
         ESCALATE_ONLY_CANONICAL, GCLOUD_LOCATION, GHCR_PAT, GITHUB_TOKEN,
         GPT_RICK_API_KEY, HOSTINGER_API_TOKEN, LINEAR_AGENT_STACK_PROJECT_ID,
         LINEAR_AGENT_STACK_PROJECT_NAME, LINEAR_API_KEY, MAKE_WEBHOOK_SIM_RUN,
         MISSION_CONTROL_TOKEN, N8N_API_KEY, N8N_URL, NODE_COMPILE_CACHE,
         NOTION_API_KEY, NOTION_BITACORA_DB_ID, NOTION_BRIDGE_DB_ID,
         NOTION_COMMERCIAL_PROJECTS_DB_ID, NOTION_CONTROL_ROOM_PAGE_ID,
         NOTION_DASHBOARD_PAGE_ID, NOTION_DELIVERABLES_DB_ID, NOTION_GRANOLA_DB_ID,
         NOTION_HUMAN_TASKS_DB_ID, NOTION_PROJECTS_DB_ID,
         NOTION_REPORTS_ARCHIVE_PAGE_ID, NOTION_SUPERVISOR_ALERT_PAGE_ID,
         NOTION_SUPERVISOR_API_KEY, NOTION_TASKS_DB_ID, OBSIDIAN_SYNC_MODE,
         OBSIDIAN_VAULT_PATH, OPENCLAW_NO_RESPAWN, PIT_VAULT_PATH,
         PIT_VAULT_WRITE_SCOPE, REDIS_URL, TAVILY_API_KEY, UMBRAL_DISABLE_CLAUDE,
         UMBRAL_DISCOVERY_DATABASE_ID, UMBRAL_DISCOVERY_DATA_SOURCE_ID,
         UMBRAL_DISCOVERY_REFERENTES_DS_ID, VM_TOKEN, VM_URL, WORKER_TOKEN,
         WORKER_URL, WORKER_URL_VM, WORKER_URL_VM_GUI, WORKER_URL_VM_INTERACTIVE,
         X_ACCESS_TOKEN, X_ACCESS_TOKEN_SECRET, X_API_KEY, X_API_SECRET,
         X_BEARER_TOKEN, X_CLIENT_ID, X_CLIENT_SECRET, YOUTUBE_DATA_API_KEY]
      etiqueta: ACTIVE_HEALTHY
    worker_env:
      cantidad: 82
      contiene_los_61_nombres_de_openclaw_env: true
      adicionales:
        [COPILOT_CLI_SANDBOX_IMAGE, COPILOT_GITHUB_TOKEN, DBUS_SESSION_BUS_ADDRESS,
         GSM_SKIP_SSH_AGENT_WORKAROUND, HOME, INVOCATION_ID, JOURNAL_STREAM, LANG,
         LOGNAME, MANAGERPID, MEMORY_PRESSURE_WATCH, MEMORY_PRESSURE_WRITE, PATH,
         RICK_COPILOT_CLI_ENABLED, RICK_COPILOT_CLI_EXECUTE, SHELL, SSH_AUTH_SOCK,
         SYSTEMD_EXEC_PID, USER, XDG_DATA_DIRS, XDG_RUNTIME_DIR]
      etiqueta: ACTIVE_HEALTHY
    matriz_critica:
      - {nombre: GOOGLE_API_KEY, openclaw_env: ausente, worker_env: ausente, etiqueta: ACTIVE_DEGRADED}
      - {nombre: ANTHROPIC_API_KEY, openclaw_env: ausente, worker_env: ausente, nota: "perfil existe en auth store; no live-smoke", etiqueta: UNKNOWN}
      - {nombre: UMBRAL_DISABLE_CLAUDE, openclaw_env: presente, worker_env: presente, nota: "valor deliberadamente no leido", etiqueta: UNKNOWN}
      - {nombre: NOTION_POLLER_ENABLE_V2_CLASSIFY, openclaw_env: ausente, worker_env: ausente, nota: "coherente con default-off fail-closed de #540", etiqueta: ACTIVE_HEALTHY}
      - {nombre: "AZURE_*", openclaw_env: ausente, worker_env: ausente, etiqueta: ACTIVE_DEGRADED}
      - {nombre: "OPENAI_*", openclaw_env: ausente, worker_env: ausente, nota: "OpenClaw usa OAuth; worker no", etiqueta: ACTIVE_DEGRADED}

  drift:
    evidencia:
      comando: "cd ~/umbral-agent-stack && git log --oneline -3; git status --short; git rev-parse HEAD origin/main; git ls-remote origin refs/heads/main"
      salida_sanitizada: "branch=main; status vacio; HEAD local, origin/main local y origin/main remoto coinciden."
    repo:
      branch: main
      dirty: no
      head: e90852196b6637dccf45d8718faeab08ffecabbc
      origin_main: e90852196b6637dccf45d8718faeab08ffecabbc
      produccion_repo_corre_main_limpio: si
      etiqueta: ACTIVE_HEALTHY
    ultimos_commits:
      - "e908521 | 2026-07-17T09:34:28-04:00 | fix poller P2a default-off"
      - "42b8861 | 2026-07-17T02:01:43-04:00 | fix Granola P1.1"
      - "83c0b68 | 2026-07-17T00:44:39-04:00 | feat Granola P1"
    runtime_vs_head:
      - {componente: notion-poller, estado: "inicio 09:35, posterior a HEAD 09:34", etiqueta: ACTIVE_HEALTHY}
      - {componente: worker, estado: "inicio 02:02, posterior a #539 pero anterior al HEAD actual", etiqueta: DRIFT_REPO_VPS}
      - {componente: dispatcher, estado: "inicio 2026-07-03; Python executable deleted", etiqueta: DRIFT_REPO_VPS}
      - {componente: mission-control, estado: "inicio 2026-07-03; Python executable deleted", etiqueta: DRIFT_REPO_VPS}
      - {componente: gateway, estado: "binario npm-global; no consume openclaw/** del repo", etiqueta: ACTIVE_NOISY}

  clones_vps:
    evidencia:
      comando: "ls -d ~/umbral-agent-stack* /tmp/*clean* /tmp/*-clean; git worktree list --porcelain; git status --porcelain y git log -1 por path"
      salida_sanitizada: "15 paths Git: 12 worktrees registrados y 3 clones archivados adicionales."
    items:
      - {path: /home/rick/umbral-agent-stack, rama: main, dirty: no, ultimo_commit_fecha: "e908521 2026-07-17T09:34:28-04:00", quien_lo_usa: "dispatcher, worker, mission-control, poller y 16 crons activos", estado_clone: ACTIVE, etiqueta: ACTIVE_HEALTHY, recomendacion: KEEP}
      - {path: /home/rick/.openclaw/workspaces/rick-delivery/umbral-agent-stack-poller-hardening, rama: rick-delivery/poller-healthcheck-hardening, dirty: no, ultimo_commit_fecha: "b7f8e41 2026-05-18T13:07:17-04:00", quien_lo_usa: "ningun proceso/cron observado", estado_clone: ORPHAN_LOCAL, etiqueta: ORPHAN, recomendacion: ARCHIVE}
      - {path: /home/rick/archive/uas/umbral-agent-stack-activation-playbook, rama: rick/copilot-cli-f6-step6c4f-activation-playbook, dirty: no, ultimo_commit_fecha: "bd85732 2026-04-29T20:49:24-04:00", quien_lo_usa: ninguno, estado_clone: STALE, etiqueta: ORPHAN, recomendacion: ARCHIVE}
      - {path: /home/rick/archive/uas/umbral-agent-stack-copilot-cli, rama: rick/copilot-cli-capability-design, dirty: no, ultimo_commit_fecha: "fa704e9 2026-04-27T01:54:23-04:00", quien_lo_usa: ninguno, estado_clone: STALE, etiqueta: ORPHAN, recomendacion: ARCHIVE}
      - {path: /home/rick/archive/uas/umbral-agent-stack-editorial, rama: rick/editorial-linkedin-writer-flow, dirty: no, ultimo_commit_fecha: "410266a 2026-05-05T02:57:41-04:00", quien_lo_usa: ninguno, estado_clone: STALE, etiqueta: ORPHAN, recomendacion: ARCHIVE}
      - {path: /home/rick/archive/uas/umbral-agent-stack-f7-code-gate, rama: rick/copilot-cli-f7-code-gate-rehearsal, dirty: no, ultimo_commit_fecha: "0d6ad83 2026-05-05T14:38:29-04:00", quien_lo_usa: ninguno, estado_clone: STALE, etiqueta: ORPHAN, recomendacion: ARCHIVE}
      - {path: /home/rick/archive/uas/umbral-agent-stack-f7-policy-gate, rama: rick/copilot-cli-f7-policy-gate-rehearsal, dirty: no, ultimo_commit_fecha: "b96a7eb 2026-05-05T03:52:17-04:00", quien_lo_usa: ninguno, estado_clone: STALE, etiqueta: ORPHAN, recomendacion: ARCHIVE}
      - {path: /home/rick/archive/uas/umbral-agent-stack-postmerge-evidence, rama: rick/copilot-cli-postmerge-evidence-6c4d, dirty: no, ultimo_commit_fecha: "7e96a87 2026-04-27T05:52:11-04:00", quien_lo_usa: ninguno, estado_clone: STALE, etiqueta: ORPHAN, recomendacion: ARCHIVE}
      - {path: /tmp/openclaw-oauth-apply-wt, rama: rick/openclaw-oauth-apply-20260713, dirty: si, ultimo_commit_fecha: "2f79709 2026-07-13T11:59:41-04:00", quien_lo_usa: "ningun proceso/cron; 1 task file modificado", estado_clone: DIRTY_HIGH_RISK, etiqueta: SECURITY_RISK, recomendacion: DO_NOT_TOUCH}
      - {path: /tmp/openclaw-oauth-only-urgent-wt, rama: rick/openclaw-oauth-only-urgent-20260713, dirty: si, ultimo_commit_fecha: "e5d650c 2026-07-13T01:45:09-04:00", quien_lo_usa: "ningun proceso/cron; 1 task file modificado", estado_clone: DIRTY_HIGH_RISK, etiqueta: SECURITY_RISK, recomendacion: DO_NOT_TOUCH}
      - {path: /tmp/rick-hb-20260713-0143/wt-candidate, rama: DETACHED, dirty: no, ultimo_commit_fecha: "0d70b67 2026-07-09T06:34:08-04:00", quien_lo_usa: "ningun proceso/cron; HEAD no contenido en origin/main", estado_clone: ORPHAN_LOCAL, etiqueta: ORPHAN, recomendacion: ARCHIVE}
      - {path: /tmp/rick-hb-20260713-0143/wt-replay-on-origin, rama: DETACHED, dirty: si, ultimo_commit_fecha: "e5d650c 2026-07-13T01:45:09-04:00", quien_lo_usa: "ninguno; dispatcher/notion_poller.py y test modificados", estado_clone: DIRTY_HIGH_RISK, etiqueta: SECURITY_RISK, recomendacion: DO_NOT_TOUCH}
      - {path: /home/rick/archive/uas/umbral-agent-stack-cand001-apply-20260629-174758, rama: main, dirty: no, ultimo_commit_fecha: "61de099 2026-06-29T16:34:35-04:00", quien_lo_usa: ninguno, estado_clone: STALE, etiqueta: OBSOLETE, recomendacion: DELETE_CANDIDATE}
      - {path: /home/rick/archive/uas/umbral-agent-stack-cursor, rama: rick/supervisor-structured-telemetry, dirty: no, ultimo_commit_fecha: "b376a4d 2026-04-20T13:48:48-04:00", quien_lo_usa: ninguno, estado_clone: STALE, etiqueta: ORPHAN, recomendacion: ARCHIVE}
      - {path: /home/rick/archive/uas/umbral-agent-stack.backup-pre-cand001-20260629-174640, rama: rick-delivery/editorial-contract-paths, dirty: si, ultimo_commit_fecha: "18cdc48 2026-06-29T06:06:42-04:00", quien_lo_usa: "ninguno; 29 untracked preservados", estado_clone: DIRTY_HIGH_RISK, etiqueta: SECURITY_RISK, recomendacion: DO_NOT_TOUCH}
    gate_archivo: "WHY.md prohibe borrado definitivo sin G-WH-VPS-2 y al menos 30 dias."

  skills_drift:
    evidencia:
      comando: "diff -rq ~/.openclaw/workspace/skills ~/umbral-agent-stack/openclaw/workspace-templates/skills | head -40"
      salida_sanitizada:
        only_live: 10
        only_repo: 49
        files_differ: 27
        total_differences: 86
        ejemplos_only_live: [google-agenda-readiness, granola-meeting-capitalization, "desktop.ini residuales"]
        ejemplos_only_repo: [acc-bim360, azure-audio, azure-platform, bim-expert, copilot-studio, document-generation, figma, github-ops, gmail, granola-pipeline]
        ejemplos_difieren: [agent-handoff-governance, director-comunicacion-umbral, editorial-source-curation, editorial-voice-profile, external-reference-intelligence, google-calendar]
    etiqueta: DRIFT_REPO_VPS

  redis_claves:
    evidencia:
      comando: "redis-cli --scan --pattern '*cursor*' | head -20"
      salida_sanitizada: "PONG; 12 nombres; no se ejecuto GET ni otra lectura de valores."
    items:
      - {nombre: "notion:poll:cursor:31f5f443-fb5c-81e8-8689-f2a9e863002b", etiqueta: ACTIVE_HEALTHY}
      - {nombre: "notion:poll:cursor:31f5f443-fb5c-8115-9182-d8321da22c0d", etiqueta: ACTIVE_HEALTHY}
      - {nombre: "notion:poll:cursor:31e5f443-fb5c-8125-a21c-e5333fb32a03", etiqueta: ACTIVE_HEALTHY}
      - {nombre: "notion:poll:cursor:34b5f443-fb5c-81dd-8338-cb0b46699250", etiqueta: ACTIVE_HEALTHY}
      - {nombre: "notion:poll:cursor:30c5f443fb5c80eeb721dc5727b20dca", etiqueta: ACTIVE_HEALTHY}
      - {nombre: "notion:poll:cursor:31f5f443-fb5c-8155-832c-dd91e22e1aaf", etiqueta: ACTIVE_HEALTHY}
      - {nombre: "notion:poll:cursor:31f5f443-fb5c-81d1-8469-c5c76833af30", etiqueta: ACTIVE_HEALTHY}
      - {nombre: "notion:poll:cursor:3205f443-fb5c-81e2-b58e-ee73c01a0804", etiqueta: ACTIVE_HEALTHY}
      - {nombre: "notion:poll:cursor:3415f443-fb5c-81c2-9aaa-c788008edf8f", etiqueta: ACTIVE_HEALTHY}
      - {nombre: "notion:poll:cursor:31e5f443-fb5c-8180-bec7-cbcda641b3b7", etiqueta: ACTIVE_HEALTHY}
      - {nombre: "notion:poll:cursor:3415f443-fb5c-81dd-b0b6-f3ef52a76b64", etiqueta: ACTIVE_HEALTHY}
      - {nombre: "notion:poll:cursor:31f5f443-fb5c-8198-8632-c79bc95f5696", etiqueta: ACTIVE_HEALTHY}

  oportunidades:
    - {accion: "Rotar inmediatamente la credencial/perfil Google Vertex cuyo fingerprint parcial fue emitido por el CLI, siguiendo secret-output-guard.", etiqueta: SECURITY_RISK}
    - {accion: "Actualizar OpenClaw/Codex y luego validar o reasignar gpt-5.6-sol y gpt-5.3-codex; hoy provocan fallbacks y fallas repetidas.", etiqueta: ACTIVE_DEGRADED}
    - {accion: "Definir un backend real para llm.generate/classify en el worker o desactivar fail-closed esas rutas; faltan GOOGLE_API_KEY y Azure/OpenAI.", etiqueta: ACTIVE_DEGRADED}
    - {accion: "En ventana autorizada, reiniciar y verificar dispatcher/Mission Control para abandonar Python deleted y cargar main actual.", etiqueta: DRIFT_REPO_VPS}
    - {accion: "Agregar rotacion al log de poller, investigar el origen de 6722 cierres WS y reconciliar las 86 diferencias de skills antes de cualquier sync.", etiqueta: ACTIVE_NOISY}

  unknowns:
    - {detalle: "No se leyo el valor de UMBRAL_DISABLE_CLAUDE ni de ninguna otra variable.", etiqueta: UNKNOWN}
    - {detalle: "Anthropic, Google y Google Vertex tienen perfiles, pero no se ejecutaron smokes de provider/modelo.", etiqueta: UNKNOWN}
    - {detalle: "No se identifico el cliente que origina los cierres WebSocket antes de conectar.", etiqueta: UNKNOWN}
    - {detalle: "La ejecucion cada minuto de scheduled-tasks no pudo demostrarse por journal; las corridas no-op no escriben log.", etiqueta: UNKNOWN}
    - {detalle: "No se determino si bootstrap ABSENT para los 8 agentes es intencional.", etiqueta: UNKNOWN}
    - {detalle: "No se auditaron stashes ni contenido de cambios locales en clones; solo nombres de paths y estados Git.", etiqueta: UNKNOWN}
    - {detalle: "n8n fue verificado por systemd, no mediante un health/API smoke.", etiqueta: UNKNOWN}
```

Created 12 todos
