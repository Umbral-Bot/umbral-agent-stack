# Instrucciones para Agentes — Ronda 3

Todas las rondas anteriores completadas. Este archivo se actualizará con las nuevas tareas.

## Flujo de trabajo
```bash
git checkout main && git pull origin main
git checkout -b feat/<agente>-<feature>
# ... implementar ...
git add . && git commit -m "feat: descripcion"
git push -u origin feat/<agente>-<feature>
gh pr create --base main --title "[Agente] Feature" --body "Descripcion"
```
