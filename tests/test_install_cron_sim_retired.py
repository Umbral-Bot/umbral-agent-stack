"""SIM salió del instalador de cron y no debe volver (Q8, 2026-08-14).

El retiro a mano no era durable: el crontab vivo ya no tenía SIM desde
2026-07-19, pero `install-cron.sh` seguía declarando las líneas y las
re-agregaba en cada re-run. Estos tests leen el instalador como TEXTO y fallan
si alguien reintroduce las declaraciones o se lleva puesto el filtro de strip.

No ejecutan el instalador ni tocan el crontab: son de lectura.

Ver docs/operations/sim-cron-retired-2026-08-14.md
"""

from __future__ import annotations

import re
import subprocess
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
INSTALLER = REPO / "scripts" / "vps" / "install-cron.sh"

# Los dos wrappers que el instalador instalaba y ahora strippea.
SIM_CRON_SCRIPTS = ("sim-report-cron.sh", "sim-to-make-cron.sh")

# Los tres wrappers que se conservan como histórico (sim-daily nunca estuvo en
# el instalador, pero lleva la misma nota para que nadie lo reenganche).
SIM_WRAPPERS = ("sim-report-cron.sh", "sim-to-make-cron.sh", "sim-daily-cron.sh")


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

    def test_installer_never_adds_sim_to_crontab(self):
        """Ninguna línea que mencione un wrapper SIM puede escribir al crontab.

        Es el guard que importa: prohibir la variable no alcanza si alguien
        vuelve a instalar la línea inline.
        """
        for ln in self.text.splitlines():
            for script in SIM_CRON_SCRIPTS:
                if script in ln and "crontab -" in ln:
                    self.assertIn(
                        "grep -vF", ln,
                        f"esta línea manda {script} al crontab en vez de sacarlo: {ln.strip()}",
                    )

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


if __name__ == "__main__":
    unittest.main()
