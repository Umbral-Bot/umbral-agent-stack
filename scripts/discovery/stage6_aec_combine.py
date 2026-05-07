"""Stage 6 — Combinación AEC (stub LLM).

> **STUB.** Implementación pospuesta a fase LLM (próximo PR).

Contrato I/O documentado abajo y en
`openclaw/workspace-agent-overrides/rick-linkedin-writer/INPUTS.md` / `OUTPUTS.md`.

Input (esperado por main() cuando se implemente):
    --top-n-report PATH    JSON producido por Stage 5 (`reports/stage5-*.json`).
    --top-k INT            Cuántos top-K usar como pool.
    --report-dir PATH      default reports/.

Input shape (Stage 5 output relevante):
    {
      "items": [
        { "rank": 1, "url_canonica": "...", "ranking_score": 0.74,
          "ranking_reason": {...}, "titulo": "...", "referente_nombre": "...",
          "canal": "youtube", "publicado_en": "..." }
      ]
    }

Output shape (cuando se implemente, ver OUTPUTS.md):
    {
      "stage": "stage6_aec_combine",
      "version": "v1-llm",
      "decision": "single | combined",
      "primary": { "url_canonica": "...", "ranking_score": ... },
      "partner": {                          # presente solo si decision == "combined"
        "url_canonica": "...",
        "bridge_type": "mecanismo | problema | consecuencia_operativa | contraste",
        "bridge_justification": "1-2 frases."
      },
      "transformation_path": "(si single) cómo aterrizar el item solo en voz David"
    }

Schema validation futura: validar que `bridge_type` ∈ enum cerrado y
`bridge_justification` no esté vacía cuando `decision == "combined"`.

Disciplina (de Criterio 2):
- Si la referencia ya es AEC, mantener single salvo que el partner agregue
  contexto/tensión/operacionalización clara.
- Si el puente se siente forzado, NO combinar — transformar el ítem solo.
- Nunca combinar dos referencias sólo para parecer más investigado.
"""

from __future__ import annotations

import argparse
import sys


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--top-n-report", type=str, required=False)
    parser.add_argument("--top-k", type=int, default=10)
    parser.add_argument("--report-dir", type=str, default="reports")
    parser.parse_args(argv)
    raise NotImplementedError("Fase LLM, próximo PR")


if __name__ == "__main__":
    sys.exit(main())
