"""Pruebas de la cadena de aviso de los monitores del VPS.

Nacen del incidente Linear UMB-276: el stack estuvo 3,7 días sin poder generar
texto y ningún monitor avisó. Cada prueba de aquí fija uno de los puntos en que
la cadena estaba rota, de modo que no puedan volver a romperse en silencio.
"""

from __future__ import annotations

import json
import os
import subprocess
import textwrap
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
LIB = REPO / "scripts" / "vps" / "lib" / "umbral_alerting.sh"


def run_bash(script: str, env: dict[str, str] | None = None) -> subprocess.CompletedProcess:
    full = f'set -uo pipefail\nsource "{LIB}"\n{script}'
    e = {**os.environ, **(env or {})}
    return subprocess.run(["bash", "-c", full], capture_output=True, text=True, env=e)


@pytest.fixture()
def state_dir(tmp_path: Path) -> dict[str, str]:
    d = tmp_path / "monitor"
    d.mkdir()
    return {
        "UMBRAL_MON_STATE_DIR": str(d),
        "UMBRAL_OPS_LOG_DIR": str(tmp_path / "ops"),
    }


H = 3600     # una hora en segundos: la unidad en que esta escrita la cadencia
TOPE = 82800  # el tope del retroceso: 23 h, por debajo de la cadencia diaria de e2e

# Un aviso ENTREGADO: decidir y, solo entonces, abrir la ventana de silencio.
# Es lo que hace umbral_alert cuando el envio se confirma.
ENTREGADO = 'entregado() { umbral_should_alert "$1" "$2" && umbral_commit_alert "$1" "$2"; }\n'


def alerta(state_dir: dict[str, str], monitor: str) -> Path:
    return Path(state_dir["UMBRAL_MON_STATE_DIR"]) / f"{monitor}.alert"


def ops_log(state_dir: dict[str, str]) -> Path:
    return Path(state_dir["UMBRAL_OPS_LOG_DIR"]) / "ops_log.jsonl"


def reavisos(f: Path) -> int:
    return int(f.read_text(encoding="utf-8").split()[2])


def adelantar_reloj(f: Path, segundos: int) -> None:
    """Reloj controlado: atrasa la marca del estado, que es exactamente lo que
    ve el monitor cuando pasa el tiempo. Asi la secuencia entera de ventanas se
    recorre sin esperar 24 horas y sin meter un reloj falso en produccion."""
    fp, ts, n = f.read_text(encoding="utf-8").split()
    f.write_text(f"{fp}\n{int(ts) - segundos}\n{n}\n", encoding="utf-8")


class _WorkerStub:
    def __init__(self) -> None:
        self.url = ""
        self.codigo = 200
        self.recibidas: list[str] = []

    @property
    def env(self) -> dict[str, str]:
        return {
            "WORKER_URL": self.url,
            "WORKER_TOKEN": "token-de-prueba",
            "UMBRAL_ENV_FILE": "/dev/null",
        }


@pytest.fixture()
def worker_stub():
    """Destino local del aviso, con codigo de respuesta gobernable.

    Nunca sale de 127.0.0.1: el 2026-09-18 un ensayo cuyo destino acabo siendo
    el real dejo cuatro avisos de prueba en la pagina de alertas de David."""
    stub = _WorkerStub()

    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):
            n = int(self.headers.get("Content-Length") or 0)
            stub.recibidas.append(self.rfile.read(n).decode("utf-8"))
            self.send_response(stub.codigo)
            self.send_header("Content-Length", "2")
            self.end_headers()
            self.wfile.write(b"{}")

        def log_message(self, *a):  # silencio en la salida de pytest
            pass

    srv = HTTPServer(("127.0.0.1", 0), Handler)
    stub.url = f"http://127.0.0.1:{srv.server_port}"
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    try:
        yield stub
    finally:
        srv.shutdown()
        srv.server_close()


class TestTruncado:
    """Notion rechaza comentarios largos con 400. Pasó de verdad el 2026-09-18."""

    def test_texto_corto_no_se_toca(self, state_dir):
        r = run_bash('umbral_truncate "hola" 100', state_dir)
        assert r.stdout == "hola"

    def test_texto_largo_queda_bajo_el_maximo(self, state_dir):
        r = run_bash(f'umbral_truncate "{"x" * 5000}" 1900', state_dir)
        assert len(r.stdout) <= 1900
        assert "recortado" in r.stdout

    def test_el_maximo_por_defecto_es_menor_que_el_de_notion(self, state_dir):
        # El límite real de la API es 2000; el nuestro deja margen.
        r = run_bash(f'umbral_truncate "{"y" * 9000}"', state_dir)
        assert 0 < len(r.stdout) < 2000

    def test_el_borde_exacto_no_se_pasa(self, state_dir):
        r = run_bash('umbral_truncate "' + "z" * 1901 + '" 1900', state_dir)
        assert len(r.stdout) <= 1900


