"""Fase 6 monitor fuera, F8a congelado (PKG-MACRO-P5-Q9-T1, 2026-08-21).

El monitor dedicado (`scripts/monitor_supervisor_observability.py`) no tenía
cron ni toque desde 2026-04-20 — fase 6 nunca ancló. F8a tenía evidencia live
histórica sin re-corrida ni smoke recurrente que la justifique. Este test
lee el árbol como texto y falla si el monitor reaparece, si el instalador
de cron vuelve a mencionarlo, o si el doc de F8a pierde el banner CONGELADO.

No ejecuta nada: es de lectura.

Ver docs/operations/q9-fase6-f8a-acotado-2026-08-21.md
"""

from __future__ import annotations

import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
MONITOR_SCRIPT = REPO / "scripts" / "monitor_supervisor_observability.py"
INSTALLER = REPO / "scripts" / "vps" / "install-cron.sh"
F8A_DOC = REPO / "docs" / "copilot-cli-f8a-real-execution-path.md"


class TestFase6MonitorRetired(unittest.TestCase):

    def test_monitor_script_is_gone(self):
        self.assertFalse(
            MONITOR_SCRIPT.exists(),
            f"{MONITOR_SCRIPT} reapareció: el monitor dedicado de fase 6 "
            f"está retirado desde 2026-08-21 (Q9) — la observability viva "
            f"es la integrada en dispatcher/router.py",
        )

    def test_installer_never_mentions_the_monitor(self):
        text = INSTALLER.read_text(encoding="utf-8")
        self.assertNotIn(
            "monitor_supervisor", text,
            "monitor_supervisor reapareció en install-cron.sh: el monitor "
            "dedicado de fase 6 nunca tuvo cron y no debe volver a tenerlo",
        )


class TestF8aFrozen(unittest.TestCase):

    def test_f8a_doc_still_has_frozen_banner(self):
        text = F8A_DOC.read_text(encoding="utf-8")
        self.assertIn(
            "CONGELADO 2026-08-21 [PKG-MACRO-P5-Q9-T1]", text,
            f"{F8A_DOC} perdió el banner CONGELADO: F8a está congelado sin "
            f"smoke recurrente desde 2026-08-21 (Q9), reactivar requiere GO "
            f"explícito de David. (Match exacto a propósito: un simple "
            f"assertIn('CONGELADO', ...) seguiría en verde si alguien "
            f"reactiva y escribe algo como 'ya no está CONGELADO'.)",
        )


if __name__ == "__main__":
    unittest.main()
