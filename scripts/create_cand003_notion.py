#!/usr/bin/env python3
"""
Create CAND-003 page in Notion Publicaciones DB.

Reads the payload from docs/ops/cand-003-payload.md and creates
the page with all properties and body blocks.

Requires: NOTION_API_KEY env var.
DB: e6817ec4698a4f0fbbc8fedcf4e52472
"""

import json
import os
import sys

# Allow importing from project root
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from worker import notion_client  # noqa: E402

DB_ID = "e6817ec4698a4f0fbbc8fedcf4e52472"
PUB_ID = "CAND-003"


# ---------------------------------------------------------------------------
# Helpers for Notion block building
# ---------------------------------------------------------------------------


def heading2(text: str) -> dict:
    return {
        "object": "block",
        "type": "heading_2",
        "heading_2": {"rich_text": [{"type": "text", "text": {"content": text}}]},
    }


def heading3(text: str) -> dict:
    return {
        "object": "block",
        "type": "heading_3",
        "heading_3": {"rich_text": [{"type": "text", "text": {"content": text}}]},
    }


def paragraph(text: str) -> dict:
    # Notion limits rich_text content to 2000 chars per element.
    chunks = _chunk_text(text, 2000)
    return {
        "object": "block",
        "type": "paragraph",
        "paragraph": {
            "rich_text": [
                {"type": "text", "text": {"content": c}} for c in chunks
            ]
        },
    }


def bold_paragraph(label: str, value: str) -> dict:
    return {
        "object": "block",
        "type": "paragraph",
        "paragraph": {
            "rich_text": [
                {
                    "type": "text",
                    "text": {"content": label},
                    "annotations": {"bold": True},
                },
                {"type": "text", "text": {"content": f" {value}"}},
            ]
        },
    }


def bulleted(text: str) -> dict:
    chunks = _chunk_text(text, 2000)
    return {
        "object": "block",
        "type": "bulleted_list_item",
        "bulleted_list_item": {
            "rich_text": [
                {"type": "text", "text": {"content": c}} for c in chunks
            ]
        },
    }


def callout(text: str, emoji: str = "📌") -> dict:
    chunks = _chunk_text(text, 2000)
    return {
        "object": "block",
        "type": "callout",
        "callout": {
            "icon": {"type": "emoji", "emoji": emoji},
            "rich_text": [
                {"type": "text", "text": {"content": c}} for c in chunks
            ],
        },
    }


def divider() -> dict:
    return {"object": "block", "type": "divider", "divider": {}}


def _chunk_text(text: str, max_len: int = 2000) -> list[str]:
    if len(text) <= max_len:
        return [text]
    chunks = []
    while text:
        chunks.append(text[:max_len])
        text = text[max_len:]
    return chunks


def _rt(text: str) -> dict:
    """Build a rich_text property value."""
    return {"rich_text": [{"type": "text", "text": {"content": text}}]}


# ---------------------------------------------------------------------------
# Step 1 — Dedup
# ---------------------------------------------------------------------------


def dedup_check() -> str | None:
    """Return page_id if CAND-003 already exists, else None."""
    pages = notion_client.query_database(
        DB_ID,
        filter={
            "property": "publication_id",
            "rich_text": {"equals": PUB_ID},
        },
    )
    if pages:
        pid = pages[0]["id"]
        url = pages[0].get("url", "")
        print(f"⚠️  CAND-003 already exists: {pid}\n   {url}")
        return pid
    print("✅ No existing CAND-003 found — safe to create.")
    return None


# ---------------------------------------------------------------------------
# Step 2 — Build properties
# ---------------------------------------------------------------------------

TITLE = "CAND-003 — Criterio antes que automatización: en AEC, la preparación real no empieza por la herramienta."

PREMISA = (
    "Antes de automatizar, definí qué es 'suficientemente bueno'. "
    "Sin criterios operativos explícitos — qué revisar, cuándo escalar, "
    "con qué umbrales medir — la automatización amplifica el desorden "
    "en vez de resolverlo."
)