class TestHuella:
    """Sin normalizar lo volátil, cada ciclo genera una huella nueva y el
    monitor se convierte en ruido: 1026 corridas del dashboard produjeron
    1026 huellas distintas y cero omisiones."""

    def test_misma_falla_distinta_hora_misma_huella(self, state_dir):
        a = run_bash('umbral_fingerprint "Worker caido 2026-09-18T06:00:00Z pid=123 tardo 250ms"', state_dir).stdout
        b = run_bash('umbral_fingerprint "Worker caido 2026-09-18T07:30:00Z pid=987 tardo 812ms"', state_dir).stdout
        assert a == b != ""

    def test_fallas_distintas_huellas_distintas(self, state_dir):
        a = run_bash('umbral_fingerprint "Worker caido"', state_dir).stdout
        b = run_bash('umbral_fingerprint "Redis caido"', state_dir).stdout
        assert a != b


class TestDeduplicacionYEnfriamiento:
    """Avisar del mismo estado en cada ciclo convierte el monitor en ruido."""

    def test_primer_aviso_pasa_y_el_repetido_calla(self, state_dir):
        r = run_bash(
            ENTREGADO +
            'entregado mon huella-1 && echo PRIMERO; '
            'umbral_should_alert mon huella-1 && echo SEGUNDO || echo SILENCIADO',
            state_dir,
        )
        assert "PRIMERO" in r.stdout
        assert "SILENCIADO" in r.stdout

    def test_un_estado_nuevo_rompe_el_silencio(self, state_dir):
        r = run_bash(
            ENTREGADO +
            'entregado mon huella-1 >/dev/null; '
            'umbral_should_alert mon huella-2 && echo AVISA || echo CALLA',
            state_dir,
        )
        assert "AVISA" in r.stdout

    def test_vencido_el_enfriamiento_vuelve_a_avisar(self, state_dir):
        r = run_bash(
            ENTREGADO +
            'entregado mon h >/dev/null; '
            'UMBRAL_ALERT_COOLDOWN_S=0 umbral_should_alert mon h && echo AVISA || echo CALLA',
            state_dir,
        )
        assert "AVISA" in r.stdout

    def test_la_recuperacion_se_anuncia_una_sola_vez(self, state_dir):
        r = run_bash(
            ENTREGADO +
            'entregado mon h >/dev/null; '
            'umbral_clear_alert mon && echo RECUPERADO; '
            'umbral_clear_alert mon && echo OTRA_VEZ || echo YA_ESTABA_SANO',
            state_dir,
        )
        assert "RECUPERADO" in r.stdout
        assert "YA_ESTABA_SANO" in r.stdout


class TestLatido:
    """La caída del propio monitor se detecta por AUSENCIA de marca fresca.
    El silencio de un log no distingue 'todo bien' de 'cron murió'."""

    def test_sin_marca_se_considera_rancio(self, state_dir):
        r = run_bash('umbral_heartbeat_stale nunca 60 && echo RANCIO || echo FRESCO', state_dir)
        assert "RANCIO" in r.stdout

    def test_marca_recien_escrita_esta_fresca(self, state_dir):
        r = run_bash('umbral_heartbeat_write mon; umbral_heartbeat_stale mon 60 && echo RANCIO || echo FRESCO', state_dir)
        assert "FRESCO" in r.stdout

    def test_marca_vieja_se_detecta(self, state_dir):
        d = Path(state_dir["UMBRAL_MON_STATE_DIR"])
        (d / "viejo.beat").write_text("1000000000\n", encoding="utf-8")
        r = run_bash('umbral_heartbeat_stale viejo 60 && echo RANCIO || echo FRESCO', state_dir)
        assert "RANCIO" in r.stdout

    def test_la_edad_sin_marca_es_negativa(self, state_dir):
        r = run_bash('umbral_heartbeat_age inexistente', state_dir)
        assert r.stdout.strip() == "-1"


class TestEstadoDurable:
    """El estado no puede vivir en /tmp: systemd-tmpfiles borra a los 30 días
    justo la prueba de que un monitor enmudeció."""

    def test_el_directorio_por_defecto_no_es_tmp(self):
        texto = LIB.read_text(encoding="utf-8")
        linea = next(l for l in texto.splitlines() if l.startswith("UMBRAL_MON_STATE_DIR="))
        assert "/tmp" not in linea


class TestOpsLog:
    def test_escribe_una_linea_json_por_evento(self, state_dir):
        run_bash('umbral_ops_log \'{"kind":"prueba","n":1}\'', state_dir)
        f = Path(state_dir["UMBRAL_OPS_LOG_DIR"]) / "ops_log.jsonl"
        assert json.loads(f.read_text(encoding="utf-8").strip())["kind"] == "prueba"


