"""Worker ya no registra tournament/PIT tasks (PKG-MACRO-P5-PIT-T1, 2026-08-20).

Los docs de PIT quedaron HISTÓRICO desde #594 y no hay cron que dispare
torneos, pero el worker seguía registrando tournament.run,
github.orchestrate_tournament, tournament_lane.* y pit.* en TASK_HANDLERS —
nada los disparaba solo, pero el código seguía siendo invocable a mano.

Este test lee TASK_HANDLERS y falla si cualquiera de esas claves reaparece,
y confirma que los módulos que las respaldaban ya no existen.

No ejecuta ningún handler: es de lectura sobre el registro.

Ver docs/operations/pit-worker-tasks-retired-2026-08-20.md
"""

from __future__ import annotations

import importlib
import unittest

from worker.tasks import TASK_HANDLERS

RETIRED_EXACT_KEYS = ("tournament.run", "github.orchestrate_tournament")
RETIRED_PREFIXES = ("tournament_lane.", "pit.")

RETIRED_MODULES = (
    "worker.tasks.tournament",
    "worker.tasks.github_tournament",
    "worker.tasks.tournament_lane_github",
    "worker.tasks.pit_runner",
)


class TestPitTournamentTasksRetired(unittest.TestCase):

    def test_no_retired_exact_keys_in_registry(self):
        offenders = [k for k in RETIRED_EXACT_KEYS if k in TASK_HANDLERS]
        self.assertEqual(
            offenders, [],
            f"tasks retiradas reaparecieron en TASK_HANDLERS: {offenders} "
            f"(PKG-MACRO-P5-PIT-T1 las sacó — ver "
            f"docs/operations/pit-worker-tasks-retired-2026-08-20.md)",
        )

    def test_no_retired_prefixed_keys_in_registry(self):
        offenders = [
            k for k in TASK_HANDLERS
            if any(k.startswith(prefix) for prefix in RETIRED_PREFIXES)
        ]
        self.assertEqual(
            offenders, [],
            f"claves con prefijo retirado (tournament_lane., pit.) reaparecieron: {offenders}",
        )

    def test_retired_modules_are_gone(self):
        for mod in RETIRED_MODULES:
            with self.assertRaises(
                ModuleNotFoundError,
                msg=f"{mod} sigue existiendo — el retiro de PIT-T1 se revirtió",
            ):
                importlib.import_module(mod)


if __name__ == "__main__":
    unittest.main()
