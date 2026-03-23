---
id: "020"
title: "Team Workflow Engine — Flujos por equipo"
assigned_to: github-copilot
status: done
updated_at: "2026-03-22T19:04:21-03:00"
branch: feat/copilot-team-workflows
priority: high
round: 5
---

# Team Workflow Engine

## Problema
Hay 5 equipos definidos en teams.yaml (marketing, advisory, improvement, lab, system)
pero ninguno tiene workflows. Cuando llega una tarea para "marketing", se ejecuta
genéricamente sin contexto del equipo. Necesitamos que cada equipo tenga su propio
flujo de trabajo.

## Tu tarea

### A. Archivo config/team_workflows.yaml
Definir workflows por equipo:

```yaml
marketing:
  default_workflow: "research_and_post"
  workflows:
    research_and_post:
      steps:
        - task: research.web
          input_template:
            query: "{topic} marketing digital tendencias 2026"
            count: 5
        - task: llm.generate
          input_template:
            prompt: "Basado en esta investigación, genera un post para LinkedIn sobre {topic}: {prev_result}"
            model: gemini-2.5-flash
        - task: notion.add_comment
          input_template:
            text: "Rick: [Marketing] Post generado para {topic}:\n{prev_result}"

advisory:
  default_workflow: "financial_analysis"
  workflows:
    financial_analysis:
      steps:
        - task: research.web
          input_template:
            query: "{topic} análisis financiero inversión Chile"
            count: 5
        - task: llm.generate
          input_template:
            prompt: "Genera un análisis financiero breve sobre {topic} para un inversor chileno: {prev_result}"

improvement:
  default_workflow: "self_improvement_cycle"
  workflows:
    self_improvement_cycle:
      steps:
        - task: system.self_eval
        - task: llm.generate
          input_template:
            prompt: "Basado en esta auto-evaluación, sugiere 3 mejoras concretas: {prev_result}"

system:
  default_workflow: "health_report"
  workflows:
    health_report:
      steps:
        - task: ping
```

### B. Módulo dispatcher/workflow_engine.py
```python
class WorkflowEngine:
    def __init__(self, config_path, worker_client):
        self.workflows = load_yaml(config_path)
        self.wc = worker_client

    def execute_workflow(self, team, workflow_name, context):
        """
        Ejecuta los pasos del workflow secuencialmente.
        Cada paso recibe el resultado del paso anterior como {prev_result}.
        Retorna el resultado final.
        """

    def get_default_workflow(self, team):
        """Retorna el workflow default del equipo."""
```

### C. Integrar en smart_reply.py
Cuando el intent classifier detecta un "task" y lo routea a un equipo con workflow,
ejecutar el workflow en vez de solo responder con acknowledgment.

### D. Tests
Crear `tests/test_workflow_engine.py`:
- Test: workflow de marketing ejecuta los 3 pasos
- Test: prev_result se pasa entre pasos
- Test: equipo sin workflow usa fallback
- Test: error en un paso no crashea el workflow

## Archivos relevantes
- `config/teams.yaml` — equipos existentes
- `dispatcher/smart_reply.py` — integrar workflow execution
- `dispatcher/intent_classifier.py` — route_to_team (referencia)

## Log

### [codex] 2026-03-22 19:04 -03:00
Regularizacion administrativa por UMB-132. Esta tarea quedo como arrastre historico y ya no representa trabajo vivo; se cierra el archivo para alinearlo con el board y el estado real del repo.