class TestCargaDeEntorno:
    """health-check.sh no hacía source del env, así que WORKER_TOKEN llegaba
    vacío bajo cron y el aviso se saltaba en silencio."""

    def test_exporta_las_variables_del_archivo(self, tmp_path, state_dir):
        env_file = tmp_path / "env"
        env_file.write_text("WORKER_TOKEN=secreto-de-prueba\n", encoding="utf-8")
        r = run_bash(
            'umbral_load_env && [ -n "${WORKER_TOKEN:-}" ] && echo CARGADO',
            {**state_dir, "UMBRAL_ENV_FILE": str(env_file)},
        )
        assert "CARGADO" in r.stdout

    def test_no_falla_si_el_archivo_no_existe(self, tmp_path, state_dir):
        r = run_bash(
            'umbral_load_env || echo SIN_ARCHIVO',
            {**state_dir, "UMBRAL_ENV_FILE": str(tmp_path / "no-existe")},
        )
        assert "SIN_ARCHIVO" in r.stdout

    def test_el_aviso_no_imprime_el_token(self, tmp_path, state_dir):
        env_file = tmp_path / "env"
        env_file.write_text("WORKER_TOKEN=token-secretisimo\n", encoding="utf-8")
        r = run_bash(
            'umbral_load_env; WORKER_URL=http://127.0.0.1:1 umbral_alert mon "titulo" "cuerpo" error || true',
            {**state_dir, "UMBRAL_ENV_FILE": str(env_file)},
        )
        assert "token-secretisimo" not in (r.stdout + r.stderr)


class TestCodigoDeSalidaDelE2E:
    """Regresión del defecto exacto: `set -euo pipefail` hacía inalcanzable el
    bloque de alerta, porque e2e_validation.py termina en sys.exit(1)."""

    def test_el_patron_roto_falla(self, tmp_path):
        roto = textwrap.dedent(
            """
            set -euo pipefail
            python3 -c 'import sys; sys.exit(1)'
            EXIT_CODE=$?
            echo "ALCANZADO exit=$EXIT_CODE"
            """
        )
        r = subprocess.run(["bash", "-c", roto], capture_output=True, text=True)
        assert "ALCANZADO" not in r.stdout, "este es el bug original; si aparece, el patrón cambió"

    def test_el_patron_corregido_captura_el_codigo(self, tmp_path):
        bueno = textwrap.dedent(
            """
            set -euo pipefail
            set +e
            python3 -c 'import sys; sys.exit(1)'
            EXIT_CODE=$?
            set -e
            echo "ALCANZADO exit=$EXIT_CODE"
            """
        )
        r = subprocess.run(["bash", "-c", bueno], capture_output=True, text=True)
        assert "ALCANZADO exit=1" in r.stdout

    def test_el_script_real_usa_el_patron_corregido(self):
        lineas = (REPO / "scripts" / "vps" / "e2e-validation-cron.sh").read_text(encoding="utf-8").splitlines()
        # La invocación real, no las menciones en comentarios.
        idx = [i for i, l in enumerate(lineas)
               if "e2e_validation.py" in l and not l.lstrip().startswith("#")]
        assert len(idx) == 1, f"se esperaba una sola invocación, hay {len(idx)}"
        i = idx[0]
        previas = [l.strip() for l in lineas[:i] if l.strip() and not l.lstrip().startswith("#")]
        assert previas[-1] == "set +e", "la invocación debe ir precedida de set +e"
        assert lineas[i + 1].strip() == "EXIT_CODE=$?", "el código de salida debe capturarse en la línea siguiente"


class TestCanario:
    """El canario debe medir el camino REAL del agente. Medido el 2026-09-18:
    `capability model run` daba 200 por un perfil api-key mientras el agente,
    atado a los perfiles OAuth, no podía responder."""

    def test_usa_un_turno_de_agente_y_no_el_atajo_del_cli(self):
        texto = (REPO / "scripts" / "vps" / "canary-inference.sh").read_text(encoding="utf-8")
        assert "agent --agent" in texto and "$OPENCLAW_BIN" in texto
        cuerpo = texto[texto.index("set -uo pipefail"):]
        assert "capability model run" not in cuerpo, "el atajo del CLI da falsos verdes"

    def test_no_aborta_ante_un_fallo_del_modelo(self):
        texto = (REPO / "scripts" / "vps" / "canary-inference.sh").read_text(encoding="utf-8")
        assert "set -uo pipefail" in texto and "set -euo pipefail" not in texto

    def test_registra_si_respondio_por_fallback(self):
        texto = (REPO / "scripts" / "vps" / "canary-inference.sh").read_text(encoding="utf-8")
        assert "fallback_used" in texto