COPY_LINKEDIN = (
    "Hay una pregunta que falta en casi toda conversación sobre automatización en AEC:\n\n"
    "¿Cuál es tu criterio?\n\n"
    "No qué herramienta usás. No qué modelo probaste. Sino: ¿qué definiste como "
    "suficientemente bueno? ¿Cuándo se escala? ¿Quién revisa qué?\n\n"
    "En infraestructura, el patrón se ve claro. Una ciudad prometió una olimpíada "
    "sin autos, pero cuando los criterios reales no sostuvieron la ambición, el plan "
    "retrocedió. Un rascacielos se construyó sin criterios de integración urbana — "
    "el rechazo duró 50 años y la reparación cuesta €300M.\n\n"
    "En IA, el patrón se repite. Las plataformas de gestión de agentes más avanzadas "
    "no funcionan 'en general': definen permisos, umbrales, evaluación y escalamiento "
    "antes de ejecutar. Las arquitecturas que no definen criterios producen outputs "
    "incorrectos. Y cuando una tecnología impresionante no tiene criterios operativos "
    "sostenibles, se cancela.\n\n"
    "En AEC pasa algo similar. Se adoptan herramientas con lógica aspiracional: mucha "
    "expectativa, poco criterio definido. Cuando no entregan valor, se culpa al software.\n\n"
    "Pero el problema suele estar antes:\n"
    "— no había un umbral de calidad explícito,\n"
    "— no había criterio de revisión definido,\n"
    "— no había proceso de escalamiento claro.\n\n"
    "La automatización amplifica lo que hay. Si hay criterio, amplifica orden. Si no, "
    "amplifica caos.\n\n"
    "Antes de sumar más tecnología, quizá convenga responder una pregunta más básica:\n"
    "¿tenés los criterios operativos para que funcione?"
)

COPY_X = (
    "En AEC, la pregunta correcta antes de automatizar no es qué herramienta usar.\n\n"
    "Es qué criterio tenés definido.\n\n"
    "¿Qué es suficientemente bueno? ¿Quién revisa? ¿Cuándo se escala?\n\n"
    "Sin eso definido, la automatización amplifica desorden, no lo resuelve."
)

CLAIM_PRINCIPAL = (
    "En AEC, la preparación real para automatizar no empieza por la herramienta. "
    "Empieza por definir criterios operativos explícitos: qué es suficientemente bueno, "
    "quién revisa, cuándo se escala. Sin eso, la automatización amplifica desorden."
)

ANGULO_EDITORIAL = (
    "La capacidad tecnológica ya existe. Pero en AEC, la automatización no entrega "
    "valor cuando falta la infraestructura invisible: criterios operativos explícitos."
)

RESUMEN_FUENTE = (
    "Fuentes: The B1M (LA Olympics, Tour Montparnasse), The Batch #343 (Frontier, "
    "Context Hub), #347 (Claude Code, Sora). Discovery: Marc Vidal → OECD/Solow. "
    "Contextual: Aelion.io."
)

COMENTARIOS_REVISION = (
    "Segunda candidata source-driven. Tesis prescriptiva: criterio antes que "
    "automatización. Diferenciada de CAND-002 (diagnóstico) — CAND-003 prescribe "
    "la respuesta: definí criterios operativos explícitos."
)

NOTAS = (
    "Fuentes: The B1M (LA Olympics, Tour Montparnasse), The Batch (#343 Frontier, "
    "#347 Claude Code/Sora). Discovery: Vidal → OECD/Solow. Contextual: Aelion.io. "
    "QA: pass. Attribution: pass. Voice: pass. Flujo canónico de 9 pasos."
)


