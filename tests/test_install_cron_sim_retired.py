"""SIM salió del instalador de cron y no debe volver (Q8, 2026-08-14).

El retiro a mano no era durable: el crontab vivo ya no tenía SIM desde
2026-07-19, pero `install-cron.sh` seguía declarando las líneas y las
re-agregaba en cada re-run. Estos tests leen el instalador como TEXTO y fallan
si alguien reintroduce las declaraciones o se lleva puesto el filtro de strip.

No ejecutan el instalador ni tocan el crontab: son de lectura.

Ver docs/operations/sim-cron-retired-2026-08-14.md
"""

from __future__ import annotations

import os
import re
import subprocess
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
INSTALLER = REPO / "scripts" / "vps" / "install-cron.sh"

# Los tres wrappers SIM. sim-daily nunca estuvo en el instalador — se instalaba
# A MANO (audit 2026-07-17) — y justamente por eso entra al filtro: es el más
# propenso a volver por la puerta de atrás.
SIM_CRON_SCRIPTS = ("sim-report-cron.sh", "sim-to-make-cron.sh", "sim-daily-cron.sh")
SIM_WRAPPERS = SIM_CRON_SCRIPTS


class TestInstallerHasNoSim(unittest.TestCase):

    def setUp(self):
        self.text = INSTALLER.read_text(encoding="utf-8")

    def test_no_sim_line_variables_declared(self):
        """Ni SIM_REPORT_LINE ni SIM_TO_MAKE_LINE vuelven a declararse."""
        for var in ("SIM_REPORT_LINE", "SIM_TO_MAKE_LINE"):
            self.assertNotIn(
                var, self.text,
                f"{var} reapareció en install-cron.sh: SIM está retirado desde 2026-08-14 (Q8)",
            )

    def test_no_echo_of_sim_line_variables(self):
        """Nadie vuelve a inyectar esas variables al crontab con echo."""
        offenders = [
            ln.strip() for ln in self.text.splitlines()
            if re.search(r"echo\s+\"\$SIM_[A-Z_]*LINE\"", ln)
        ]
        self.assertEqual(offenders, [], f"echo de una SIM_*_LINE en el instalador: {offenders}")

    def test_installer_never_pipes_sim_into_crontab(self):
        """Ninguna línea que mencione un wrapper SIM puede ESCRIBIR al crontab.

        Es el guard que importa: prohibir la variable no alcanza si alguien
        vuelve a instalar la línea inline.

        El matcher es `| crontab -` y no `crontab -` a propósito: lo segundo
        también matchea `crontab -l`, que es de lectura, y prohibiría de rebote
        un chequeo legítimo del estilo `crontab -l | grep -qF sim-report`.
        """
        offenders = [
            ln.strip() for ln in self.text.splitlines()
            if "| crontab -" in ln and any(s in ln for s in SIM_CRON_SCRIPTS) and "grep -vF" not in ln
        ]
        self.assertEqual(offenders, [], f"estas líneas mandan SIM al crontab en vez de sacarlo: {offenders}")

    def test_read_only_checks_are_not_flagged(self):
        """El guard de arriba no debe morder código de solo lectura.

        Sin esto, apretar el matcher no tiene red y el próximo que lo relaje a
        `crontab -` reintroduce el falso positivo sin enterarse.
        """
        read_only = 'if crontab -l 2>/dev/null | grep -qF "sim-report-cron.sh"; then'
        self.assertNotIn("| crontab -", read_only)

    def test_strip_filter_present_for_both_sim_scripts(self):
        """El instalador SANEA: un re-run saca las líneas SIM que hubiera."""
        for script in SIM_CRON_SCRIPTS:
            self.assertIn(
                f'grep -vF "{script}"', self.text,
                f"falta el filtro de strip para {script}: sin él, un crontab con esa "
                f"línea se la queda para siempre",
            )

    def test_strip_filter_actually_writes_the_filtered_crontab(self):
        """El filtro no puede quedar en una variable que nadie usa."""
        self.assertRegex(
            self.text,
            r'printf .*"\$sim_after".*\|.*crontab -',
            "el crontab filtrado no se escribe: el strip sería decorativo",
        )

    def test_installer_is_valid_bash(self):
        r = subprocess.run(["bash", "-n", str(INSTALLER)], capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr)


