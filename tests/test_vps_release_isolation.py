"""Aislamiento entre el árbol de trabajo y producción.

El cron ejecutaba `~/umbral-agent-stack/scripts/vps/...`, es decir, el árbol de
trabajo. Cualquier edición local entraba en producción en el siguiente tic. El
2026-09-18 a las 15:00 UTC eso hizo que el cron corriera un canario a medio
escribir desde una rama sin integrar y emitiera una alarma falsa (Linear UMB-276).

Estas pruebas fijan el modelo de release: producción ejecuta una copia inmutable
de un commit que ya está en origin/main.
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
DEPLOY = REPO / "scripts" / "vps" / "release-deploy.sh"


def git(*args, cwd):
    return subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True)


@pytest.fixture()
def repo_falso(tmp_path):
    """Un repo con origin, para probar el despliegue sin tocar el real."""
    origen = tmp_path / "origen.git"
    trabajo = tmp_path / "trabajo"
    subprocess.run(["git", "init", "--bare", "-q", str(origen)], check=True)
    subprocess.run(["git", "clone", "-q", str(origen), str(trabajo)], check=True)
    git("config", "user.email", "t@t", cwd=trabajo)
    git("config", "user.name", "t", cwd=trabajo)
    (trabajo / "scripts" / "vps").mkdir(parents=True)
    (trabajo / "scripts" / "vps" / "demo.sh").write_text("echo VERSION-1\n", encoding="utf-8")
    git("add", "-A", cwd=trabajo)
    git("commit", "-qm", "v1", cwd=trabajo)
    git("push", "-q", "origin", "HEAD:main", cwd=trabajo)
    git("fetch", "-q", "origin", cwd=trabajo)
    return trabajo, tmp_path


def desplegar(trabajo, base, *extra):
    env = {
        **os.environ,
        "REPO_DIR": str(trabajo),
        "UMBRAL_RELEASES_DIR": str(base / "releases"),
        "UMBRAL_CURRENT_LINK": str(base / "current"),
        "UMBRAL_OPS_LOG_DIR": str(base / "ops"),
    }
    return subprocess.run(["bash", str(DEPLOY), *extra], capture_output=True, text=True, env=env)


class TestDespliegue:
    def test_crea_el_release_y_el_enlace(self, repo_falso):
        trabajo, base = repo_falso
        r = desplegar(trabajo, base)
        assert r.returncode == 0, r.stdout + r.stderr
        actual = base / "current"
        assert actual.is_symlink()
        assert (actual / "RELEASE_SHA").exists()
        assert (actual / "scripts" / "vps" / "demo.sh").read_text(encoding="utf-8").strip() == "echo VERSION-1"

    def test_el_release_registra_el_commit(self, repo_falso):
        trabajo, base = repo_falso
        desplegar(trabajo, base)
        sha = (base / "current" / "RELEASE_SHA").read_text(encoding="utf-8").strip()
        esperado = git("rev-parse", "HEAD", cwd=trabajo).stdout.strip()
        assert sha == esperado

    def test_el_release_no_lleva_git(self, repo_falso):
        """Sin .git no puede seguir una rama ni quedar sucio."""
        trabajo, base = repo_falso
        desplegar(trabajo, base)
        assert not (base / "current" / ".git").exists()

    def test_registra_el_despliegue_en_la_fuente_canonica(self, repo_falso):
        trabajo, base = repo_falso
        desplegar(trabajo, base)
        ops = (base / "ops" / "ops_log.jsonl").read_text(encoding="utf-8")
        assert '"kind":"release_deploy"' in ops


class TestAislamiento:
    """La prueba que David pidió: un cambio local sin commit no debe afectar al cron."""

    def test_un_cambio_sin_commit_no_llega_a_produccion(self, repo_falso):
        trabajo, base = repo_falso
        desplegar(trabajo, base)
        # Se edita el árbol de trabajo, como haría cualquiera desarrollando.
        (trabajo / "scripts" / "vps" / "demo.sh").write_text("echo VERSION-ROTA\n", encoding="utf-8")
        # Producción sigue ejecutando lo desplegado.
        salida = subprocess.run(
            ["bash", str(base / "current" / "scripts" / "vps" / "demo.sh")],
            capture_output=True, text=True,
        ).stdout
        assert "VERSION-1" in salida
        assert "ROTA" not in salida

    def test_un_commit_local_sin_integrar_tampoco_llega(self, repo_falso):
        trabajo, base = repo_falso
        desplegar(trabajo, base)
        (trabajo / "scripts" / "vps" / "demo.sh").write_text("echo VERSION-RAMA\n", encoding="utf-8")
        git("checkout", "-qb", "rama/experimento", cwd=trabajo)
        git("commit", "-qam", "cambio en rama", cwd=trabajo)
        salida = subprocess.run(
            ["bash", str(base / "current" / "scripts" / "vps" / "demo.sh")],
            capture_output=True, text=True,
        ).stdout
        assert "VERSION-1" in salida

    def test_no_se_despliega_algo_que_no_este_en_origin_main(self, repo_falso):
        trabajo, base = repo_falso
        (trabajo / "scripts" / "vps" / "demo.sh").write_text("echo NO-INTEGRADO\n", encoding="utf-8")
        git("checkout", "-qb", "rama/no-integrada", cwd=trabajo)
        git("commit", "-qam", "sin integrar", cwd=trabajo)
        r = desplegar(trabajo, base, "--ref", "HEAD")
        assert r.returncode == 2
        assert "no es ancestro de origin/main" in r.stdout

    def test_el_release_es_de_solo_lectura(self, repo_falso):
        trabajo, base = repo_falso
        desplegar(trabajo, base)
        destino = base / "current" / "scripts" / "vps" / "demo.sh"
        with pytest.raises(PermissionError):
            destino.write_text("echo INTRUSO\n", encoding="utf-8")


class TestRollback:
    def test_vuelve_al_release_anterior(self, repo_falso):
        trabajo, base = repo_falso
        desplegar(trabajo, base)
        v1 = (base / "current" / "RELEASE_SHA").read_text(encoding="utf-8").strip()
        (trabajo / "scripts" / "vps" / "demo.sh").write_text("echo VERSION-2\n", encoding="utf-8")
        git("commit", "-qam", "v2", cwd=trabajo)
        git("push", "-q", "origin", "HEAD:main", cwd=trabajo)
        git("fetch", "-q", "origin", cwd=trabajo)
        desplegar(trabajo, base)
        assert "VERSION-2" in (base / "current" / "scripts" / "vps" / "demo.sh").read_text(encoding="utf-8")
        r = desplegar(trabajo, base, "--rollback")
        assert r.returncode == 0, r.stdout + r.stderr
        assert (base / "current" / "RELEASE_SHA").read_text(encoding="utf-8").strip() == v1
        assert "VERSION-1" in (base / "current" / "scripts" / "vps" / "demo.sh").read_text(encoding="utf-8")

    def test_status_informa_el_release_activo(self, repo_falso):
        trabajo, base = repo_falso
        desplegar(trabajo, base)
        r = desplegar(trabajo, base, "--status")
        assert r.returncode == 0
        assert "release activo" in r.stdout


class TestPuertaEnsureMain:
    def test_dentro_de_un_release_la_puerta_pasa(self, tmp_path):
        """El release es por definición un commit ya integrado: no hay rama que
        comprobar ni árbol que pueda estar sucio."""
        rel = tmp_path / "rel"
        rel.mkdir()
        (rel / "RELEASE_SHA").write_text("abc123def456", encoding="utf-8")
        r = subprocess.run(
            ["bash", str(REPO / "scripts" / "vps" / "ensure-main-for-run.sh")],
            capture_output=True, text=True,
            env={**os.environ, "REPO": str(rel), "ENSURE_MAIN_LOG": str(tmp_path / "log")},
        )
        assert r.returncode == 0
        assert "release abc123def456" in (tmp_path / "log").read_text(encoding="utf-8")


class TestRegistroDelCommit:
    def test_la_libreria_expone_el_commit_en_ejecucion(self):
        texto = (REPO / "scripts" / "vps" / "lib" / "umbral_alerting.sh").read_text(encoding="utf-8")
        assert "umbral_release_sha" in texto
        assert "arbol-de-trabajo:" in texto, "debe distinguir release de árbol de trabajo"

    def test_los_monitores_registran_el_commit(self):
        for f in ("health-check.sh", "canary-inference.sh"):
            texto = (REPO / "scripts" / "vps" / f).read_text(encoding="utf-8")
            assert "umbral_release_sha" in texto, f"{f} no registra el commit en ejecución"
