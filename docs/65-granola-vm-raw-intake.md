# Granola VM Raw Intake

Flujo recomendado para operar Granola desde la VM Windows sin depender de exports manuales.

## Objetivo

Mover reuniones desde la VM donde vive Granola hacia la DB raw de Notion usando el stack actual:

`cache/API local de Granola -> batch seguro -> Worker /run -> raw Notion`

Este flujo:

- si usa el cache/API real de Granola en Windows;
- si pasa por `granola.process_transcript` via `/run`;
- si deja trazabilidad fuerte en raw;
- no hace `raw -> canonical`;
- no toca CRM, programas, recursos ni sesion capitalizable.

## Cuando usarlo

Usar este flujo como camino principal para Rick en la VM cuando:

- Granola esta instalado en Windows;
- el cache vive en `%APPDATA%\Granola\cache-v6.json`;
- el Worker local en la VM esta disponible en `http://127.0.0.1:8088`;
- se quiere medir capacidad real de Rick por handler, no por ejecucion directa desde otro operador.

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
- ejecutar el batch unicamente en `mode=worker`;
- guardar un reporte JSON por corrida en `C:\Granola\reports`.

### 3. Launcher oculto

- [start_granola_vm_raw_intake_hidden.ps1](C:/GitHub/umbral-agent-stack-codex/scripts/vm/start_granola_vm_raw_intake_hidden.ps1)

Se usa como target de Task Scheduler y evita procesos duplicados.

### 4. Launcher de arranque

- [start_granola_vm_raw_intake_startup_hidden.ps1](C:/GitHub/umbral-agent-stack-codex/scripts/vm/start_granola_vm_raw_intake_startup_hidden.ps1)

Responsabilidades:

- esperar a que el Worker local responda en `8088`;
- correr el smoke test de arranque;
- lanzar una corrida segura de intake al iniciar sesion;
- dejar log de arranque en `C:\Granola\vm-raw-intake-startup.log`.

### 5. Instalador

- [setup_granola_vm_raw_intake.ps1](C:/GitHub/umbral-agent-stack-codex/scripts/vm/setup_granola_vm_raw_intake.ps1)

Configura:

- `C:\Granola\.env`
- bucket seguro
- tamano maximo por corrida
- report dir
- tarea programada `GranolaVmRawIntakeStartup`
- tarea programada `GranolaVmRawIntake`

### 6. Smoke test

- [test_granola_vm_raw_intake.ps1](C:/GitHub/umbral-agent-stack-codex/scripts/vm/test_granola_vm_raw_intake.ps1)

Verifica:

- cache local accesible;
- Worker sano;
- preview del runner sin escribir en Notion.

## Instalacion

En la VM:

```powershell
cd C:\GitHub\umbral-agent-stack-codex
.\scripts\vm\setup_granola_vm_raw_intake.ps1
```

Despues validar:

```powershell
.\scripts\vm\test_granola_vm_raw_intake.ps1
```

## Ejecucion manual

Preview:

```powershell
python scripts\vm\granola_vm_raw_intake.py --json
```

Ejecucion real:

```powershell
python scripts\vm\granola_vm_raw_intake.py --execute --json
```

## Cadencia recomendada

No usar una automatizacion ciega una vez al dia.

Recomendacion:

- una corrida segura al iniciar sesion en la VM;
- task segura cada `4 horas`;
- bucket por defecto `batch1_recent_unique`;
- maximo `5` items por corrida;
- ambiguos siempre fuera del task automatico.

## Encendido y apagado de la VM

La VM puede estar apagada parte del dia. Por eso conviene:

- automatizar una corrida de arranque, no depender de que Rick la dispare manualmente;
- mantener una tarea periodica solo mientras la VM este encendida;
- usar a Rick como revisor de logs, reportes y ambiguos.

No agregamos una tarea de apagado en V1. Tiene menos valor operativo que:

- el check de arranque;
- la cadencia horaria mientras la VM esta encendida;
- la reconciliacion del siguiente arranque.

## Regla para titulos repetidos

No usar el titulo como llave canonica.

Regla operativa:

- mismo `granola_document_id`:
  - actualizar/completar el mismo raw si cambia `source_updated_at`
- distinto `granola_document_id` y distinta fecha:
  - crear nueva pagina raw automaticamente
- distinto `granola_document_id`, mismo titulo y mismo dia:
  - no crear ni actualizar automaticamente
  - dejar comentario para revision

## Evidencia y capacidad de Rick

Este flujo es mejor para evaluar a Rick porque:

- mide reachability real del Worker;
- mide exito del handler `/run`;
- deja reporte JSON por corrida;
- separa claramente ejecucion segura de revision humana obligatoria;
- permite medir a Rick como supervisor del sistema, no como operador manual de copia y pega.

## Fuera de scope

- `raw -> session_capitalizable`
- capitalizacion a tareas/proyectos/entregables
- CRM / programas / recursos
- drafts de correo
- briefing matinal
