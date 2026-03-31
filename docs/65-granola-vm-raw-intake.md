# Granola VM Raw Intake

Flujo recomendado para operar Granola desde la VM Windows sin depender de exports manuales.

## Objetivo

Mover reuniones desde la VM donde vive Granola hacia la DB raw de Notion usando el stack actual:

`cache/API local de Granola -> batch seguro -> Worker /run -> raw Notion`

Este flujo:

- sí usa el cache/API real de Granola en Windows;
- sí pasa por `granola.process_transcript` vía `/run`;
- sí deja trazabilidad fuerte en raw;
- no hace `raw -> canonical`;
- no toca CRM, programas, recursos ni sesión capitalizable.

## Cuándo usarlo

Usar este flujo como camino principal para Rick en la VM cuando:

- Granola está instalado en Windows;
- el cache vive en `%APPDATA%\Granola\cache-v6.json`;
- el Worker local en la VM está disponible en `http://127.0.0.1:8088`;
- se quiere medir capacidad real de Rick por handler, no por ejecución directa desde otro operador.

## Componentes

### 1. Worker local

Debe existir un Worker sano en la VM en `8088`.

Referencia:

- [06-setup-worker-windows.md](C:/GitHub/umbral-agent-stack-codex/docs/06-setup-worker-windows.md)

### 2. Runner VM

Script principal:

- [granola_vm_raw_intake.py](C:/GitHub/umbral-agent-stack-codex/scripts/vm/granola_vm_raw_intake.py)

Responsabilidades:

- correr el gap audit live;
- seleccionar solo el bucket seguro configurado;
- exportar markdown temporal;
- exigir preflight exitoso del Worker;
- ejecutar el batch únicamente en `mode=worker`;
- guardar un reporte JSON por corrida en `C:\Granola\reports`.

### 3. Launcher oculto

- [start_granola_vm_raw_intake_hidden.ps1](C:/GitHub/umbral-agent-stack-codex/scripts/vm/start_granola_vm_raw_intake_hidden.ps1)

Se usa como target de Task Scheduler y evita procesos duplicados.

### 4. Instalador

- [setup_granola_vm_raw_intake.ps1](C:/GitHub/umbral-agent-stack-codex/scripts/vm/setup_granola_vm_raw_intake.ps1)

Configura:

- `C:\Granola\.env`
- bucket seguro
- tamaño máximo por corrida
- report dir
- tarea programada `GranolaVmRawIntake`

### 5. Smoke test

- [test_granola_vm_raw_intake.ps1](C:/GitHub/umbral-agent-stack-codex/scripts/vm/test_granola_vm_raw_intake.ps1)

Verifica:

- cache local accesible;
- Worker sano;
- preview del runner sin escribir en Notion.

## Instalación

En la VM:

```powershell
cd C:\GitHub\umbral-agent-stack-codex
.\scripts\vm\setup_granola_vm_raw_intake.ps1
```

Después validar:

```powershell
.\scripts\vm\test_granola_vm_raw_intake.ps1
```

## Ejecución manual

Preview:

```powershell
python scripts\vm\granola_vm_raw_intake.py --json
```

Ejecución real:

```powershell
python scripts\vm\granola_vm_raw_intake.py --execute --json
```

## Cadencia recomendada

No usar una automatización ciega “una vez al día”.

Recomendación:

- task segura cada `4 horas`;
- bucket por defecto `batch1_recent_unique`;
- máximo `5` ítems por corrida;
- ambiguos siempre fuera del task automático.

## Regla para títulos repetidos

No usar el título como llave canónica.

Regla operativa:

- mismo `granola_document_id`:
  - actualizar/completar el mismo raw si cambia `source_updated_at`
- distinto `granola_document_id` y distinta fecha:
  - crear nueva página raw automáticamente
- distinto `granola_document_id`, mismo título y mismo día:
  - no crear ni actualizar automáticamente
  - dejar comentario para revisión

## Evidencia y capacidad de Rick

Este flujo es mejor para evaluar a Rick porque:

- mide reachability real del Worker;
- mide éxito del handler `/run`;
- deja reporte JSON por corrida;
- separa claramente ejecución segura de revisión humana obligatoria.

## Fuera de scope

- `raw -> session_capitalizable`
- capitalización a tareas/proyectos/entregables
- CRM / programas / recursos
- drafts de correo
- briefing matinal
