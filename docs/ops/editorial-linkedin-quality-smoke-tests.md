# Editorial LinkedIn Quality Smoke Tests

> Status: repo-side manual smoke suite. These checks do not store or replay David's approved benchmark text. They express synthetic pass/fail criteria for the current editorial system.

## Purpose

Use these smoke tests when adjusting LinkedIn drafting, communication direction, or QA rules for thesis-led AEC/BIM posts.

They are designed to catch:

- abstract openings;
- abrupt entry into `modelo BIM`;
- consultant-sounding phrasing;
- overlong mini-article behavior;
- inflated claims;
- repeated nucleus words.

## Fail Cases

### FAIL-001 — Abstract opening

```text
En AEC/BIM, la capacidad tecnologica ya existe. El problema real es el criterio operativo.
```

Expected result:

- communication director rewrites or blocks;
- QA cannot return `voice: pass`;
- reason mentions abstract opening and consultant phrasing.

### FAIL-002 — `modelo BIM` too early

```text
Cuando un modelo BIM no esta listo, la automatizacion no sirve.
```

Expected result:

- system asks for process framing first;
- preferred rewrite direction starts from revision, deliverable, observation, or decision before the object.

### FAIL-003 — Mini-article drift

```text
Antes de automatizar hay que definir el proceso. Luego hay que pensar en adopcion de mercado, auditoria, gobernanza, supervision, ROI, madurez digital y cultura organizacional...
```

Expected result:

- director or QA flags more than one central idea;
- draft is compressed to a single thesis-led LinkedIn post.

### FAIL-004 — Inflated market claim

```text
Cada vez mas empresas usan sistemas algoritmicos para gestionar trabajo y por eso todos los equipos BIM deberian hacer lo mismo.
```

Expected result:

- QA downgrades for unsupported generalization;
- safer direction uses conditional language or removes the market claim.

### FAIL-005 — Repeated nucleus word

```text
Si el criterio no existe, el criterio no ordena el criterio del equipo y ese criterio se vuelve el cuello de botella.
```

Expected result:

- director flags repetition and artificial cadence;
- revised direction rotates vocabulary toward review, acceptance, closure, or decision.

## Pass Cases

### PASS-001 — Thesis first, process first

```text
Antes de automatizar una revision, conviene resolver algo mas basico: que se acepta, que vuelve y que puede avanzar.
```

Expected result:

- acceptable opening for LinkedIn;
- process framing arrives before technical examples.

### PASS-002 — Concrete operational landing

```text
Eso se nota cuando una observacion no queda bien cerrada, un entregable pasa de etapa sin acuerdo claro o un reporte informa pero no ayuda a decidir.
```

Expected result:

- operational examples are recognized as AEC/BIM-relevant;
- no need for broader abstraction.

### PASS-003 — Controlled BIM mention

```text
Despues, si hace falta, eso baja a escenas concretas: cuando un modelo BIM esta listo para revision, cuando una observacion obliga a rehacer o cuando un entregable ya se puede aceptar.
```

Expected result:

- `modelo BIM` appears after context;
- technical object supports the thesis instead of replacing it.

### PASS-004 — Modest claim discipline

```text
Si esas reglas no estan claras, la automatizacion puede terminar acelerando un proceso mal definido.
```

Expected result:

- QA accepts as editorial inference;
- no extra source required beyond the original thesis set.

## Operator Checklist

When a new variant is proposed, verify manually:

1. The opening frames the problem as process, review, deliverable, observation, or decision.
2. `modelo BIM` does not appear as the first reflex unless the piece is explicitly technical.
3. There is one main idea only.
4. The wording avoids `criterio operativo`, `capacidad tecnologica`, `umbrales`, and similar formulas unless justified.
5. The post feels like LinkedIn, not a mini-essay.
6. Claims remain modest and defensible.

## Related

- `evals/editorial/benchmark-umbral-voice-v1.yaml`
- `docs/ops/editorial-decision-brief-and-benchmark-2026-06-05.md`