def build_properties() -> dict:
    return {
        "Título": {"title": [{"type": "text", "text": {"content": TITLE}}]},
        "publication_id": _rt(PUB_ID),
        "Canal": {"select": {"name": "linkedin"}},
        "Tipo de contenido": {"select": {"name": "linkedin_post"}},
        "Etapa audiencia": {"select": {"name": "awareness"}},
        "Estado": {"status": {"name": "Borrador"}},
        "Prioridad": {"select": {"name": "media"}},
        "Premisa": _rt(PREMISA),
        "Copy LinkedIn": _rt(COPY_LINKEDIN),
        "Copy X": _rt(COPY_X),
        "Copy Blog": _rt(""),
        "Copy Newsletter": _rt(""),
        "Claim principal": _rt(CLAIM_PRINCIPAL),
        "Ángulo editorial": _rt(ANGULO_EDITORIAL),
        "Resumen fuente": _rt(RESUMEN_FUENTE),
        "Comentarios revisión": _rt(COMENTARIOS_REVISION),
        "Notas": _rt(NOTAS),
        # Gates — all false
        "aprobado_contenido": {"checkbox": False},
        "autorizar_publicacion": {"checkbox": False},
        "gate_invalidado": {"checkbox": False},
        "Creado por sistema": {"checkbox": False},
        "visual_hitl_required": {"checkbox": True},
        # Source tracking
        "Fuente primaria": {"url": "https://www.deeplearning.ai/the-batch"},
        "Fuente referente": {"url": "https://www.theb1m.com"},
        # Trace
        "trace_id": _rt("CAND-003-source-driven-editorial-candidate"),
        "Proyecto": _rt("Sistema Editorial Rick"),
        # Visual
        "Visual brief": _rt(
            "Visual editorial sobrio con una secuencia central: a la izquierda, "
            "ícono de criterio/regla (un check o una lupa sobre un umbral); a la "
            "derecha, ícono de automatización (engranaje o flujo). El criterio "
            "antecede a la automatización. Estética limpia, técnica, apta para "
            "LinkedIn, sin interfaces internas ni referencias a sistemas propios."
        ),
    }


# ---------------------------------------------------------------------------
# Step 3 — Build body blocks
# ---------------------------------------------------------------------------


