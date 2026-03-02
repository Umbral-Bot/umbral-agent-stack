# Control dual de sesiones: VPS → VM (Sesión 0 y Sesión 1)

## Objetivo

Que la VPS pueda controlar la VM en **dos contextos**:

1. **Sesión 0** (sin interfaz gráfica): tareas automatizadas, fondo, sin interacción del usuario.
2. **Sesión 1** (interfaz gráfica): tareas que requieren GUI o interacción con el usuario (David) cuando Rick necesita ayuda para un paso solo realizable desde sesión con interfaz gráfica.

## Contexto actual

- La VPS envía tareas al Worker (FastAPI) en la VM.
- El Worker corre como **servicio** (cuenta SYSTEM) en **sesión 0**.
- Todo lo que lanza (Notepad, etc.) va a sesión 0 → no visible para el usuario.
- El usuario (David) está en **sesión 1** cuando usa la VM.

## Requisito

| Contexto   | Sesión | Uso                                    | Ejemplo                        |
|------------|--------|----------------------------------------|--------------------------------|
| Headless   | 0      | Automatización, fondo, sin GUI         | ping, notion.*, scripts CLI    |
| Interactivo| 1      | Mostrar cosas al usuario, pedir ayuda  | Abrir Notepad, PAD, diálogos   |

## Propuesta de diseño

### Opción A: Worker dual (recomendada)

1. **Worker actual (sistema)** – sesión 0  
   - Sigue como servicio NSSM bajo SYSTEM.  
   - Atiende tareas headless: `ping`, `notion.*`, `linear.*`, etc.

2. **Worker interactivo (sesión 1)**  
   - Proceso que corre bajo Rick cuando está logueado.  
   - Se inicia con Windows (Startup, tarea programada al logon, o servicio con /ru Rick).  
   - Atiende tareas con `session: "interactive"` o `session_target: 1`.  
   - Puede abrir Notepad, PAD y otros programas visibles para el usuario.

3. **Dispatcher/VPS**  
   - Decide destino según el tipo de tarea.  
   - Tareas con `session: "interactive"` → Worker interactivo.  
   - Resto → Worker sesión 0.

### Opción B: Un solo Worker con /ru para tareas interactivas

1. Worker sigue como servicio en sesión 0.  
2. Para tareas que requieren GUI, crea tareas programadas con `/ru pcrick\rick` y `/rp`.  
3. Necesita resolver el error de SID mapeo que vimos antes (formato de cuenta, contraseña, etc.).

### Opción C: APIs de Windows (WTSQueryUserToken + CreateProcessAsUser)

1. Worker en sesión 0.  
2. Usa `pywin32` (o ctypes) para obtener el token de sesión 1 y crear procesos en esa sesión.  
3. Más complejo y con dependencias extra.

## Parámetros de tarea

Para indicar sesión destino:

```json
{
  "task": "windows.open_notepad",
  "input": {
    "text": "hola",
    "session": "interactive"
  }
}
```

- `session: "interactive"` → ejecutar en sesión 1 (visible para el usuario).  
- `session: "headless"` o ausente → ejecutar en sesión 0 (por defecto actual).

## Implementación (Opción A)

- Script arranque: `scripts/vm/start_interactive_worker.bat` (puerto 8089).
- Runbook setup: `runbooks/runbook-vm-interactive-worker-setup.md`.
- Script run_worker_task: `--session interactive` envía a WORKER_URL_VM_INTERACTIVE (8089).
- Env VPS: `WORKER_URL_VM_INTERACTIVE=http://100.109.16.40:8089`.

## Referencias

- Setup Worker interactivo: `runbooks/runbook-vm-interactive-worker-setup.md`
- Runbook diagnóstico schtasks: `runbooks/runbook-vm-schtasks-runas-diagnosis.md`
- Worker setup VM: `runbooks/runbook-vm-worker-setup.md`
