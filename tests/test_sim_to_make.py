"""scripts/sim_to_make.py — extracción del payload y guard de reporte vacío.

El bug que estos tests fijan: el script encola un composite, poolea
GET /task/<id>/status y leía `result["result"]` como si fuera el payload del
handler. Sobre un status ese nivel es el SOBRE del worker, así que `report`
salía '' — y el script mandaba ese '' al webhook de Make.com devolviendo exit 0.
No fallaba nada: mentía en silencio.

Ningún test de acá toca la red: se mockean enqueue/poll/send.
"""

from __future__ import annotations

import contextlib
import unittest
from unittest.mock import MagicMock, patch

import scripts.sim_to_make as sim
from client.task_result import worker_payload
from dispatcher.service import COMPOSITE_TASK_TIMEOUT_S
from tests.conftest import naive_unwrap, worker_status_envelope as status_envelope

REPORT = "x" * 19459
SOURCES = [{"url": f"https://e.test/{i}", "title": f"s{i}"} for i in range(15)]

# El payload real de composite.research_report, medido en T11 (acta §15).
COMPOSITE_PAYLOAD = {
    "report": REPORT,
    "sources": SOURCES,
    "queries": ["proptech 2026", "BIM"],
    "execution_time_s": 206.6,
    "stats": {"total_sources": 15, "sources_sent_to_model": 15},
}


class TestUsesTheSharedHelper(unittest.TestCase):

    def test_sim_does_not_keep_its_own_copy_of_the_unwrap(self):
        """El punto del pack: un helper, no un cuarto copy-paste."""
        self.assertIs(sim.worker_payload, worker_payload)

    def test_the_old_read_would_have_returned_an_empty_report(self):
        """Documenta el bug, anclado al helper real y no sólo a un fixture.

        El mismo status: por el helper rinde 19.459 chars; leído al nivel viejo
        rinde '' y lo que aparece ahí es el sobre del worker.
        """
        wrapped = status_envelope(COMPOSITE_PAYLOAD)
        self.assertEqual(len(worker_payload(wrapped).get("report", "")), 19459)

        old = naive_unwrap(wrapped)
        self.assertEqual(old.get("report", ""), "")
        self.assertIn("trace_id", old)


class TestPollingWindow(unittest.TestCase):

    def test_default_timeout_covers_the_dispatcher_window(self):
        """La ventana del cliente tiene que cubrir la del DISPATCHER, no el wall.

        Se compara contra COMPOSITE_TASK_TIMEOUT_S y no contra el literal 340:
        si mañana el dispatcher ensancha su ventana, un assert sobre el número
        seguiría verde con sim_to_make ya rindiéndose antes de tiempo. Es la
        lección de T10 — el invariante tiene que mirar las dos magnitudes.
        """
        self.assertGreater(sim.DEFAULT_TIMEOUT, COMPOSITE_TASK_TIMEOUT_S)


class TestMainGuards(unittest.TestCase):
    """main() no debe llamar a Make.com si tras el unwrap no hay reporte."""

    def _run_main(self, poll_result, argv, env=None, extra_patches=()):
        env = {"MAKE_WEBHOOK_SIM_URL": "https://hook.invalid/x", **(env or {})}
        sent = MagicMock(return_value={"ok": True, "task_id": "t", "task": "make.post_webhook",
                                       "result": {"ok": True, "status_code": 200}})
        # ExitStack y no un for/start suelto: si un patcher falla al arrancar,
        # los ya activos se deshacen igual en vez de contaminar la suite entera.
        with contextlib.ExitStack() as stack:
            for ctx in (
                patch.object(sim, "WorkerClient", MagicMock()),
                patch.object(sim, "enqueue_research", MagicMock(return_value="task-abc")),
                patch.object(sim, "poll_task_status", MagicMock(return_value=poll_result)),
                patch.object(sim, "send_to_make", sent),
                patch.dict("os.environ", env, clear=False),
                patch("sys.argv", ["sim_to_make.py", *argv]),
                *extra_patches,
            ):
                stack.enter_context(ctx)
            return sim.main(), sent

    def test_happy_path_sends_the_real_report(self):
        code, sent = self._run_main(status_envelope(COMPOSITE_PAYLOAD), [])
        self.assertEqual(code, 0)
        sent.assert_called_once()
        payload = sent.call_args[0][2]
        self.assertEqual(len(payload["report"]), 19459)
        self.assertEqual(payload["sources_count"], 15)

    def test_empty_report_does_not_call_make_and_exits_nonzero(self):
        empty = dict(COMPOSITE_PAYLOAD, report="", sources=[])
        code, sent = self._run_main(status_envelope(empty), [])
        self.assertNotEqual(code, 0)
        sent.assert_not_called()

    def test_empty_report_in_dry_run_also_exits_nonzero(self):
        """Dry-run tampoco puede fingir éxito: imprimir 0 chars y devolver 0 era el bug."""
        empty = dict(COMPOSITE_PAYLOAD, report="", sources=[])
        code, sent = self._run_main(status_envelope(empty), ["--dry-run"])
        self.assertNotEqual(code, 0)
        sent.assert_not_called()

    def test_dry_run_with_a_real_report_succeeds_without_posting(self):
        code, sent = self._run_main(status_envelope(COMPOSITE_PAYLOAD), ["--dry-run"])
        self.assertEqual(code, 0)
        sent.assert_not_called()

    def test_short_timeout_warns_that_it_does_not_cover_the_window(self):
        """Subir el default no alcanza: --timeout sigue pudiendo bajarlo."""
        with self.assertLogs(sim.logger, level="WARNING") as logs:
            code, _ = self._run_main(status_envelope(COMPOSITE_PAYLOAD), ["--timeout", "120"])
        self.assertEqual(code, 0)
        self.assertTrue(
            any("no cubre la ventana del dispatcher" in m for m in logs.output),
            f"no se avisó de la ventana corta: {logs.output}",
        )

    def test_without_the_helper_the_run_fails_instead_of_sending_empty(self):
        """MUTACIÓN: si la extracción vuelve a result.get('result'), no se manda nada.

        Es el punto del pack. Antes ese mismo camino terminaba en un POST a
        Make.com con report='' y exit 0.
        """
        code, sent = self._run_main(
            status_envelope(COMPOSITE_PAYLOAD),
            [],
            extra_patches=[patch.object(sim, "worker_payload", naive_unwrap)],
        )
        self.assertNotEqual(code, 0)
        sent.assert_not_called()


if __name__ == "__main__":
    unittest.main()