class TestHealthCheck:
    def test_vigila_el_gateway(self):
        texto = (REPO / "scripts" / "vps" / "health-check.sh").read_text(encoding="utf-8")
        assert "GATEWAY_URL" in texto and "/health" in texto

    def test_incluye_el_canario(self):
        texto = (REPO / "scripts" / "vps" / "health-check.sh").read_text(encoding="utf-8")
        assert "canary-inference.sh" in texto

    def test_carga_el_entorno(self):
        texto = (REPO / "scripts" / "vps" / "health-check.sh").read_text(encoding="utf-8")
        assert "umbral_load_env" in texto

    def test_detecta_monitores_rancios(self):
        texto = (REPO / "scripts" / "vps" / "health-check.sh").read_text(encoding="utf-8")
        assert "umbral_heartbeat_stale" in texto


class TestElEntornoNoPisaAlLlamador:
    """Regresión del fallo del 2026-09-18: el archivo de entorno sobrescribía un
    WORKER_URL puesto a propósito para un ensayo y cuatro avisos sintéticos
    acabaron en la página real de alertas."""

    def test_no_sobrescribe_una_variable_ya_definida(self, tmp_path, state_dir):
        env_file = tmp_path / "env"
        env_file.write_text("WORKER_URL=http://produccion:8088\n", encoding="utf-8")
        r = run_bash(
            'umbral_load_env; echo "URL=$WORKER_URL"',
            {**state_dir, "UMBRAL_ENV_FILE": str(env_file), "WORKER_URL": "http://stub-de-ensayo:8399"},
        )
        assert "URL=http://stub-de-ensayo:8399" in r.stdout

    def test_si_falta_la_toma_del_archivo(self, tmp_path, state_dir):
        env_file = tmp_path / "env"
        env_file.write_text("WORKER_URL=http://produccion:8088\n", encoding="utf-8")
        env = {**state_dir, "UMBRAL_ENV_FILE": str(env_file)}
        env.pop("WORKER_URL", None)
        r = subprocess.run(
            ["bash", "-c", f'set -uo pipefail\nunset WORKER_URL\nsource "{LIB}"\numbral_load_env; echo "URL=$WORKER_URL"'],
            capture_output=True, text=True, env={**os.environ, **env},
        )
        assert "URL=http://produccion:8088" in r.stdout

    def test_ignora_comentarios_y_lineas_vacias(self, tmp_path, state_dir):
        env_file = tmp_path / "env"
        env_file.write_text("# comentario\n\nMIVAR=valor\n", encoding="utf-8")
        r = run_bash('umbral_load_env && echo "V=$MIVAR"', {**state_dir, "UMBRAL_ENV_FILE": str(env_file)})
        assert "V=valor" in r.stdout


class TestCanarioBajoCron:
    """El PATH de cron es mínimo y `openclaw` vive en ~/.npm-global/bin. Sin
    resolver la ruta, el canario reportaba «no puede generar texto» cuando en
    realidad no encontraba la herramienta: falsa alarma real el 2026-09-18 15:00Z."""

    def test_resuelve_el_binario_explicitamente(self):
        texto = (REPO / "scripts" / "vps" / "canary-inference.sh").read_text(encoding="utf-8")
        assert "OPENCLAW_BIN" in texto
        assert ".npm-global/bin/openclaw" in texto
        assert '"$OPENCLAW_BIN" agent --agent' in texto

    def test_distingue_entorno_de_incapacidad(self):
        texto = (REPO / "scripts" / "vps" / "canary-inference.sh").read_text(encoding="utf-8")
        # 127 (no existe) y 126 (no ejecutable) son problemas de entorno -> exit 2.
        assert "126" in texto and "127" in texto
        assert "exit 2" in texto

    def test_sin_binario_no_dice_que_el_modelo_fallo(self, tmp_path, state_dir):
        r = subprocess.run(
            ["bash", str(REPO / "scripts" / "vps" / "canary-inference.sh")],
            capture_output=True, text=True,
            env={"HOME": str(tmp_path), "PATH": "/usr/bin:/bin",
                 "OPENCLAW_BIN": str(tmp_path / "no-existe"),
                 **state_dir},
        )
        assert r.returncode == 2
        assert "ENTORNO" in r.stdout
        assert "no pudo generar texto" not in r.stdout


