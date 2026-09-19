#!/usr/bin/env bash
# =================================================================
# bateria-canario.sh — validación del canario antes de integrarlo.
#
# CI en verde no basta: las pruebas unitarias no ejercitan el canario contra un
# turno real ni bajo el entorno de cron, que es justo donde fallaron sus dos
# primeras versiones (PATH mínimo y token literal). Esta batería cubre los ocho
# casos exigidos, más cuatro que añadió la revisión adversarial del 2026-09-19: que la
# degradación se vea aunque la respuesta no traiga el token literal, que se
# cierre cuando el primario vuelve, que el retroceso enganche aunque cambie el
# modelo de reserva, y que un fallback indeterminado no cierre nada. Con stubs deterministas para lo que no se
# puede provocar a voluntad en producción.
#
#   bash scripts/vps/bateria-canario.sh [directorio-de-salida]
#
# No toca producción: el estado y el ops_log van a un sandbox, y las
# notificaciones las recibe un stub HTTP local.
# =================================================================
set -uo pipefail

REPO_DIR="${REPO_DIR:-$HOME/umbral-agent-stack}"
OUT_DIR="${1:-$(mktemp -d)}"
mkdir -p "$OUT_DIR"
SB="$OUT_DIR/sandbox"; mkdir -p "$SB/state" "$SB/ops" "$SB/bin"
CAP="$OUT_DIR/notificaciones.jsonl"; : > "$CAP"
OPS="$SB/ops/ops_log.jsonl"; : > "$OPS"

OK=0; TOTAL=0
pass() { OK=$((OK+1)); TOTAL=$((TOTAL+1)); echo "  [PASS] $1"; }
fail() { TOTAL=$((TOTAL+1)); echo "  [FAIL] $1"; }

export UMBRAL_MON_STATE_DIR="$SB/state"
export UMBRAL_OPS_LOG_DIR="$SB/ops"

echo "=== Batería de validación del canario ==="
echo "utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)  salida=$OUT_DIR"
echo

