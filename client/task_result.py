"""Forma canónica del resultado de una tarea del Worker.

Dos endpoints entregan el payload del handler a distinta profundidad:

    POST /run              -> {ok, task_id, task, team, trace_id, result:{...}}
    GET  /task/<id>/status -> {status, result:{ok, task_id, task, ..., result:{...}}}

El worker arma ese sobre en ``worker/app.py:729-735`` y ``WorkerClient.run()``
lo devuelve tal cual. El dispatcher, al completar la tarea, guarda el sobre
ENTERO dentro del envelope de Redis (``dispatcher/queue.py:243``:
``envelope["result"] = result``), así que sobre un status el payload del
handler queda **un nivel más adentro**.

Leerlo al nivel equivocado no explota: devuelve ``None`` y el caller reporta
``''`` o ``'?'``. Así estuvo cinco meses (PKG-MACRO-P5-L2-T11/T12, acta §15 y
§16): el e2e daba FAIL de aserción con el runtime sano, y ``sim_to_make``
mandaba un reporte vacío a un webhook externo devolviendo exit 0.

Este módulo existe para que ese gesto viva UNA vez. Sólo lee: no toca el
contrato de Redis ni el wrap de ``queue.py``.
"""

from __future__ import annotations

from collections.abc import Mapping as _MappingABC
from typing import Any, Dict, Mapping

# Las tres llaves que el worker pone SIEMPRE en el sobre y que ningún payload
# de handler trae juntas. Verificado recorriendo con AST todos los `return
# {...}` de worker/tasks/ (T12): ninguno devuelve las tres.
WORKER_ENVELOPE_MARKERS = ("ok", "task_id", "task")


def worker_payload(response: Mapping[str, Any]) -> Dict[str, Any]:
    """Devuelve el payload del handler, venga o no envuelto en el sobre del worker.

    Sirve tanto para una respuesta de ``POST /run`` como para una de
    ``GET /task/<id>/status``: sobre la primera es pass-through, sobre la
    segunda pela el nivel de más. Siempre devuelve un dict, para que el caller
    pueda hacer ``.get()`` sin chequear.

    El criterio es ESTRICTO a propósito. Hay handlers cuyo payload propio ya
    trae un ``result`` anidado — ``granola`` devuelve
    ``{followup_type, result:{task_id, ...}}`` — y un criterio laxo ("¿tiene un
    result dict adentro?") se comería un nivel de más justo ahí. Por eso se
    exige el juego completo de marcadores.

    Y "¿es el sobre?" se decide SOLO por los marcadores, nunca por el tipo del
    payload de adentro: si se exigiera que el inner fuera dict, un handler que
    devuelve una lista haría que el caller recibiera el sobre entero — o sea el
    bug de T11 de vuelta, en silencio y justo en el caso que este helper cubre.
    """
    # collections.abc y no typing.Mapping: typing.Mapping es un alias deprecado
    # desde 3.9 y su isinstance depende de que siga delegando __instancecheck__.
    if not isinstance(response, _MappingABC):
        return {}
    result = response.get("result")
    if not isinstance(result, dict):
        return {}
    if "result" in result and all(k in result for k in WORKER_ENVELOPE_MARKERS):
        inner = result["result"]
        return inner if isinstance(inner, dict) else {}
    return result