class TestCriterioDeSaludDelCanario:
    """La salud es el éxito ESTRUCTURAL del turno y el proveedor utilizado.
    El token literal es evidencia adicional, nunca el único criterio: tomarlo
    como tal produjo un falso negativo el 2026-09-18 (el agente respondió bien
    y el canario declaró «no puede generar texto»)."""

    def test_evalua_estructura_y_no_solo_el_token(self):
        texto = (REPO / "scripts" / "vps" / "canary-inference.sh").read_text(encoding="utf-8")
        assert 'result") == "success"' in texto, "debe exigir un candidato con éxito"
        assert "stopReason" in texto and "finishReason" in texto, "debe exigir cierre del turno"
        assert "EV_ESTRUCTURA" in texto

    def test_una_respuesta_sin_token_no_es_caida(self):
        texto = (REPO / "scripts" / "vps" / "canary-inference.sh").read_text(encoding="utf-8")
        assert "ok_sin_token" in texto
        cierre = texto[texto.index("case \"$STATUS\" in\n  ok|ok_sin_token"):]
        assert "exit 0" in cierre, "ok_sin_token debe salir con 0"

    def test_registra_el_proveedor_utilizado(self):
        texto = (REPO / "scripts" / "vps" / "canary-inference.sh").read_text(encoding="utf-8")
        for campo in ('\\"provider\\"', '\\"model\\"', '\\"fallback_used\\"', '\\"token_literal\\"'):
            assert campo in texto, f"falta {campo} en el registro"

    def test_registra_el_commit_en_ejecucion(self):
        texto = (REPO / "scripts" / "vps" / "canary-inference.sh").read_text(encoding="utf-8")
        assert "umbral_release_sha" in texto


class TestBateriaDeValidacion:
    """CI en verde no basta: las dos primeras versiones del canario pasaron CI y
    fallaron en producción (PATH de cron y token literal)."""

    def test_la_bateria_existe_y_cubre_los_diez_casos(self):
        texto = (REPO / "scripts" / "vps" / "bateria-canario.sh").read_text(encoding="utf-8")
        for caso in ("Entorno real de cron", "Primario sano", "Fallback sano",
                     "Fallo duro", "Fallo blando", "Deduplicación",
                     "Recuperación única", "no lo pisa el archivo de entorno",
                     "aunque falte el token literal", "cierra la degradación"):
            assert caso in texto, f"la batería no cubre: {caso}"

    def test_la_bateria_no_escribe_en_produccion(self):
        texto = (REPO / "scripts" / "vps" / "bateria-canario.sh").read_text(encoding="utf-8")
        assert "UMBRAL_MON_STATE_DIR=" in texto and "UMBRAL_OPS_LOG_DIR=" in texto
        assert "127.0.0.1" in texto


class TestRetrocesoExponencial:
    """Un estado degradado ya registrado en un incidente abierto no debe avisar
    cada hora indefinidamente: eso desensibiliza a quien lo lee, que es como se
    pierde el aviso que sí importa. Medido el 2026-09-18: el aviso «responde solo
    por fallback» era CIERTO y aun así generó 4 comentarios en Notion en cuatro
    horas sobre una condición ya conocida.

    La cadencia se comprueba de dos maneras independientes: como función pura
    (sin reloj) y recorriendo la secuencia completa con un reloj controlado."""

    def test_la_ventana_documentada_por_numero_de_reaviso(self, state_dir):
        r = run_bash(
            'for n in 0 1 2 3 4 5 6 20; do printf "%s " "$(umbral_alert_window $n)"; done',
            state_dir,
        )
        assert r.stdout.split() == [
            "3600",    # 1 h  — primer reaviso
            "7200",    # 2 h
            "14400",   # 4 h
            "28800",   # 8 h
            "57600",   # 16 h
            "82800",   # 23 h — tope: como mucho un aviso al día
            "82800",
            "82800",
        ], r.stdout

    def test_la_secuencia_completa_con_reloj_controlado(self, state_dir):
        """1 h → 2 h → 4 h → 8 h → 16 h → tope de 23 h, recorrida de verdad.

        En cada escalón se comprueban los dos bordes: un segundo antes de que
        venza la ventana el monitor calla, y al cumplirse avisa. Sin los dos
        bordes, una ventana de cero segundos pasaría la prueba igual."""
        f = alerta(state_dir, "mon")
        r = run_bash(ENTREGADO + 'entregado mon h && echo AVISA', state_dir)
        assert "AVISA" in r.stdout
        assert reavisos(f) == 0

        for i, ventana in enumerate([1 * H, 2 * H, 4 * H, 8 * H, 16 * H, TOPE, TOPE]):
            adelantar_reloj(f, ventana - 1)
            r = run_bash('umbral_should_alert mon h && echo AVISA || echo CALLA', state_dir)
            assert "CALLA" in r.stdout, f"reaviso {i}: avisó antes de cumplirse {ventana}s"

            adelantar_reloj(f, 1)
            r = run_bash(ENTREGADO + 'entregado mon h && echo AVISA || echo CALLA', state_dir)
            assert "AVISA" in r.stdout, f"reaviso {i}: no avisó al cumplirse {ventana}s"
            assert reavisos(f) == i + 1

    def test_un_estado_nuevo_devuelve_la_ventana_a_una_hora(self, state_dir):
        """No basta con que el contador vuelva a cero: la ventana real tiene que
        volver a ser de una hora. Si no, una degradación distinta quedaría tapada
        por el silencio que ganó la anterior."""
        f = alerta(state_dir, "mon")
        run_bash(ENTREGADO + 'entregado mon h1', state_dir)
        for ventana in (1 * H, 2 * H):
            adelantar_reloj(f, ventana)
            run_bash(ENTREGADO + 'entregado mon h1', state_dir)
        assert reavisos(f) == 2          # la ventana en curso sería de 4 h

        r = run_bash(ENTREGADO + 'entregado mon h2-distinta && echo AVISA', state_dir)
        assert "AVISA" in r.stdout, "una degradación distinta debe avisar ya"
        assert reavisos(f) == 0

        adelantar_reloj(f, 1 * H - 1)
        r = run_bash('umbral_should_alert mon h2-distinta && echo AVISA || echo CALLA', state_dir)
        assert "CALLA" in r.stdout
        adelantar_reloj(f, 1)
        r = run_bash('umbral_should_alert mon h2-distinta && echo AVISA || echo CALLA', state_dir)
        assert "AVISA" in r.stdout, "tras un estado nuevo la ventana debe ser de 1 h otra vez"

    def test_la_recuperacion_reinicia_el_retroceso(self, state_dir):
        """Un fallo que vuelve tras una recuperación es noticia, aunque el estado
        anterior hubiera acumulado silencio."""
        f = alerta(state_dir, "mon")
        run_bash(ENTREGADO + 'entregado mon h', state_dir)
        for ventana in (1 * H, 2 * H, 4 * H):
            adelantar_reloj(f, ventana)
            run_bash(ENTREGADO + 'entregado mon h', state_dir)
        assert reavisos(f) == 3

        run_bash('umbral_clear_alert mon', state_dir)
        r = run_bash(ENTREGADO + 'entregado mon h && echo AVISA || echo CALLA', state_dir)
        assert "AVISA" in r.stdout
        assert reavisos(f) == 0

    def test_el_aviso_silenciado_declara_la_ventana_real(self, state_dir):
        """El mensaje de silencio decía siempre «3600s» aunque la ventana en
        curso fuera de horas: un informe que no coincide con la conducta."""
        r = run_bash(
            'umbral_commit_alert mon "$(umbral_fingerprint "t c")" 2; '
            'umbral_alert mon "t" "c" error || true',
            {**state_dir, "UMBRAL_ENV_FILE": "/dev/null"},
        )
        assert "14400" in r.stdout, r.stdout


