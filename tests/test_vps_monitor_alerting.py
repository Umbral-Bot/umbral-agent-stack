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
    def test_primer_aviso_pasa_y_el_repetido_calla(self, state_dir):
        r = run_bash(
            'umbral_should_alert mon huella-1 && echo PRIMERO; '
            'umbral_should_alert mon huella-1 && echo SEGUNDO || echo SILENCIADO',
            state_dir,
        )
        assert "PRIMERO" in r.stdout
        assert "SILENCIADO" in r.stdout
        assert "SEGUNDO" not in r.stdout

    def test_un_estado_nuevo_rompe_el_silencio(self, state_dir):
        r = run_bash(
            'umbral_should_alert mon huella-1 >/dev/null; '
            'umbral_should_alert mon huella-2 && echo AVISA || echo CALLA',
            state_dir,
        )
        assert "AVISA" in r.stdout

    def test_vencido_el_enfriamiento_vuelve_a_avisar(self, state_dir):
        r = run_bash(
            'umbral_should_alert mon h >/dev/null; '
            'UMBRAL_ALERT_COOLDOWN_S=0 umbral_should_alert mon h && echo AVISA || echo CALLA',
            {**state_dir, "UMBRAL_ALERT_COOLDOWN_S": "0"},
        )
        assert "AVISA" in r.stdout

    def test_la_recuperacion_se_anuncia_una_sola_vez(self, state_dir):
        r = run_bash(
            'umbral_should_alert mon h >/dev/null; '
            'umbral_clear_alert mon && echo RECUPERADO; '
            'umbral_clear_alert mon && echo OTRA_VEZ || echo YA_ESTABA_SANO',
            state_dir,
        )
        assert "RECUPERADO" in r.stdout
        assert "YA_ESTABA_SANO" in r.stdout
        assert "OTRA_VEZ" not in r.stdout


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


class TestCanarioFallosBlandos:
    """El modelo a veces no devuelve el token exacto aunque el turno vaya bien.
    Observado el 2026-09-18: fallo una vez y acerto a la siguiente. Sin acotar,
    una sola desobediencia dispara una alarma falsa."""

    def test_distingue_fallo_duro_de_blando(self):
        texto = (REPO / "scripts" / "vps" / "canary-inference.sh").read_text(encoding="utf-8")
        assert "DURO" in texto and "BLANDO" in texto

    def test_reintenta_exactamente_una_vez(self):
        texto = (REPO / "scripts" / "vps" / "canary-inference.sh").read_text(encoding="utf-8")
        assert "while [ $INTENTO -lt 2 ]" in texto, "el reintento debe estar acotado a 2 intentos"
        assert "INTENTO=$(( INTENTO + 1 ))" in texto

    def test_el_fallo_duro_no_se_reintenta(self):
        texto = (REPO / "scripts" / "vps" / "canary-inference.sh").read_text(encoding="utf-8")
        cuerpo = texto[texto.index("while [ $INTENTO"):texto.index("END=$(date")]
        # timeout y exit!=0 rompen el bucle; solo el blando continua.
        assert cuerpo.count("break") >= 3

    def test_registra_cuantos_intentos_hizo(self):
        texto = (REPO / "scripts" / "vps" / "canary-inference.sh").read_text(encoding="utf-8")
        assert "intentos" in texto
