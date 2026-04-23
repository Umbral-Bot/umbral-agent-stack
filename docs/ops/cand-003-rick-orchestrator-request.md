Actúa como rick-orchestrator simulando explícitamente rick-editorial.

Objetivo: Generar el payload completo para CAND-003, una candidata editorial source-driven con tesis "Criterio antes que automatización".

Contexto:
- CAND-002 ya existe con tesis: "La barrera principal para capturar valor de IA en AEC no parece ser la falta de herramientas, sino la falta de preparación organizacional." CAND-003 NO debe repetir esa tesis, sino avanzar hacia: ¿qué significa preparación organizacional concretamente? Respuesta: criterio operativo explícito.
- Política de atribución vigente: referentes son discovery sources internos, no autoridades públicas. No citar personas por nombre en copy público.
- Premisa requerida: afirmación breve, fuerte, clara.
- Ortografía española correcta desde el inicio (tildes, ñ, puntuación).

Reglas:
- No escribir a Notion.
- No publicar.
- No marcar gates humanos.
- No activar Rick.
- No inventar fuentes — usar solo las proporcionadas.
- Separar evidencia (datos verificables), inferencia (conclusiones lógicas), hipótesis (supuestos no verificados).
- Devolver solo payload YAML completo.
- No citar personas por nombre en copy público (aplicar política de atribución desde el inicio).

Audiencia:
- Profesionales AEC/BIM: coordinadores, BIM managers, directores de transformación digital, consultores de operaciones en construcción.
- Etapa: awareness (o consideration si la pieza es más prescriptiva — decidir y justificar).

Fuentes disponibles (ya investigadas y clasificadas):

1. **The Batch #340 — Standardized AI Audits** [CITABLE: analysis_source]
   - "AI is becoming ubiquitous, yet no standards exist for auditing its safety and security"
   - AVERI framework: 8 audit principles (independence, clarity, rigor, information access, continuous monitoring)
   - 3 risk categories: technology, organizational, assurance levels
   - 4 Assurance Levels (AAL-1 a AAL-4)
   - "Auditors should analyze model vendors, and not just the models"
   - "Different developers view risks in different ways, and measures of risk aren't standardized"

2. **The Batch #343 — Frontier Agent Management** [CITABLE: analysis_source]
   - OpenAI Frontier: agent identity, permissions, guardrails
   - Companies control which employees access which agents
   - Evaluation: ground-truth data or model outputs
   - "Human oversight remains implicit in the design rather than formally outlined"

3. **Marc Vidal — "El algoritmo como jefe supremo"** [DISCOVERY SOURCE — no citar en copy público]
   - Datos primarios citados por Vidal:
     - OECD (2025): 79% de empresas europeas usan herramientas algorítmicas de gestión
     - McKinsey: hasta 30% de horas laborales en EE.UU. podrían automatizarse para 2030
     - WEF (2025): 92M empleos desplazados, 170M nuevos antes de 2030
     - Regulación IA UE (Feb 2025): prohibido reconocimiento emocional en trabajo
   - Señal: gestión algorítmica desplegada sin criterios de gobernanza

4. **OECD (2025) — Algorithmic Management Report** [CITABLE: primary_source]
   - 79% de empresas europeas usan herramientas algorítmicas
   - Adopción masiva sin gobernanza proporcional

5. **McKinsey Global Institute** [CITABLE: primary_source]
   - Hasta 30% de horas laborales automatizables para 2030
   - La escala de automatización exige criterios explícitos

6. **AVERI — AI Verification and Research Institute** [CITABLE: primary_source]
   - Primer framework propuesto para criterios de auditoría de IA
   - El framework existe precisamente porque no había criterios antes

7. **Aelion.io / Iván Gómez** [CONTEXTUAL REFERENCE — no citar en copy público]
   - "La tecnología solo tiene sentido si genera valor desde el primer día"
   - En AEC, "valor desde el primer día" requiere criterios para definir qué es "valor" operativamente

Tesis CAND-003:
"En AEC, automatizar sin criterio operativo explícito no acelera: amplifica la ambigüedad. Antes de escalar con IA, hay que definir qué constituye una revisión válida, qué dispara una escalación y qué hace que la coordinación sea suficiente."

Fórmula de transformación sugerida: pattern_synthesis (combinar señales de auditoría IA + gobernanza de agentes + gestión algorítmica en tesis AEC sobre criterio operativo).

Devuelve el payload YAML completo siguiendo la estructura de CAND-002 (ver template en docs/ops/rick-editorial-candidate-payload-template.md), incluyendo:
- publication_id, title, estado, canal, tipo_de_contenido, etapa_audiencia, prioridad
- premisa (breve, fuerte, clara)
- claim_principal (con tipo: inferencia_con_fuentes)
- angulo_editorial
- source_set (sources_analyzed con URLs, periods, publications_found, access_status)
- extraction_matrix (evidencia, inferencia, hipótesis con source attribution)
- decantation (discarded, conserved, combined)
- transformation_formula (nombre, tipo, input_signals, steps, aec_connection, assumptions, risks)
- editorial_decision (selected angle, alternatives_considered, why_selected)
- copies: copy_linkedin (base draft, ortografía correcta, sin nombres de personas), copy_x (base draft)
- visual brief
- comentarios_revision
- gates (all false)
- post_publication (all empty)
- system (all false/empty)
- acceptance_checklist
- source_classification (ya incluida arriba, repetir en payload)