def build_body_blocks() -> list[dict]:
    blocks: list[dict] = []

    # ---- Batch 1: Editorial content ----
    blocks.append(heading2("Estado del borrador"))
    blocks.append(
        callout(
            "Borrador — No publicar. Gates cerrados. Pendiente revisión humana.",
            "🔒",
        )
    )
    blocks.append(divider())

    # Premisa in body (required: visible in property AND body)
    blocks.append(heading2("Premisa"))
    blocks.append(callout(PREMISA, "💡"))
    blocks.append(divider())

    # LinkedIn copy
    blocks.append(heading2("Propuesta principal — LinkedIn"))
    for para in COPY_LINKEDIN.split("\n\n"):
        blocks.append(paragraph(para))
    blocks.append(divider())

    # X copy
    blocks.append(heading2("Variante X"))
    for para in COPY_X.split("\n\n"):
        blocks.append(paragraph(para))
    blocks.append(divider())

    # Visual brief
    blocks.append(heading2("Brief visual"))
    blocks.append(
        paragraph(
            "Visual editorial sobrio con una secuencia central: a la izquierda, "
            "ícono de criterio/regla (un check o una lupa sobre un umbral); a la "
            "derecha, ícono de automatización (engranaje o flujo). El criterio "
            "antecede a la automatización. Estética limpia, técnica, apta para "
            "LinkedIn, sin interfaces internas ni referencias a sistemas propios."
        )
    )
    blocks.append(
        callout("visual_hitl_required = true — Requiere revisión humana.", "🎨")
    )
    blocks.append(divider())

    # ---- Batch 2: Sources & extraction ----
    blocks.append(heading2("Fuentes analizadas"))

    # The B1M
    blocks.append(heading3("The B1M [CITABLE — original_article]"))
    blocks.append(
        bulleted(
            "Will Los Angeles Be Ready For The Next Olympics? (2026-04-13) — "
            "Plan 'Twenty-eight by 28': 28 proyectos de transporte, criterios "
            "aspiracionales que no sostuvieron la ambición. 'Not all of them were realistic.'"
        )
    )
    blocks.append(
        bulleted(
            "The Plan to Save Paris' Most Hated Building (2026-02-11) — "
            "Tour Montparnasse: construido 1973 sin criterios de integración "
            "urbana → rechazo 50 años → Francia prohibió rascacielos en París "
            "central → €300M renovación."
        )
    )

    # The Batch
    blocks.append(heading3("DeepLearning.AI / The Batch [CITABLE — analysis_source]"))
    blocks.append(
        bulleted(
            "#343: Management for Agents (2026-03-06) — OpenAI Frontier: "
            "permisos, guardrails y evaluación por agente. Context Hub: contexto "
            "operativo explícito previene alucinación."
        )
    )
    blocks.append(
        bulleted(
            "#347: Inside Claude Code / OpenAI Exits Sora (2026-04-03) — "
            "Claude Code: 40+ tools con permission gates, 3 niveles de memoria. "
            "Sora: ~$1M/día de pérdida → cancelación. Capacidad sin criterios "
            "operativos = fracaso."
        )
    )

    # Marc Vidal
    blocks.append(heading3("Marc Vidal [DISCOVERY — solo trazabilidad interna]"))
    blocks.append(
        bulleted(
            "El algoritmo como jefe supremo (2026-03-23) → Fuente primaria: "
            "OECD Algorithmic Management 2025 (79% sin criterios de gobernanza)."
        )
    )
    blocks.append(
        bulleted(
            "La paradoja de la productividad (2026-03-09) → Fuente primaria: "
            "Robert Solow (1987), paradoja de la productividad."
        )
    )

    # Aelion
    blocks.append(heading3("Aelion.io [CONTEXTUAL — solo trazabilidad interna]"))
    blocks.append(
        bulleted(
            "Manifesto: 'La tecnología solo tiene sentido si genera valor desde "
            "el primer día.' Representa mentalidad sector AEC (ROI-first = "
            "criteria-first)."
        )
    )
    blocks.append(divider())

    # Extraction matrix
    blocks.append(heading2("Matriz de extracción"))

    blocks.append(heading3("Evidencia (6)"))
    evidencia = [
        (
            "B1M — LA Olympics",
            "Plan 'Twenty-eight by 28': criterios aspiracionales que retrocedieron bajo presión.",
        ),
        (
            "B1M — Tour Montparnasse",
            "Construido sin criterios de integración → 50 años de rechazo → €300M de reparación.",
        ),
        (
            "Batch #343 — Frontier",
            "Gestión de agentes con identidad, permisos, guardrails y métricas de evaluación.",
        ),
        (
            "Batch #343 — Context Hub",
            "Contexto operativo explícito previene alucinación y outputs incorrectos.",
        ),
        (
            "Batch #347 — Claude Code",
            "40+ herramientas, cada una con módulos de permisos. Arquitectura embebe criterios.",
        ),
        (
            "Batch #347 — Sora",
            "~$1M/día de pérdida. Capacidad técnica sin criterios sostenibles = cancelación.",
        ),
    ]
    for label, desc in evidencia:
        blocks.append(bold_paragraph(f"[E] {label}:", desc))

    blocks.append(heading3("Inferencia (3)"))
    inferencia = [
        (
            "Criterio = infraestructura invisible",
            "La diferencia entre promesa aspiracional e implementación funcional "
            "es la existencia de criterios operativos definidos antes de ejecutar.",
        ),
        (
            "Capacidad sin criterio es frágil",
            "Las arquitecturas exitosas embeben criterios en su diseño. Las que "
            "no los tienen, fracasan incluso con capacidad técnica superior.",
        ),
        (
            "Paradoja de Solow persiste",
            "Se suma tecnología sin cambiar los criterios operativos del sistema. "
            "Cambiar criterios es la intervención que falta.",
        ),
    ]
    for label, desc in inferencia:
        blocks.append(bold_paragraph(f"[I] {label}:", desc))

    blocks.append(heading3("Hipótesis (1)"))
    blocks.append(
        bold_paragraph(
            "[H] Criterio primero captura más valor:",
            "Los equipos AEC que definan criterios operativos explícitos antes "
            "de automatizar capturarán valor desproporcionadamente mayor que los "
            "que automaticen primero y definan criterios después.",
        )
    )
    blocks.append(divider())

    # Decantation
    blocks.append(heading2("Decantación"))
    blocks.append(heading3("Descartado"))
    descartado = [
        "Detallar arquitectura interna de Claude Code como tutorial técnico — desvía hacia ingeniería de software.",
        "Analizar fracaso de Sora como caso de negocio — no es el nivel correcto para awareness AEC.",
        "Repetir el diagnóstico de brecha de CAND-002 — CAND-003 debe prescribir, no rediagnosticar.",
        "Listar criterios específicos que un equipo AEC debería definir — convertiría awareness en checklist prescriptivo.",
    ]
    for d in descartado:
        blocks.append(bulleted(d))

    blocks.append(heading3("Conservado"))
    conservado = [
        "La ausencia de criterios explícitos diferencia ambición fallida de implementación funcional.",
        "Los sistemas de IA más avanzados definen criterios antes de operar.",
        "El costo de no definir criterios se acumula con el tiempo (Tour Montparnasse, LA Olympics).",
    ]
    for c in conservado:
        blocks.append(bulleted(c))

    blocks.append(heading3("Combinado"))
    combinado = [
        "Infraestructura (LA Olympics + Montparnasse + OECD): la ausencia de criterios "
        "es la raíz de implementaciones que fallan o generan deuda permanente.",
        "IA (Frontier + Claude Code + Sora): la capacidad técnica sin criterios "
        "operativos no produce valor. Si aplica a la tecnología, aplica a la organización.",
    ]
    for c in combinado:
        blocks.append(bulleted(c))
    blocks.append(divider())

    # ---- Batch 3: Formula, attribution, checklist ----
    blocks.append(heading2("Fórmula de transformación"))
    blocks.append(bold_paragraph("Nombre:", "Criterio como infraestructura"))
    blocks.append(bold_paragraph("Tipo:", "pattern_synthesis"))
    blocks.append(
        paragraph(
            "Tomar señales de infraestructura (B1M), gestión de agentes (The Batch) "
            "y gobernanza organizacional (OECD/Solow). Identificar el patrón común: "
            "la variable que determina éxito o fracaso no es la capacidad, sino la "
            "existencia de criterios operativos explícitos. Traducir al lenguaje "
            "operativo AEC: umbrales de calidad, criterios de revisión, escalamiento, "
            "definición de 'suficientemente bueno'."
        )
    )

    blocks.append(heading3("Alternativas consideradas"))
    alternativas = [
        "checklist_prescriptivo — Rechazado: convierte awareness en consultoría.",
        "caso_de_estudio_sora — Rechazado: desvía hacia tech news, pierde conexión AEC.",
        "continuacion_directa_de_cand_002 — Rechazado: riesgo de repetir diagnóstico.",
    ]
    for a in alternativas:
        blocks.append(bulleted(a))
    blocks.append(divider())

    # Attribution policy
    blocks.append(heading2("Política de atribución aplicada"))
    blocks.append(
        paragraph(
            "Aplicada desde el inicio del flujo (no post-hoc). Los referentes "
            "(Marc Vidal, Aelion.io) son fuentes de descubrimiento editorial, "
            "no fuentes de autoridad pública. El copy público cita organizaciones "
            "(The B1M, DeepLearning.AI), no personas. Ningún referente aparece "
            "mencionado por nombre en el contenido público."
        )
    )
    blocks.append(
        callout(
            "Clasificación: The B1M = original_article [CITABLE]. "
            "The Batch = analysis_source [CITABLE]. "
            "Marc Vidal = discovery_source [SOLO INTERNO]. "
            "Aelion.io = contextual_reference [SOLO INTERNO].",
            "📋",
        )
    )
    blocks.append(divider())

    # Risks
    blocks.append(heading2("Riesgos y supuestos"))
    riesgos = [
        "Que la pieza se lea como anti-automatización (propone secuencia, no rechazo).",
        "Que la tesis resulte obvia para equipos maduros que ya operan con criterios.",
        "Que la relación entre infraestructura urbana y gestión de agentes IA parezca forzada.",
        "La hipótesis sobre BIM es inferencial y no verificada empíricamente para AEC.",
    ]
    for r in riesgos:
        blocks.append(bulleted(r))

    supuestos = [
        "La mayoría de equipos AEC relevantes no tienen criterios operativos explícitos para automatización.",
        "La audiencia reconoce la frustración entre adoptar herramientas y no ver resultados.",
        "Una pieza awareness funciona mejor si provoca una pregunta concreta que si prescribe un checklist.",
    ]
    blocks.append(heading3("Supuestos"))
    for s in supuestos:
        blocks.append(bulleted(s))
    blocks.append(divider())

    # Checklist David
    blocks.append(heading2("Checklist David"))
    checklist_items = [
        "¿La premisa es clara y fuerte? ¿Diferenciada de CAND-002?",
        "¿El copy LinkedIn es publicable? ¿Voz correcta?",
        "¿La variante X funciona como pieza independiente?",
        "¿Las fuentes están correctamente clasificadas?",
        "¿La política de atribución está aplicada?",
        "¿Los riesgos son aceptables?",
        "¿El brief visual es claro?",
        "¿Aprobado para avanzar a aprobado_contenido?",
    ]
    for item in checklist_items:
        blocks.append(
            {
                "object": "block",
                "type": "to_do",
                "to_do": {
                    "rich_text": [
                        {"type": "text", "text": {"content": item}}
                    ],
                    "checked": False,
                },
            }
        )
    blocks.append(divider())

    # No hacer todavía
    blocks.append(heading2("No hacer todavía"))
    no_hacer = [
        "No publicar en ningún canal.",
        "No activar Rick runtime.",
        "No marcar aprobado_contenido ni autorizar_publicacion.",
        "No calcular content_hash ni idempotency_key.",
        "No generar visual final (solo brief).",
        "No crear variantes hijas hasta aprobar esta pieza.",
    ]
    for n in no_hacer:
        blocks.append(
            callout(n, "🚫")
        )

    return blocks


