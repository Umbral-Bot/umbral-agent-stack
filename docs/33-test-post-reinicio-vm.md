# Test post-reinicio VM: control dual VPS → VM

## Objetivo

Comprobar que, tras reiniciar la VM y que Rick inicie sesión, el Worker interactivo (puerto 8089) arranca solo por el acceso directo en Inicio y la VPS puede ejecutar tareas con interfaz gráfica (ej. abrir Notepad en el escritorio).

## Prerrequisitos

- VM con el acceso directo **StartInteractiveWorker** en la carpeta Inicio de Rick (creado con la tarea `windows.add_interactive_worker_to_startup`).
- VPS con `WORKER_URL_VM_INTERACTIVE` y `WORKER_TOKEN` en `~/.config/openclaw/env`.

## Pasos del test

1. **Reiniciar la VM** (desde Hyper-V o desde la propia VM).
2. **Iniciar sesión** en la VM como Rick (si hay auto-logon, la sesión se inicia sola).
3. **Esperar unos segundos** a que el .bat del Worker interactivo se ejecute (ventana de consola puede aparecer brevemente o quedarse abierta).
4. **Desde la VPS**, ejecutar:

   ```bash
   cd ~/umbral-agent-stack
   python3 scripts/run_worker_task.py windows.open_notepad 'todo ok 999' --session interactive --run-now
   ```

5. **Comprobar en la VM**: debe abrirse un Bloc de notas con el texto **"todo ok 999"** en el escritorio de Rick.

## Criterio de éxito

- La respuesta del Worker es `"ok": true`, `"interactive": true`.
- El Notepad aparece en la sesión del usuario (visible en pantalla).

## Referencias

- Runbook: `runbooks/runbook-vm-interactive-worker-setup.md`
- Control dual: `docs/32-vps-vm-dual-session-control.md`