# ---- stubs deterministas -----------------------------------------
# Un turno correcto por el PRIMARIO (sin fallback).
cat > "$SB/bin/primario-sano" <<'STUB'
#!/usr/bin/env bash
tok=$(printf '%s' "$*" | grep -oE 'CANARIO-[0-9]+' | head -1)
cat <<JSON
{"ok":true,"result":{"text":"$tok","completion":{"stopReason":"stop"},
"routing":{"candidates":[{"provider":"openai","model":"gpt-5.6-sol","result":"success"}],"fallbackUsed":false}}}
JSON
STUB
# Un turno correcto por el FALLBACK.
cat > "$SB/bin/fallback-sano" <<'STUB'
#!/usr/bin/env bash
tok=$(printf '%s' "$*" | grep -oE 'CANARIO-[0-9]+' | head -1)
cat <<JSON
{"ok":true,"result":{"text":"$tok","completion":{"stopReason":"stop"},
"routing":{"candidates":[{"provider":"openai","model":"gpt-5.6-sol","result":"candidate_failed"},
{"provider":"anthropic","model":"claude-sonnet-5","result":"success"}],"fallbackUsed":true}}}
JSON
STUB
# Fallo DURO: el turno no termina.
cat > "$SB/bin/fallo-duro" <<'STUB'
#!/usr/bin/env bash
echo "Embedded agent failed before reply: Auth profile unavailable" >&2
exit 1
STUB
# Fallo BLANDO: respuesta semanticamente correcta, sin el token literal.
cat > "$SB/bin/fallo-blando" <<'STUB'
#!/usr/bin/env bash
cat <<'JSON'
{"ok":true,"result":{"text":"Claro, aqui tienes el identificador solicitado.","completion":{"stopReason":"stop"},
"routing":{"candidates":[{"provider":"anthropic","model":"claude-sonnet-5","result":"success"}],"fallbackUsed":true}}}
JSON
STUB
# Mismo estado cualitativo que fallback-sano —el primario no sirve— pero por
# OTRO modelo. Sirve para el caso 11: mientras el primario esta caido, los
# perfiles tienen enfriamientos independientes y el modelo de reserva cambia de
# un ciclo a otro.
cat > "$SB/bin/fallback-otro-modelo" <<'STUB'
#!/usr/bin/env bash
tok=$(printf '%s' "$*" | grep -oE 'CANARIO-[0-9]+' | head -1)
cat <<JSON
{"ok":true,"result":{"text":"$tok","completion":{"stopReason":"stop"},
"routing":{"candidates":[{"provider":"openai","model":"gpt-5.6-sol","result":"candidate_failed"},
{"provider":"anthropic","model":"claude-haiku-4-5","result":"success"}],"fallbackUsed":true}}}
JSON
STUB
# Turno correcto que NO declara si hubo fallback: el JSON del CLI es externo y
# ya ha cambiado de forma varias veces. "No se sabe" no es "no hubo".
cat > "$SB/bin/sin-declarar-fallback" <<'STUB'
#!/usr/bin/env bash
tok=$(printf '%s' "$*" | grep -oE 'CANARIO-[0-9]+' | head -1)
cat <<JSON
{"ok":true,"result":{"text":"$tok","completion":{"stopReason":"stop"},
"routing":{"candidates":[{"provider":"anthropic","model":"claude-sonnet-5","result":"success"}]}}}
JSON
STUB
chmod +x "$SB/bin"/*

canario() { OPENCLAW_BIN="$1" timeout 240 bash "$REPO_DIR/scripts/vps/canary-inference.sh" 2>&1; }

# ---- 1. entorno real de cron, contra el agente de verdad ----------
echo "1. Entorno real de cron (PATH mínimo, sin variables), turno real"
SAL=$(env -i HOME="$HOME" PATH=/usr/bin:/bin \
      UMBRAL_MON_STATE_DIR="$SB/state" UMBRAL_OPS_LOG_DIR="$SB/ops" \
      timeout 300 bash "$REPO_DIR/scripts/vps/canary-inference.sh" 2>&1)
RC=$?
echo "$SAL" > "$OUT_DIR/1-cron-real.txt"
if [ $RC -eq 0 ] && printf '%s' "$SAL" | grep -q '\[OK\]'; then
  pass "el canario funciona bajo cron y resuelve el binario ($(printf '%s' "$SAL" | grep -oE '[a-z]+/[a-z0-9.-]+' | head -1))"
else
  fail "el canario no funcionó bajo el entorno de cron (exit $RC)"
fi

# ---- 2. primario sano --------------------------------------------
echo "2. Primario sano"
SAL=$(canario "$SB/bin/primario-sano"); RC=$?
echo "$SAL" > "$OUT_DIR/2-primario.txt"
L=$(grep '"kind":"canary_inference"' "$OPS" | tail -1)
if [ $RC -eq 0 ] && printf '%s' "$L" | grep -q '"status":"ok"' \
   && printf '%s' "$L" | grep -q '"provider":"openai"' \
   && printf '%s' "$L" | grep -q '"fallback_used":false'; then
  pass "turno correcto por el primario, proveedor identificado, sin fallback"
else
  fail "no se reconoció el primario sano: $L"
fi

# ---- 3. fallback sano --------------------------------------------
echo "3. Fallback sano"
SAL=$(canario "$SB/bin/fallback-sano"); RC=$?
echo "$SAL" > "$OUT_DIR/3-fallback.txt"
L=$(grep '"kind":"canary_inference"' "$OPS" | tail -1)
if [ $RC -eq 0 ] && printf '%s' "$L" | grep -q '"provider":"anthropic"' \
   && printf '%s' "$L" | grep -q '"fallback_used":true' \
   && printf '%s' "$SAL" | grep -q 'POR FALLBACK'; then
  pass "turno correcto por el fallback, y queda dicho que el primario no sirvió"
else
  fail "no se distinguió el fallback: $L"
fi

# ---- 4. fallo duro -----------------------------------------------
echo "4. Fallo duro (el turno no termina)"
SAL=$(canario "$SB/bin/fallo-duro"); RC=$?
echo "$SAL" > "$OUT_DIR/4-duro.txt"
L=$(grep '"kind":"canary_inference"' "$OPS" | tail -1)
if [ $RC -eq 1 ] && printf '%s' "$L" | grep -q '"status":"fail"'; then
  pass "el fallo duro se reporta como fallo de salud (exit 1)"
else
  fail "el fallo duro no se reportó como tal (exit $RC): $L"
fi

# ---- 5. fallo blando ---------------------------------------------
echo "5. Fallo blando: respuesta correcta sin el token literal"
SAL=$(canario "$SB/bin/fallo-blando"); RC=$?
echo "$SAL" > "$OUT_DIR/5-blando.txt"
L=$(grep '"kind":"canary_inference"' "$OPS" | tail -1)
if [ $RC -eq 0 ] && printf '%s' "$L" | grep -q '"status":"ok_sin_token"' \
   && printf '%s' "$L" | grep -q '"token_literal":"no"'; then
  pass "no se cuenta como caída: el turno fue estructuralmente correcto y queda registrada la no-conformidad"
else
  fail "una respuesta correcta sin token se trató como caída (exit $RC): $L"
fi

# ---- 6 y 7. deduplicación y recuperación única --------------------
echo "6. Deduplicación   7. Recuperación única"
STUB_PORT="${STUB_PORT:-8397}"
python3 - "$STUB_PORT" "$CAP" <<'PY' &
import json, sys
from http.server import BaseHTTPRequestHandler, HTTPServer
port, dest = int(sys.argv[1]), sys.argv[2]
class H(BaseHTTPRequestHandler):
    def do_POST(self):
        n = int(self.headers.get("Content-Length", 0))
        raw = self.rfile.read(n).decode("utf-8", "replace")
        with open(dest, "a", encoding="utf-8") as f:
            f.write(json.dumps({"body": raw}, ensure_ascii=False) + "\n")
        self.send_response(200); self.end_headers(); self.wfile.write(b'{"ok":true}')
    def do_GET(self):
        self.send_response(200); self.end_headers(); self.wfile.write(b'{"ok":true}')
    def log_message(self, *a): pass
HTTPServer(("127.0.0.1", port), H).serve_forever()
PY
STUB_PID=$!
trap 'kill "$STUB_PID" 2>/dev/null' EXIT
sleep 1

export UMBRAL_SKIP_CANARY=1 WORKER_TOKEN="bateria"
hc() { WORKER_URL="http://127.0.0.1:${STUB_PORT}" GATEWAY_URL="$1" bash "$REPO_DIR/scripts/vps/health-check.sh" > "$2" 2>&1; }
hc "http://127.0.0.1:18899" "$OUT_DIR/6a-fallo.txt"; N1=$(wc -l < "$CAP")
hc "http://127.0.0.1:18899" "$OUT_DIR/6b-repetido.txt"; N2=$(wc -l < "$CAP")
if [ "$N2" -eq "$N1" ] && [ "$N1" -ge 1 ] && grep -q 'silenciada' "$OUT_DIR/6b-repetido.txt"; then
  pass "el mismo fallo no vuelve a notificar ($N1 -> $N2)"
else
  fail "la repetición volvió a notificar ($N1 -> $N2)"
fi
hc "http://127.0.0.1:${STUB_PORT}" "$OUT_DIR/7a-recuperado.txt"; N3=$(wc -l < "$CAP")
hc "http://127.0.0.1:${STUB_PORT}" "$OUT_DIR/7b-estable.txt"; N4=$(wc -l < "$CAP")
if [ "$N3" -gt "$N2" ] && [ "$N4" -eq "$N3" ]; then
  pass "la recuperación se anuncia una sola vez ($N2 -> $N3 -> $N4)"
else
  fail "la recuperación no se anunció una sola vez ($N2 -> $N3 -> $N4)"
fi
unset UMBRAL_SKIP_CANARY

# ---- 8. el stub no puede ser sobrescrito por el entorno real ------
echo "8. El destino del ensayo no lo pisa el archivo de entorno"
ENVF="$SB/env-falso"; printf 'WORKER_URL=http://produccion-real:8088\nWORKER_TOKEN=de-produccion\n' > "$ENVF"
R=$(UMBRAL_ENV_FILE="$ENVF" WORKER_URL="http://127.0.0.1:${STUB_PORT}" bash -c '
  source "'"$REPO_DIR"'/scripts/vps/lib/umbral_alerting.sh"
  umbral_load_env
  echo "URL=$WORKER_URL"')
echo "$R" > "$OUT_DIR/8-stub-protegido.txt"
if printf '%s' "$R" | grep -q "127.0.0.1:${STUB_PORT}"; then
  pass "el WORKER_URL del ensayo sobrevive a la carga del entorno real"
else
  fail "el entorno real pisó el destino del ensayo: $R"
fi

# ---- 9 y 10. la degradación se ve, y se cierra cuando el primario vuelve ----
# El stub sigue en pie desde el caso 6; el gateway apunta a él para que el único
# motivo de aviso sea el canario.
echo "9. La degradación se anuncia aunque falte el token literal"
hcc() { OPENCLAW_BIN="$1" WORKER_URL="http://127.0.0.1:${STUB_PORT}" \
        GATEWAY_URL="http://127.0.0.1:${STUB_PORT}" \
        bash "$REPO_DIR/scripts/vps/health-check.sh" > "$2" 2>&1; }
hcc "$SB/bin/fallo-blando" "$OUT_DIR/9-degradado.txt"
# El aviso no puede llevar la latencia: la huella se calcula sobre el cuerpo, y
# un valor que cambia en cada ciclo convierte cada ciclo en un "estado nuevo".
if grep -q 'respondio por fallback' "$OUT_DIR/9-degradado.txt" \
   && [ -f "$UMBRAL_MON_STATE_DIR/health-check-degradado.alert" ] \
   && ! grep -q 'latency_ms' "$CAP"; then
  pass "un turno correcto sin el token literal no oculta que el primario no sirvió, y el aviso no lleva nada volátil"
else
  fail "la degradación pasó inadvertida cuando la respuesta no traía el token"
fi

echo "10. El primario recuperado cierra la degradación"
hcc "$SB/bin/primario-sano" "$OUT_DIR/10-primario-vuelve.txt"
# El aviso se comprueba en lo que RECIBIÓ el destino, no en lo que imprimió el
# monitor: el titulo no se echa por stdout, y comprobarlo ahi daria un fallo que
# no existe.
if [ ! -f "$UMBRAL_MON_STATE_DIR/health-check-degradado.alert" ] \
   && grep -q 'primario vuelve a atender' "$CAP"; then
  pass "al volver el primario se anuncia y se cierra el estado degradado"
else
  fail "el estado degradado siguió abierto tras volver el primario"
fi

# ---- 11 y 12. el retroceso engancha, y lo indeterminado no cierra nada ----
echo "11. Una degradación que cambia de modelo sigue siendo la misma degradación"
N_ANTES=$(grep -c 'responde solo por fallback' "$CAP" 2>/dev/null || echo 0)
for s in fallback-sano fallback-otro-modelo fallo-blando fallback-sano; do
  hcc "$SB/bin/$s" "$OUT_DIR/11-$s.txt"
done
N_DESPUES=$(grep -c 'responde solo por fallback' "$CAP" 2>/dev/null || echo 0)
NUEVOS=$(( N_DESPUES - N_ANTES ))
# Cuatro ciclos con proveedor, modelo y estado distintos: el estado CUALITATIVO
# es uno solo —el primario no atiende— asi que debe avisar una vez y callar tres.
# Si el cuerpo del aviso llevara esos datos, cada ciclo pareceria nuevo, el
# contador volveria a cero y saldria un comentario cada media hora para siempre.
if [ "$NUEVOS" -le 1 ]; then
  pass "cuatro ciclos con proveedor y modelo distintos produjeron $NUEVOS aviso(s): el retroceso engancha"
else
  fail "el retroceso no enganchó: $NUEVOS avisos en cuatro ciclos del mismo estado"
fi

echo "12. Un fallback indeterminado no cierra la degradación"
hcc "$SB/bin/sin-declarar-fallback" "$OUT_DIR/12-indeterminado.txt"
if [ -f "$UMBRAL_MON_STATE_DIR/health-check-degradado.alert" ] \
   && grep -q 'no pudo determinar si hubo fallback' "$OUT_DIR/12-indeterminado.txt"; then
  pass "sin dato no se declara recuperado: el incidente sigue abierto"
else
  fail "un turno que no declara el fallback cerró la degradación"
fi

echo
echo "=== Resultado: $OK/$TOTAL ==="
cp "$OPS" "$OUT_DIR/ops_log-de-la-bateria.jsonl" 2>/dev/null
echo "Evidencia en $OUT_DIR"
[ "$OK" -eq "$TOTAL" ] && exit 0
exit 1
