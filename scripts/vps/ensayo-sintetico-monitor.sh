#!/usr/bin/env bash
# =================================================================
# ensayo-sintetico-monitor.sh — demuestra que la cadena de aviso funciona.
#
# Inyecta una degradación REAL y comprueba los seis pasos que exige el encargo:
#   1 detección  2 registro  3 notificación  4 deduplicación  5 recuperación  6 cierre
#
# No toca producción: el monitor se apunta a puertos muertos, el estado va a un
# directorio temporal y la notificación la recibe un stub HTTP local que la
# registra en vez de enviarla a Notion. No se mata ningún proceso, no se reinicia
# ningún servicio y no se escribe en Notion ni en Linear.
#
#   bash scripts/vps/ensayo-sintetico-monitor.sh [directorio-de-salida]
#
# Salida: 0 si los seis pasos pasan; 1 si alguno falla.
# =================================================================
set -uo pipefail

REPO_DIR="${REPO_DIR:-$HOME/umbral-agent-stack}"
OUT_DIR="${1:-$(mktemp -d)}"
mkdir -p "$OUT_DIR"
SANDBOX="$OUT_DIR/sandbox"
mkdir -p "$SANDBOX/state" "$SANDBOX/ops"
CAPTURA="$OUT_DIR/notificaciones.jsonl"
: > "$CAPTURA"

PASOS_OK=0
PASOS_TOTAL=6
fallo() { echo "  [FAIL] $1"; }
ok()    { echo "  [PASS] $1"; PASOS_OK=$(( PASOS_OK + 1 )); }

echo "=== Ensayo sintético de la cadena de aviso ==="
echo "utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
echo "salida=$OUT_DIR"
echo "VENTANA DE ENSAYO: los eventos de este intervalo son sintéticos, no un incidente real."
echo

# ---------------------------------------------------------------
# Stub que hace de worker: acepta el POST /run y lo guarda.
# ---------------------------------------------------------------
STUB_PORT="${STUB_PORT:-8399}"
python3 - "$STUB_PORT" "$CAPTURA" <<'PY' &
import json, sys
from http.server import BaseHTTPRequestHandler, HTTPServer
port, dest = int(sys.argv[1]), sys.argv[2]
class H(BaseHTTPRequestHandler):
    def do_POST(self):
        n = int(self.headers.get("Content-Length", 0))
        raw = self.rfile.read(n).decode("utf-8", "replace")
        with open(dest, "a", encoding="utf-8") as f:
            f.write(json.dumps({"path": self.path, "body": raw}, ensure_ascii=False) + "\n")
        self.send_response(200); self.end_headers(); self.wfile.write(b'{"ok":true}')
    def do_GET(self):
        self.send_response(200); self.end_headers(); self.wfile.write(b'{"ok":true}')
    def log_message(self, *a): pass
HTTPServer(("127.0.0.1", port), H).serve_forever()
PY
STUB_PID=$!
trap 'kill "$STUB_PID" 2>/dev/null' EXIT   # solo el stub de este ensayo, nada del sistema
sleep 1

export UMBRAL_MON_STATE_DIR="$SANDBOX/state"
export UMBRAL_OPS_LOG_DIR="$SANDBOX/ops"
export UMBRAL_SKIP_CANARY=1          # el canario gasta una inferencia real; aquí se mide la cadena de aviso
export WORKER_TOKEN="ensayo-sintetico"
OPS="$SANDBOX/ops/ops_log.jsonl"
# Se crea de antemano para aislar la variable bajo prueba: sin esto, el primer
# ciclo falla ademas por "ops_log no encontrado" y el segundo no, de modo que el
# estado cambia de verdad entre ciclos y la deduplicacion no aplica.
: > "$OPS"

# ---------------------------------------------------------------
# 1. DETECCIÓN — se degrada el GATEWAY, que es el caso real del incidente
#    UMB-276, y se deja el worker en pie apuntando al stub.
#
#    LIMITACIÓN CONOCIDA, descubierta por este mismo ensayo: la vía de aviso
#    sale POR el worker. Si el que cae es el worker, el monitor detecta y
#    registra, pero el aviso no puede salir. Es un punto único de fallo real y
#    queda anotado como brecha para T3-C; no se puede cerrar desde aquí sin un
#    segundo canal independiente.
# ---------------------------------------------------------------
echo "1. Detección"
SALIDA1=$(WORKER_URL="http://127.0.0.1:${STUB_PORT}" GATEWAY_URL="http://127.0.0.1:18899" \
          bash "$REPO_DIR/scripts/vps/health-check.sh" 2>&1)
