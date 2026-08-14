"""scripts/sim_to_make.py — extracción del payload y guard de reporte vacío.

El bug que estos tests fijan: el script encola un composite, poolea
GET /task/<id>/status y leía `result["result"]` como si fuera el payload del
handler. Sobre un status ese nivel es el SOBRE del worker, así que `report`
salía '' — y el script mandaba ese '' al webhook de Make.com devolviendo exit 0.
No fallaba nada: mentía en silencio.

Ningún test de acá toca la red: se mockean enqueue/poll/send.
"""

from __future__ import annotations

import unittest
from unittest.mock import MagicMock, patch

import scripts.sim_to_make as sim
from tests.test_task_result import status_envelope

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


def _naive_extract(status_data):
    """Cómo se leía antes de este pack. Se usa para mutar el helper."""
    return status_data.get("result", {})


class TestPayloadExtraction(unittest.TestCase):
    """El status envuelto estilo T11 tiene que rendir reporte y fuentes reales."""

    def test_wrapped_status_yields_the_real_report_and_sources(self):
        payload = sim.worker_payload(status_envelope(COMPOSITE_PAYLOAD))
        self.assertEqual(len(payload.get("report", "")), 19459)
        self.assertGreater(len(payload.get("sources", [])), 0)
        self.assertEqual(len(payload["sources"]), 15)

    def test_the_old_read_returns_an_empty_report(self):
        """Documenta el bug: al nivel viejo hay un sobre, no el payload."""
        old = _naive_extract(status_envelope(COMPOSITE_PAYLOAD))
        self.assertEqual(old.get("report", ""), "")
        self.assertEqual(old.get("sources", []), [])
        # Y lo que sí hay ahí es el sobre del worker, que es la prueba del desajuste.
        self.assertIn("trace_id", old)


class TestPollingWindow(unittest.TestCase):

    def test_default_timeout_covers_the_dispatcher_window(self):
        """120s se rendían antes de que el payload existiera, con el unwrap sano.

        La ventana del cliente tiene que cubrir la del DISPATCHER (300s), no el
        wall medido (~200s), o un WINDOW que funcionó se reporta como timeout.
        """
        self.assertGreaterEqual(sim.DEFAULT_TIMEOUT, 340)


class TestMainGuards(unittest.TestCase):
    """main() no debe llamar a Make.com si tras el unwrap no hay reporte."""

    def _run_main(self, poll_result, argv, env=None, extra_patches=()):
        env = {"MAKE_WEBHOOK_SIM_URL": "https://hook.invalid/x", **(env or {})}
        sent = MagicMock(return_value={"ok": True, "task_id": "t", "task": "make.post_webhook",
                                       "result": {"ok": True, "status_code": 200}})
        stack = [
            patch.object(sim, "WorkerClient", MagicMock()),
            patch.object(sim, "enqueue_research", MagicMock(return_value="task-abc")),
            patch.object(sim, "poll_task_status", MagicMock(return_value=poll_result)),
            patch.object(sim, "send_to_make", sent),
            patch.dict("os.environ", env, clear=False),
            patch("sys.argv", ["sim_to_make.py", *argv]),
            *extra_patches,
        ]
        for ctx in stack:
            ctx.start()
        try:
            return sim.main(), sent
        finally:
            for ctx in reversed(stack):
                ctx.stop()

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

    def test_without_the_helper_the_run_fails_instead_of_sending_empty(self):
        """MUTACIÓN: si la extracción vuelve a result.get('result'), no se manda nada.

        Es el punto del pack. Antes ese mismo camino terminaba en un POST a
        Make.com con report='' y exit 0.
        """
        code, sent = self._run_main(
            status_envelope(COMPOSITE_PAYLOAD),
            [],
            extra_patches=[patch.object(sim, "worker_payload", _naive_extract)],
        )
        self.assertNotEqual(code, 0)
        sent.assert_not_called()


if __name__ == "__main__":
    unittest.main()