# ---------------------------------------------------------------------------
# Step 4 — Verify page
# ---------------------------------------------------------------------------


def verify_page(page_id: str) -> dict:
    """Read back page and verify critical fields."""
    import httpx

    resp = httpx.get(
        f"https://api.notion.com/v1/pages/{page_id}",
        headers={
            "Authorization": f"Bearer {os.environ['NOTION_API_KEY']}",
            "Notion-Version": "2022-06-28",
        },
        timeout=30,
    )
    if resp.status_code >= 400:
        print(f"❌ Failed to read page: {resp.status_code} {resp.text[:300]}")
        return {}
    data = resp.json()
    props = data.get("properties", {})

    def _get_status(p):
        s = props.get(p, {}).get("status", {})
        return s.get("name", "") if s else ""

    def _get_checkbox(p):
        return props.get(p, {}).get("checkbox", None)

    def _get_rt(p):
        rt = props.get(p, {}).get("rich_text", [])
        return "".join(item.get("plain_text", "") for item in rt) if rt else ""

    def _get_url(p):
        return props.get(p, {}).get("url", "")

    results = {
        "page_id": data.get("id", ""),
        "url": data.get("url", ""),
        "Estado": _get_status("Estado"),
        "aprobado_contenido": _get_checkbox("aprobado_contenido"),
        "autorizar_publicacion": _get_checkbox("autorizar_publicacion"),
        "gate_invalidado": _get_checkbox("gate_invalidado"),
        "publication_id": _get_rt("publication_id"),
        "Premisa_in_property": _get_rt("Premisa"),
        "published_url": _get_url("published_url"),
        "publication_url": _get_url("publication_url"),
        "platform_post_id": _get_rt("platform_post_id"),
    }
    return results


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main():
    if not os.environ.get("NOTION_API_KEY"):
        print("❌ NOTION_API_KEY not set. Export it first.")
        sys.exit(1)

    # 1. Dedup check
    print("=" * 60)
    print("STEP 1: Deduplication check")
    print("=" * 60)
    existing = dedup_check()
    if existing:
        print(f"\n⚠️  CAND-003 already exists (page_id={existing}).")
        print("   Skipping creation. Use the existing page.")
        # Still run verification
        print("\n" + "=" * 60)
        print("STEP 4: Verification of existing page")
        print("=" * 60)
        result = verify_page(existing)
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return

    # 2. Build properties
    print("\n" + "=" * 60)
    print("STEP 2: Creating page with properties")
    print("=" * 60)
    props = build_properties()
    body_blocks = build_body_blocks()
    print(f"   Properties: {len(props)} fields")
    print(f"   Body blocks: {len(body_blocks)} blocks")

    # 3. Create page (first 100 blocks as children, rest appended)
    result = notion_client.create_database_page(
        DB_ID,
        properties=props,
        children=body_blocks,
        icon="📐",
    )
    page_id = result["page_id"]
    page_url = result["url"]
    print(f"\n✅ Page created!")
    print(f"   Page ID: {page_id}")
    print(f"   URL: {page_url}")

    # 4. Verify
    print("\n" + "=" * 60)
    print("STEP 3: Post-write verification")
    print("=" * 60)
    verification = verify_page(page_id)
    print(json.dumps(verification, indent=2, ensure_ascii=False))

    # Check critical invariants
    ok = True
    if verification.get("Estado") != "Borrador":
        print("❌ Estado is NOT Borrador!")
        ok = False
    if verification.get("aprobado_contenido") is not False:
        print("❌ aprobado_contenido is NOT false!")
        ok = False
    if verification.get("autorizar_publicacion") is not False:
        print("❌ autorizar_publicacion is NOT false!")
        ok = False
    if verification.get("gate_invalidado") is not False:
        print("❌ gate_invalidado is NOT false!")
        ok = False
    if verification.get("published_url"):
        print("❌ published_url is NOT empty!")
        ok = False
    if verification.get("publication_url"):
        print("❌ publication_url is NOT empty!")
        ok = False
    if not verification.get("Premisa_in_property"):
        print("❌ Premisa NOT in property!")
        ok = False
    else:
        print("✅ Premisa present in property.")
    if verification.get("publication_id") != PUB_ID:
        print(f"❌ publication_id mismatch: {verification.get('publication_id')}")
        ok = False

    if ok:
        print("\n✅ All post-write checks passed.")
    else:
        print("\n❌ Some checks failed — review above.")

    # Output summary for evidence file
    print("\n" + "=" * 60)
    print("SUMMARY FOR EVIDENCE")
    print("=" * 60)
    print(f"page_id: {page_id}")
    print(f"url: {page_url}")
    print(f"blocks: {len(body_blocks)}")
    print(f"Estado: {verification.get('Estado')}")
    print(f"aprobado_contenido: {verification.get('aprobado_contenido')}")
    print(f"autorizar_publicacion: {verification.get('autorizar_publicacion')}")
    print(f"gate_invalidado: {verification.get('gate_invalidado')}")
    print(f"Premisa in property: {'yes' if verification.get('Premisa_in_property') else 'no'}")
    print(f"Premisa in body: yes (callout block in body)")


if __name__ == "__main__":
    main()