RC1=$?
echo "$SALIDA1" > "$OUT_DIR/paso1-deteccion.txt"
if [ $RC1 -ne 0 ] && printf '%s' "$SALIDA1" | grep -q 'check(s) failed'; then
  ok "el monitor detectó la degradación (exit $RC1)"
else
  fallo "el monitor NO detectó la degradación (exit $RC1)"
fi

# ---------------------------------------------------------------
# 2. REGISTRO — en la fuente canónica, no en una superficie nueva.
# ---------------------------------------------------------------
echo "2. Registro"
if [ -f "$OPS" ] && grep -q '"kind":"health_check","status":"fail"' "$OPS"; then
  ok "quedó registrado en ops_log.jsonl"
else
  fallo "no hay registro del fallo en ops_log.jsonl"
fi

# ---------------------------------------------------------------
# 3. NOTIFICACIÓN — salió de verdad, y cabe en el límite de Notion.
# ---------------------------------------------------------------
echo "3. Notificación"
N=$(wc -l < "$CAPTURA" 2>/dev/null || echo 0)
if [ "$N" -ge 1 ]; then
  LARGO=$(python3 -c '
import json,sys
l=open(sys.argv[1],encoding="utf-8").readline()
print(len(json.loads(json.loads(l)["body"])["input"]["text"]))' "$CAPTURA" 2>/dev/null || echo 99999)
  if [ "$LARGO" -lt 2000 ]; then
    ok "se envió la notificación ($LARGO caracteres, por debajo del máximo de Notion)"
  else
    fallo "la notificación excede el máximo de Notion ($LARGO caracteres)"
  fi
else
  fallo "no se envió ninguna notificación"
fi

# ---------------------------------------------------------------
# 4. DEDUPLICACIÓN — el mismo fallo no vuelve a avisar.
# ---------------------------------------------------------------
echo "4. Deduplicación"
WORKER_URL="http://127.0.0.1:${STUB_PORT}" GATEWAY_URL="http://127.0.0.1:18899" \
  bash "$REPO_DIR/scripts/vps/health-check.sh" > "$OUT_DIR/paso4-dedup.txt" 2>&1
N2=$(wc -l < "$CAPTURA")
if [ "$N2" -eq "$N" ] && grep -q 'silenciada' "$OUT_DIR/paso4-dedup.txt"; then
  ok "la repetición se silenció (notificaciones: $N -> $N2)"
else
  fallo "la repetición volvió a notificar (notificaciones: $N -> $N2)"
fi

# ---------------------------------------------------------------
# 5. RECUPERACIÓN — se restablece y avisa UNA vez, como transición.
# ---------------------------------------------------------------
echo "5. Recuperación"
SALIDA5=$(WORKER_URL="http://127.0.0.1:${STUB_PORT}" GATEWAY_URL="http://127.0.0.1:${STUB_PORT}" \
          bash "$REPO_DIR/scripts/vps/health-check.sh" 2>&1)
RC5=$?
echo "$SALIDA5" > "$OUT_DIR/paso5-recuperacion.txt"
N3=$(wc -l < "$CAPTURA")
if [ $RC5 -eq 0 ] && [ "$N3" -gt "$N2" ]; then
  ok "se recuperó y avisó de la vuelta a la normalidad (exit 0, notificaciones: $N2 -> $N3)"
else
  fallo "no hubo recuperación limpia (exit $RC5, notificaciones: $N2 -> $N3)"
fi

# ---------------------------------------------------------------
# 6. CIERRE — el estado vuelve a limpio y no queda alerta abierta.
# ---------------------------------------------------------------
echo "6. Cierre"
SALIDA6=$(WORKER_URL="http://127.0.0.1:${STUB_PORT}" GATEWAY_URL="http://127.0.0.1:${STUB_PORT}" \
          bash "$REPO_DIR/scripts/vps/health-check.sh" 2>&1)
N4=$(wc -l < "$CAPTURA")
if [ ! -f "$SANDBOX/state/health-check.alert" ] && [ "$N4" -eq "$N3" ]; then
  ok "cerrado: sin alerta abierta y sin avisos repetidos tras la recuperación"
else
  fallo "el cierre dejó estado sucio o siguió avisando"
fi

echo
echo "=== Resultado: $PASOS_OK/$PASOS_TOTAL pasos ==="
cp "$CAPTURA" "$OUT_DIR/notificaciones-capturadas.jsonl" 2>/dev/null
echo "Evidencia en $OUT_DIR"
[ "$PASOS_OK" -eq "$PASOS_TOTAL" ] && exit 0
exit 1