class TestEntregaYSilencio:
    """El silencio lo gana un aviso ENTREGADO, nunca un aviso intentado.

    Hasta el 2026-09-19 el estado de silencio se escribía antes de intentar el
    envío: un aviso que no lograba salir silenciaba igualmente el ciclo
    siguiente durante una hora, y cada reintento que cruzaba la ventana
    duplicaba ese silencio. Como la vía de aviso sale por el worker que se
    vigila, «no se pudo entregar» es exactamente el caso en que hay que
    insistir. Es la misma familia de fallo que UMB-276: dar por avisado lo que
    nadie recibió."""

    def test_una_entrega_confirmada_abre_la_ventana(self, state_dir, worker_stub):
        env = {**state_dir, **worker_stub.env}
        r = run_bash('umbral_alert mon "titulo" "cuerpo" error; echo "rc=$?"', env)
        assert "rc=0" in r.stdout
        assert len(worker_stub.recibidas) == 1
        assert alerta(state_dir, "mon").exists()

        r = run_bash('umbral_alert mon "titulo" "cuerpo" error; echo "rc=$?"', env)
        assert "rc=1" in r.stdout, "una entrega confirmada sí debe silenciar el repetido"
        assert len(worker_stub.recibidas) == 1

    def test_una_entrega_fallida_no_abre_la_ventana(self, state_dir, worker_stub):
        worker_stub.codigo = 500
        env = {**state_dir, **worker_stub.env}
        r = run_bash('umbral_alert mon "titulo" "cuerpo" error; echo "rc=$?"', env)
        assert "rc=2" in r.stdout
        assert not alerta(state_dir, "mon").exists(), \
            "un aviso que no se entregó no puede abrir una ventana de silencio"

    def test_tras_un_fallo_de_entrega_el_siguiente_ciclo_reintenta(self, state_dir, worker_stub):
        """La prueba que faltaba: el monitor enmudecía justo cuando el destino
        del aviso estaba caído."""
        worker_stub.codigo = 500
        env = {**state_dir, **worker_stub.env}
        run_bash('umbral_alert mon "titulo" "cuerpo" error', env)
        assert len(worker_stub.recibidas) == 1

        worker_stub.codigo = 200          # el worker vuelve
        r = run_bash('umbral_alert mon "titulo" "cuerpo" error; echo "rc=$?"', env)
        assert "rc=0" in r.stdout, "el intento siguiente no debe estar silenciado"
        assert len(worker_stub.recibidas) == 2
        assert alerta(state_dir, "mon").exists()

    def test_varios_fallos_seguidos_no_acumulan_silencio(self, state_dir, worker_stub):
        """Sin esta garantía, cada fallo de entrega duplicaba la ventana y el
        monitor se iba callando solo hasta las 24 h sin haber avisado nunca."""
        worker_stub.codigo = 500
        env = {**state_dir, **worker_stub.env}
        for _ in range(4):
            run_bash('umbral_alert mon "titulo" "cuerpo" error', env)
        assert len(worker_stub.recibidas) == 4, "cada ciclo debe volver a intentarlo"
        assert not alerta(state_dir, "mon").exists()

    def test_sin_token_tampoco_abre_la_ventana(self, state_dir, worker_stub):
        env = {**state_dir, **worker_stub.env, "WORKER_TOKEN": "", "UMBRAL_ENV_FILE": "/dev/null"}
        r = run_bash('umbral_alert mon "titulo" "cuerpo" error; echo "rc=$?"', env)
        assert "rc=2" in r.stdout
        assert not alerta(state_dir, "mon").exists()

    def test_el_registro_distingue_entregado_de_intentado(self, state_dir, worker_stub):
        """El ops_log anotaba `monitor_alert` aunque el envío hubiera fallado, y
        esa línea es la que después se cuenta como «aviso emitido»."""
        worker_stub.codigo = 500
        env = {**state_dir, **worker_stub.env}
        run_bash('umbral_alert mon "titulo" "cuerpo" error', env)
        worker_stub.codigo = 200
        run_bash('umbral_alert mon "titulo" "cuerpo" error', env)

        eventos = [json.loads(l) for l in ops_log(state_dir).read_text(encoding="utf-8").splitlines()]
        clases = [e["kind"] for e in eventos]
        assert clases.count("monitor_alert_failed") == 1
        assert clases.count("monitor_alert") == 1
        fallido = next(e for e in eventos if e["kind"] == "monitor_alert_failed")
        assert fallido["motivo"] == "error_de_envio"
        emitido = next(e for e in eventos if e["kind"] == "monitor_alert")
        assert emitido["entrega"] == "ok"

    def test_la_recuperacion_no_se_da_por_cerrada_sin_entregarla(self):
        """Si el aviso de recuperación no sale, el incidente sigue abierto: de
        otro modo el último mensaje que le consta a un humano es el del fallo."""
        for script in ("health-check.sh", "e2e-validation-cron.sh"):
            texto = (REPO / "scripts" / "vps" / script).read_text(encoding="utf-8")
            assert "umbral_alert_active" in texto, script
            assert 'RC_INFO" -ne 2' in texto, script

    def test_el_envio_tiene_tiempo_maximo(self):
        """Un envío colgado bajo cron deja al monitor sin terminar, y un monitor
        que no termina es un monitor que no vuelve a comprobar nada."""
        assert '-m "${UMBRAL_ALERT_TIMEOUT_S:' in LIB.read_text(encoding="utf-8"), \
            "el tiempo maximo tiene que llegar al curl, no solo estar definido"