class TestWrappersKeptButMarked(unittest.TestCase):
    """Los wrappers NO se borran — se conservan y se marcan."""

    def test_wrappers_still_exist(self):
        for w in SIM_WRAPPERS:
            self.assertTrue((REPO / "scripts" / "vps" / w).is_file(), f"{w} fue borrado")

    def test_wrappers_are_marked_as_retired(self):
        for w in SIM_WRAPPERS:
            text = (REPO / "scripts" / "vps" / w).read_text(encoding="utf-8")
            self.assertIn(
                "RETIRADO del instalador", text,
                f"{w} no dice que está retirado: alguien lo puede reenganchar sin enterarse",
            )

    def test_sim_to_make_python_is_untouched(self):
        """El retiro es del CRON, no del código: sim_to_make.py sigue usable a mano."""
        self.assertTrue((REPO / "scripts" / "sim_to_make.py").is_file())


class TestStripBehaviour(unittest.TestCase):
    """Ejercita el bloque DE VERDAD, con un `crontab` falso en PATH.

    Los tests de arriba leen el instalador como texto: cazan que alguien borre
    el filtro, pero no que lo rompa por dentro. Un `grep -v` sin `-F`, o sacar
    el `|| true` (que bajo `set -euo pipefail` aborta el instalador cuando el
    crontab consiste SOLO en líneas SIM), los dejaría a todos en verde.

    Nunca se toca el crontab real: el falso lee y escribe un archivo temporal.
    """

    SIM_LINES = [
        "30 8,14,20 * * * bash /home/x/scripts/vps/sim-report-cron.sh >> /tmp/sim_report.log 2>&1",
        "0 9,15,21 * * * bash /home/x/scripts/vps/sim-to-make-cron.sh >> /tmp/sim_to_make.log 2>&1",
        "0 8,14,20 * * * bash /home/x/scripts/vps/sim-daily-cron.sh",
    ]
    KEEP_LINES = [
        "*/5 * * * * bash /home/x/scripts/vps/supervisor.sh",
        "0 6 * * * bash /home/x/scripts/vps/e2e-validation-cron.sh",
    ]

    def setUp(self):
        # El bloque de strip, extraído del instalador real.
        text = INSTALLER.read_text(encoding="utf-8")
        start = text.index("# --- Retiro SIM")
        end = text.index("\n# --- Daily digest", start)
        self.block = text[start:end]
        self.assertIn("crontab -", self.block, "no se pudo extraer el bloque de strip")

        self.tmp = tempfile.mkdtemp()
        binp = Path(self.tmp) / "bin"
        binp.mkdir()
        (binp / "crontab").write_text(
            "#!/usr/bin/env bash\n"
            'if [ "${1:-}" = "-l" ]; then cat "$FAKE_CRONTAB"; exit 0; fi\n'
            'if [ "${1:-}" = "-" ]; then cat > "$FAKE_CRONTAB"; exit 0; fi\n'
            "exit 0\n"
        )
        (binp / "crontab").chmod(0o755)
        self.binp = binp

    def _run(self, crontab_lines):
        ct = Path(self.tmp) / "ct"
        ct.write_text("\n".join(crontab_lines) + ("\n" if crontab_lines else ""))
        script = Path(self.tmp) / "strip.sh"
        script.write_text("set -euo pipefail\n" + self.block)
        env = {**os.environ, "PATH": f"{self.binp}:{os.environ['PATH']}", "FAKE_CRONTAB": str(ct)}
        r = subprocess.run(["bash", str(script)], capture_output=True, text=True, env=env)
        return r, [ln for ln in ct.read_text().splitlines() if ln.strip()]

    def test_removes_every_sim_line_and_keeps_the_rest(self):
        r, after = self._run(self.KEEP_LINES[:1] + self.SIM_LINES + self.KEEP_LINES[1:])
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(after, self.KEEP_LINES, "no quedó exactamente lo que no era SIM")
        for name in SIM_CRON_SCRIPTS:
            self.assertNotIn(name, "\n".join(after))

    def test_is_idempotent_on_a_clean_crontab(self):
        r, after = self._run(self.KEEP_LINES)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(after, self.KEEP_LINES, "tocó un crontab que ya estaba limpio")

    def test_survives_an_empty_crontab(self):
        r, after = self._run([])
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(after, [])

    def test_survives_a_crontab_that_is_only_sim(self):
        """El caso que rompe si alguien saca el `|| true`.

        grep -v sin ninguna línea de salida devuelve 1, y bajo `set -euo
        pipefail` eso aborta el instalador entero — con seis crons posteriores
        sin instalar.
        """
        r, after = self._run(self.SIM_LINES)
        self.assertEqual(r.returncode, 0, f"el bloque abortó: {r.stderr}")
        self.assertEqual(after, [])

    def tearDown(self):
        subprocess.run(["rm", "-rf", self.tmp], check=False)


if __name__ == "__main__":
    unittest.main()
