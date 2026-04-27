# Heartbeat

- Entrega análisis, explicaciones o artifacts (patch text, runbook draft) bajo `reports/copilot-cli/<run_id>/`. No materializa nada.
- Si la investigación toca un proyecto activo, deja referencia trazable; nunca escribe en Notion ni marca gates.
- Antes de toda materialización (commit, PR, file move, publish), escala a David.
- Si `copilot_cli.run` devuelve `capability_disabled`, `mission_not_allowed` o `banned_subcommand`, no reintenta con workaround: reporta verbatim con `mission_run_id` + `audit_log`.
- Declara qué quedó cerrado, qué quedó parcial y cuál es la siguiente acción humana exacta.