class TestCierreDeLaDegradacion:
    """Hallazgos de la revisión adversarial del propio cambio. Los cinco son
    defectos de la misma familia: un estado que nadie cierra, o una señal que se
    reconoce por su prosa en vez de por su forma."""

    STUB_FALLBACK_SIN_TOKEN = """#!/usr/bin/env bash
cat <<'JSON'
{"ok":true,"result":{"text":"respuesta sin el token","completion":{"stopReason":"stop"},
"routing":{"candidates":[{"provider":"anthropic","model":"claude-sonnet-5","result":"success"}],"fallbackUsed":true}}}
JSON
"""

    def test_el_canario_declara_el_fallback_aunque_falte_el_token(self, tmp_path, state_dir):
        """«POR FALLBACK» solo se imprimía en el estado ok. Un turno correcto sin
        el token literal ocultaba que el primario no había servido: el monitor
        veía salud y la degradación no se anunciaba."""
        stub = tmp_path / "openclaw"
        stub.write_text(self.STUB_FALLBACK_SIN_TOKEN, encoding="utf-8")
        stub.chmod(0o755)
        r = subprocess.run(
            ["bash", str(REPO / "scripts" / "vps" / "canary-inference.sh")],
            capture_output=True, text=True,
            env={**os.environ, **state_dir, "OPENCLAW_BIN": str(stub)},
        )
        assert "status=ok_sin_token" in r.stdout
        assert "fallback=true" in r.stdout, r.stdout

    def test_el_monitor_no_reconoce_la_degradacion_por_una_frase(self):
        texto = (REPO / "scripts" / "vps" / "health-check.sh").read_text(encoding="utf-8")
        assert "fallback=true" in texto
        assert "grep -q 'POR FALLBACK'" not in texto

    def test_el_primario_recuperado_cierra_la_degradacion(self):
        """Nadie borraba `health-check-degradado.alert`: el retroceso acumulado
        sobrevivía a la recuperación y podía amordazar la siguiente degradación
        hasta el tope."""
        texto = (REPO / "scripts" / "vps" / "health-check.sh").read_text(encoding="utf-8")
        assert "umbral_alert_active health-check-degradado" in texto
        assert "umbral_clear_alert health-check-degradado" in texto

    def test_abrir_un_incidente_olvida_el_aviso_de_recuperacion(self, state_dir, worker_stub):
        """El texto del aviso de recuperación es siempre el mismo, así que su
        huella también. Sin olvidarlo al abrir el incidente siguiente, la
        segunda recuperación quedaba silenciada por la ventana que ganó la
        primera — y con el retroceso, hasta un día entero. El resultado sería
        una cadena de fallos anunciados sin ningún cierre."""
        env = {**state_dir, **worker_stub.env}
        run_bash('umbral_alert mon "cayo" "detalle" error', env)
        run_bash('umbral_alert mon "ya esta sano" "todo pasa" info', env)
        assert alerta(state_dir, "mon.info").exists()

        run_bash('umbral_clear_alert mon', env)          # lo que hace el monitor al sanar
        run_bash('umbral_alert mon "cayo" "detalle" error', env)
        assert not alerta(state_dir, "mon.info").exists(), \
            "abrir un incidente debe olvidar el ultimo aviso de recuperacion"

        r = run_bash('umbral_alert mon "ya esta sano" "todo pasa" info; echo "rc=$?"', env)
        assert "rc=0" in r.stdout, "la segunda recuperacion tambien tiene que anunciarse"

    def test_el_tope_queda_por_debajo_de_la_cadencia_del_monitor_mas_lento(self, state_dir):
        """e2e-validation corre una vez al día. Con un tope de exactamente 24 h,
        la comparación contra el ciclo del día siguiente se decide por unos
        segundos de deriva y el aviso se va a 48 h la mitad de las veces: el tope
        deja de ser un tope y pasa a ser una lotería."""
        r = run_bash('umbral_alert_window 99', state_dir)
        tope = int(r.stdout.strip())
        assert tope < 86400, "el tope debe quedar por debajo de una cadencia diaria"
        assert tope == 82800

    def test_el_envio_espera_mas_que_el_cliente_de_notion_del_worker(self):
        """Con 20 s se cortaba una entrega lenta que el worker sí iba a
        completar: se contaba como fallida y el ciclo siguiente la repetía, con
        un comentario duplicado en Notion."""
        worker = (REPO / "worker" / "notion_client.py").read_text(encoding="utf-8")
        suyo = float(next(l for l in worker.splitlines()
                          if l.startswith("TIMEOUT")).split("=")[1].strip())
        lib = LIB.read_text(encoding="utf-8")
        nuestro = int(lib.split("UMBRAL_ALERT_TIMEOUT_S:-")[1].split("}")[0])
        assert nuestro > suyo, (
            f"el aviso espera {nuestro}s y el worker puede tardar {suyo}s contra Notion")

    def test_la_huella_no_soporta_numeros_pequenos_volatiles(self, state_dir):
        """El normalizador de la huella solo neutraliza números de tres cifras o
        más. Una latencia de dos cifras en el cuerpo del aviso haría que cada
        ciclo pareciera un estado nuevo y avisara cada media hora para siempre;
        por eso lo volátil no entra en el cuerpo, sino en el ops_log, que no
        deduplica."""
        marca = "[CANARIO] status=ok provider=anthropic model=claude-sonnet-5 fallback=true"
        r = run_bash(f'umbral_fingerprint "{marca} latency_ms=95"; '
                     f'umbral_fingerprint "{marca} latency_ms=87"', state_dir)
        cortas = r.stdout.split()
        assert cortas[0] != cortas[1], "si esto empieza a coincidir, revisa el normalizador"

        r = run_bash(f'umbral_fingerprint "{marca}"; umbral_fingerprint "{marca}"', state_dir)
        iguales = r.stdout.split()
        assert iguales[0] == iguales[1]

    def test_el_aviso_degradado_no_lleva_la_latencia(self):
        texto = (REPO / "scripts" / "vps" / "health-check.sh").read_text(encoding="utf-8")
        bloque = texto[texto.index("health-check-degradado \\"):]
        assert "latency_ms=[0-9]+//" in bloque[:900], \
            "el cuerpo del aviso degradado debe quitar la latencia antes de enviarlo"
