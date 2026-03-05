#!/usr/bin/env python3
"""
Añade la sección "En pocas palabras" al inicio de cada página de la Bitácora.

Genera un resumen corto (2-4 oraciones) en español no técnico para cada entrada,
y lo inserta como primer bloque visible, sin eliminar el contenido existente.

Uso:
    export NOTION_API_KEY=...
    export NOTION_BITACORA_DB_ID=85f89758684744fb9f14076e7ba0930e
    python scripts/add_resumen_amigable.py [--dry-run] [--limit N] [--page-id UUID]
"""

import argparse
import logging
import os
import re
import sys
import time
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from worker import notion_client
from worker.notion_client import (
    _block_callout,
    _block_divider,
    _block_heading2,
    _block_paragraph,
    prepend_blocks_to_page,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

BITACORA_DB_ID = os.environ.get("NOTION_BITACORA_DB_ID", "85f89758684744fb9f14076e7ba0930e")

# ---------------------------------------------------------------------------
# Mapeo de títulos a resúmenes amigables
# ---------------------------------------------------------------------------

RESUMENES: dict[str, list[str]] = {
    "hackathon base": [
        "Se revisó y puso en marcha todo el sistema desde cero: se detectaron problemas, se corrigieron, y se verificó que cada pieza funcione correctamente.",
        "Es como hacer una revisión general del motor antes de salir a carretera: ahora todo arranca y responde como debe.",
    ],
    "hackathon r1": [
        "Se activaron las primeras automatizaciones reales del sistema: investigación automática de temas de interés, generación de reportes periódicos, y registro de toda la actividad.",
        "Antes el sistema solo existía en papel; ahora trabaja solo, buscando información y generando resúmenes tres veces al día.",
    ],
    "poller inteligente": [
        "Se creó un mecanismo que revisa constantemente si hay nuevos mensajes o solicitudes en el espacio de trabajo, los clasifica automáticamente, y los envía al equipo correcto.",
        "Es como tener una recepcionista digital que lee todos los mensajes entrantes y sabe a quién derivar cada uno.",
    ],
    "r2": [
        "Se mejoró la estabilidad del sistema para que se recupere solo si algo falla, y se añadió la capacidad de recibir solicitudes de trabajo desde fuera.",
        "Ahora el sistema es más robusto: si se cae, se levanta solo, y cualquier herramienta externa puede enviarle tareas.",
    ],
    "r3": [
        "Se implementó la capacidad de responder preguntas de forma inteligente: el asistente ahora busca información en internet, genera una respuesta, y la publica automáticamente.",
        "También se creó un resumen diario automático de toda la actividad, para que el equipo sepa qué pasó cada día sin tener que revisar logs.",
    ],
    "r4": [
        "Se creó un historial completo de tareas ejecutadas (qué se hizo, cuándo, resultado) y se conectó el sistema con herramientas de automatización externas como Make.com.",
        "Esto permite ver todo lo que el asistente ha hecho y conectar su trabajo con otros flujos de la empresa.",
    ],
    "r5": [
        "Se añadieron alertas automáticas cuando algo falla, se crearon flujos de trabajo por equipo, y se implementó la programación de tareas a futuro.",
        "Ahora si algo sale mal, el responsable se entera de inmediato. Además, cada equipo puede tener sus propios procesos automatizados.",
    ],
    "r6": [
        "Se habilitó la capacidad de usar múltiples modelos de inteligencia artificial (no solo uno), eligiendo el más adecuado según la tarea.",
        "Es como tener acceso a varios asesores expertos y poder consultar al que mejor se adapte a cada pregunta, en lugar de depender de uno solo.",
    ],
    "r7": [
        "Se añadió un sistema de monitoreo que registra cada consulta a la inteligencia artificial, y se reforzó la seguridad del sistema con límites de uso y protección contra abusos.",
        "Esto da visibilidad total sobre el uso de IA y protege contra costos inesperados o uso indebido.",
    ],
    "r8": [
        "Se conectó el sistema con herramientas de gestión de proyectos (Linear) y se creó un panel de salud que muestra en tiempo real qué servicios están activos.",
        "El equipo ahora puede ver de un vistazo si todo funciona bien, y las tareas de proyecto se sincronizan automáticamente.",
    ],
    "r9": [
        "Se crearon guías especializadas (skills) para que el asistente sepa usar herramientas específicas como Figma, Notion y otras, con instrucciones paso a paso.",
        "Es como darle al asistente un manual de cada herramienta para que pueda operar con más precisión y autonomía.",
    ],
    "r10": [
        "Se automatizó la creación de nuevas guías de habilidades a partir de documentación existente, y se incorporaron habilidades personales del equipo.",
        "El asistente ahora puede aprender nuevas herramientas leyendo su documentación, y conoce las áreas de expertise de cada persona del equipo.",
    ],
    "r11": [
        "Se añadieron docenas de habilidades especializadas en áreas como diseño BIM, automatización, inteligencia artificial, generación de documentos y marketing de contenidos.",
        "El asistente pasó de ser generalista a tener conocimiento profundo en las áreas clave del negocio: arquitectura, ingeniería, tecnología y comunicación.",
    ],
    "skill": [
        "Se añadieron nuevas capacidades especializadas al asistente, ampliando las áreas en las que puede ayudar al equipo.",
        "Cada nueva habilidad es como agregarle una certificación al asistente: sabe más y puede resolver tareas más complejas.",
    ],
    "bim": [
        "Se añadió conocimiento especializado en herramientas de diseño y construcción como Revit, Dynamo, Rhino y Navisworks.",
        "El asistente ahora entiende el lenguaje y las herramientas que usa el equipo de arquitectura e ingeniería.",
    ],
    "granola": [
        "Se creó un flujo automático que toma las transcripciones de reuniones y las organiza en el espacio de trabajo, generando seguimientos y recordatorios.",
        "Ya no hay que copiar notas manualmente después de cada reunión: el sistema lo hace solo y avisa de los compromisos pendientes.",
    ],
    "r12": [
        "Se integraron servicios de calendario y correo electrónico, se mejoró el flujo de reuniones, y se amplió el catálogo de habilidades técnicas.",
        "El asistente ahora puede agendar reuniones, redactar correos, y tiene conocimiento más profundo en herramientas especializadas.",
    ],
    "calendar": [
        "Se conectó el asistente con Google Calendar y Gmail para que pueda agendar reuniones y redactar borradores de correo automáticamente.",
        "Después de cada reunión, el asistente puede crear los eventos de seguimiento y los correos necesarios sin intervención manual.",
    ],
    "audit": [
        "Se revisó si el sistema tiene suficiente registro y trazabilidad para responder preguntas de gobernanza: qué se hizo, quién lo hizo, y con qué resultado.",
        "Esto es fundamental para rendición de cuentas y para medir si las estrategias de automatización están funcionando.",
    ],
    "r13": [
        "Se reforzaron los mecanismos de auditoría y trazabilidad del sistema, se creó documentación operativa, y se pobló el historial del proyecto.",
        "El equipo ahora tiene un registro completo de la evolución del proyecto y las herramientas para evaluarlo con criterios de gobernanza.",
    ],
    "governance": [
        "Se crearon reportes de métricas de gobernanza y un manual operativo para el equipo que mantiene el sistema.",
        "Cualquier persona nueva en el equipo puede entender cómo funciona todo y dónde buscar si algo falla.",
    ],
    "opslogger": [
        "Se mejoró el registro de actividades del sistema para que cada acción quede documentada con más detalle y se limpie automáticamente.",
        "Es como pasar de un cuaderno desordenado a un libro contable bien organizado y con rotación automática.",
    ],
    "bitacora": [
        "Se creó y pobló un historial visual del proyecto en Notion, documentando cada fase importante desde el inicio.",
        "Ahora cualquier persona puede ver de un vistazo qué se ha construido, cuándo, y quién participó en cada etapa.",
    ],
    "bitácora": [
        "Se creó y pobló un historial visual del proyecto en Notion, documentando cada fase importante desde el inicio.",
        "Ahora cualquier persona puede ver de un vistazo qué se ha construido, cuándo, y quién participó en cada etapa.",
    ],
    "pipeline": [
        "Se creó un flujo automatizado que conecta varias herramientas para que la información pase de una a otra sin intervención manual.",
        "Esto reduce el trabajo repetitivo y asegura que la información esté siempre actualizada en todos los sistemas.",
    ],
    "rrss": [
        "Se diseñó un sistema para capturar contenido de redes sociales, revisarlo con el equipo, y publicarlo en múltiples canales.",
        "El equipo puede gestionar su presencia en redes de forma más organizada, con aprobación humana antes de publicar.",
    ],
}


def _match_resumen(title: str) -> list[str]:
    """Find the best matching non-technical summary for a page title."""
    title_lower = title.lower()
    title_words = set(re.findall(r'[a-záéíóúñü\d]+', title_lower))

    is_round_key = re.compile(r'^r\d+$')
    topic_matches: list[tuple[float, str]] = []
    round_matches: list[tuple[float, str]] = []

    for key, summary in RESUMENES.items():
        keywords = key.split()
        score = 0.0
        is_pure_round = len(keywords) == 1 and is_round_key.match(keywords[0])

        for kw in keywords:
            if is_round_key.match(kw):
                if kw in title_words:
                    score += 1.5
            elif kw in title_words:
                score += 2.0
            elif len(kw) > 3 and kw in title_lower:
                score += 1.0

        if score > 0:
            if is_pure_round:
                round_matches.append((score, key))
            else:
                topic_matches.append((score, key))

    if topic_matches:
        topic_matches.sort(key=lambda x: -x[0])
        return RESUMENES[topic_matches[0][1]]

    if round_matches:
        round_matches.sort(key=lambda x: -x[0])
        return RESUMENES[round_matches[0][1]]

    return _generate_generic_resumen(title)


def _generate_generic_resumen(title: str) -> list[str]:
    """Generate a generic non-technical summary when no match is found."""
    return [
        f"En esta etapa se trabajó en mejoras al sistema de asistencia automatizada del equipo, específicamente en el área de: {title}.",
        "Cada mejora busca que el asistente sea más útil, más confiable y más fácil de usar para todo el equipo.",
    ]


def extract_page_title(page: dict) -> str:
    props = page.get("properties", {})
    for prop_name in ("Name", "Nombre", "Título", "Title", "name", "title"):
        prop = props.get(prop_name)
        if prop and prop.get("type") == "title":
            parts = prop.get("title", [])
            return "".join(p.get("plain_text", "") for p in parts)
    return ""


def build_en_pocas_palabras_blocks(title: str) -> list[dict[str, Any]]:
    """Build the 'En pocas palabras' section as Notion blocks."""
    resumen_lines = _match_resumen(title)

    blocks: list[dict[str, Any]] = []
    blocks.append(_block_heading2("En pocas palabras"))

    for line in resumen_lines:
        blocks.append(_block_callout(line, "💬", "yellow_background"))

    blocks.append(_block_divider())
    return blocks


def process_page(page: dict, dry_run: bool = False) -> bool:
    """Add 'En pocas palabras' section at the top of a page."""
    page_id = page["id"]
    title = extract_page_title(page)

    if not title:
        logger.warning("Página %s sin título, omitiendo", page_id[:8])
        return False

    logger.info("Procesando: %s (%s)", title[:60], page_id[:8])

    new_blocks = build_en_pocas_palabras_blocks(title)
    logger.info("  Generados %d bloques 'En pocas palabras'", len(new_blocks))

    if dry_run:
        for b in new_blocks:
            if b["type"] == "callout":
                text = b["callout"]["rich_text"][0]["text"]["content"]
                logger.info("  [DRY-RUN] %s", text[:80])
        return True

    try:
        result = prepend_blocks_to_page(page_id, new_blocks)
        logger.info(
            "  Prepended %d, preserved %d blocks",
            result["blocks_prepended"],
            result["blocks_preserved"],
        )
        time.sleep(1.0)
        return True
    except Exception as e:
        logger.error("  Error en página %s: %s", page_id[:8], e)
        return False


def main():
    parser = argparse.ArgumentParser(description="Añade 'En pocas palabras' a la Bitácora")
    parser.add_argument("--dry-run", action="store_true", help="No modificar Notion")
    parser.add_argument("--limit", type=int, default=0, help="Limitar páginas")
    parser.add_argument("--page-id", type=str, help="Solo una página")
    args = parser.parse_args()

    if not os.environ.get("NOTION_API_KEY"):
        logger.error("NOTION_API_KEY no está configurada")
        sys.exit(1)

    logger.info("Consultando base de datos Bitácora (%s)...", BITACORA_DB_ID[:8])
    pages = notion_client.query_database(BITACORA_DB_ID)
    logger.info("Páginas encontradas: %d", len(pages))

    if args.page_id:
        clean_id = args.page_id.replace("-", "")
        pages = [p for p in pages if p["id"].replace("-", "") == clean_id]
        if not pages:
            logger.error("Página %s no encontrada", args.page_id)
            sys.exit(1)

    if args.limit:
        pages = pages[:args.limit]

    ok = 0
    errors = 0
    for page in pages:
        try:
            if process_page(page, dry_run=args.dry_run):
                ok += 1
        except Exception as e:
            logger.error("Error en %s: %s", page.get("id", "?")[:8], e)
            errors += 1

    logger.info("=== Resumen ===")
    logger.info("Total: %d | Exitosas: %d | Errores: %d", len(pages), ok, errors)


if __name__ == "__main__":
    main()
