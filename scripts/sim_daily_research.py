#!/usr/bin/env python3
"""
SIM Daily Research — Encola tareas de research automático.

Se ejecuta desde cron (3x/día). Cada ejecución:
1. Define keywords de investigación (rotando por día/hora).
2. Encola tareas research.web para cada keyword.
3. Encola una tarea llm.generate para resumir/analizar resultados.

Requiere: REDIS_URL y al menos un backend operativo de discovery:
- TAVILY_API_KEY (primario)
- o GOOGLE_API_KEY / GOOGLE_API_KEY_NANO para fallback Gemini grounded search
"""

import os
import sys
import uuid
import logging
from datetime import datetime, timezone

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import redis
from dispatcher.queue import TaskQueue

logging.basicConfig(level=logging.INFO, format="%(asctime)s [SIM] %(message)s")
logger = logging.getLogger("sim_daily")

KEYWORD_POOLS = {
    "marketing": [
        "embudo ventas servicios profesionales 2026",
        "estrategia captación clientes arquitectura",
        "marketing digital firmas ingeniería",
        "lead generation B2B servicios técnicos",
        "propuesta valor consultoría BIM",
    ],
    "advisory": [
        "tendencias BIM 2026 Latinoamérica",
        "adopción BIM Colombia regulación",
        "digitalización construcción tendencias",
        "consultoría BIM mercado potencial",
        "inteligencia artificial construcción",
    ],
    "improvement": [
        "automatización flujos trabajo IA agentes",
        "orquestación agentes inteligentes mejores prácticas",
        "SaaS herramientas gestión agentes AI",
        "n8n make automatización workflows IA",
        "observabilidad sistemas distribuidos métricas",
    ],
}


def get_todays_keywords(max_per_pool: int = 2) -> list[dict]:
    """Selecciona keywords rotando por día."""
    now = datetime.now(timezone.utc)
    day_idx = now.timetuple().tm_yday
    hour_slot = now.hour // 8

    tasks = []
    for team, pool in KEYWORD_POOLS.items():
        offset = (day_idx + hour_slot) % len(pool)
        selected = []
        for i in range(max_per_pool):
            idx = (offset + i) % len(pool)
            selected.append(pool[idx])
        for kw in selected:
            tasks.append({"team": team, "keyword": kw})
    return tasks


def main():
    redis_url = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
    r = redis.from_url(redis_url, decode_responses=True)
    tq = TaskQueue(r)

    keywords = get_todays_keywords(max_per_pool=2)
    logger.info("SIM run: %d research tasks to enqueue", len(keywords))

    enqueued = []
    for item in keywords:
        tid = str(uuid.uuid4())
        envelope = {
            "schema_version": "0.1",
            "task_id": tid,
            "team": item["team"],
            "task_type": "research",
            "task": "research.web",
            "input": {
                "query": item["keyword"],
                "count": 5,
                "search_depth": "basic",
            },
        }
        tq.enqueue(envelope)
        enqueued.append(tid)
        logger.info("Enqueued research.web [%s] query='%s' id=%s", item["team"], item["keyword"], tid)

    summary_tid = str(uuid.uuid4())
    summary_envelope = {
        "schema_version": "0.1",
        "task_id": summary_tid,
        "team": "system",
        "task_type": "writing",
        "task": "llm.generate",
        "input": {
            "prompt": (
                "Eres un analista de mercado. Resume las tendencias clave "
                "encontradas hoy en la investigación de mercado para una "
                "consultoría BIM en Latinoamérica. Incluye: oportunidades, "
                "amenazas, y recomendaciones accionables. Responde en español."
            ),
            "system": "Eres Rick, el meta-orquestador de Umbral BIM.",
            "max_tokens": 512,
        },
    }
    tq.enqueue(summary_envelope)
    logger.info("Enqueued llm.generate summary id=%s", summary_tid)

    logger.info("SIM run complete: %d research + 1 summary = %d total", len(enqueued), len(enqueued) + 1)


if __name__ == "__main__":
    main()
