"""Forma del sobre del worker: client.task_result.worker_payload.

Estos casos venían de tests/test_e2e_validation.py (T12). Al subir el helper a
client/ suben con él, porque son del CONTRATO, no del script que lo estrenó.
Los de test_e2e_validation.py quedan igual: allá prueban que las tres funciones
del e2e dependen del unwrap, que es otra cosa.
"""

from __future__ import annotations

import unittest

from client.task_result import WORKER_ENVELOPE_MARKERS, worker_payload


def status_envelope(payload) -> dict:
    """Lo que devuelve GET /task/<id>/status: el sobre del worker adentro de result."""
    return {
        "task_id": "e2e-1234",
        "status": "done",
        "task": "llm.generate",
        "team": "lab",
        "result": {
            "ok": True,
            "task_id": "e2e-1234",
            "task": "llm.generate",
            "team": "lab",
            "trace_id": "trace-1234",
            "result": payload,
        },
        "error": None,
    }


def run_envelope(payload) -> dict:
    """Lo que devuelve POST /run (y WorkerClient.run): un solo nivel de result."""
    return {"ok": True, "task_id": "e2e-1234", "task": "llm.generate", "result": payload}


class TestWorkerPayload(unittest.TestCase):

    def test_status_envelope_yields_inner_payload(self):
        payload = worker_payload(status_envelope({"model": "anthropic/claude-sonnet-4-6", "report": "x" * 19459}))
        self.assertEqual(payload.get("model"), "anthropic/claude-sonnet-4-6")
        self.assertEqual(len(payload.get("report", "")), 19459)
        self.assertNotIn("trace_id", payload)

    def test_run_envelope_is_pass_through(self):
        """POST /run ya viene con un solo nivel: no debe haber segundo unwrap."""
        self.assertEqual(
            worker_payload(run_envelope({"text": "hola", "model": "m", "provider": "openclaw_proxy"})),
            {"text": "hola", "model": "m", "provider": "openclaw_proxy"},
        )

    def test_handler_payload_with_its_own_result_is_not_unwrapped(self):
        """granola devuelve {followup_type, result:{...}}: un unwrap laxo se come ese nivel."""
        granola = {"followup_type": "reminder", "result": {"task_id": "n-1", "due_date": "2026-08-20"}}
        self.assertEqual(worker_payload(run_envelope(granola)), granola)
        self.assertEqual(worker_payload(status_envelope(granola)), granola)

    def test_envelope_with_non_dict_inner_never_leaks_the_envelope(self):
        """El sobre se reconoce por los marcadores, no por el tipo del inner."""
        for inner in (["a", "b"], "texto", 42, None):
            payload = worker_payload(status_envelope(inner))
            self.assertEqual(payload, {}, f"inner={inner!r} filtró el sobre")
            self.assertNotIn("trace_id", payload)

    def test_missing_or_non_dict_result_is_empty_dict(self):
        self.assertEqual(worker_payload({"status": "failed", "result": None}), {})
        self.assertEqual(worker_payload({"status": "failed"}), {})
        self.assertEqual(worker_payload({"result": "texto plano"}), {})

    def test_non_mapping_response_is_empty_dict(self):
        """Los callers del dispatcher pasan lo que vuelva de wc.run(), sin garantías."""
        for bad in (None, [], "texto", 7):
            self.assertEqual(worker_payload(bad), {})

    def test_markers_are_the_three_the_worker_always_sets(self):
        """Si alguien recorta los marcadores, el unwrap se vuelve laxo."""
        self.assertEqual(WORKER_ENVELOPE_MARKERS, ("ok", "task_id", "task"))

    def test_every_marker_is_load_bearing(self):
        """Faltando cualquiera de los tres, ya no es el sobre y no se desenvuelve."""
        payload = {"model": "m"}
        for missing in WORKER_ENVELOPE_MARKERS:
            envelope = {k: v for k, v in status_envelope(payload)["result"].items() if k != missing}
            self.assertEqual(
                worker_payload({"status": "done", "result": envelope}),
                envelope,
                f"sin '{missing}' se desenvolvió igual: el criterio no está mirando ese marcador",
            )


if __name__ == "__main__":
    unittest.main()
