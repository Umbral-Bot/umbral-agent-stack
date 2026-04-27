# Instrucciones para Rick (VPS): rama `rick/vps`, sin clonación de main

> Este documento explica el cambio de flujo Git en la VPS y qué debes hacer tú (Rick) en el servidor. David/Cursor ha aplicado los cambios en el repo (scripts, runbook); lo que **no** se puede hacer desde aquí es ejecutar comandos en tu VPS. Sigue estos pasos en la VPS y, al terminar, deja un mensaje en [.agents/rick-vps-message.md](../.agents/rick-vps-message.md) en la rama `rick/vps` para que David/Cursor lo lea.

---

## 1. Qué cambió

- **Antes:** En la VPS se trabajaba o se asumía la rama `main`; los crons y el Worker corrían desde el mismo clone.
- **Ahora:**
  - **Rama de trabajo en la VPS = `rick/vps`.** No se hace commit ni push a `main` desde la VPS. Todo cambio que hagas: en la rama `rick/vps`, push, abres PR; David/Cursor hace el merge a `main`. (Se usa `rick/vps` y no `rick` porque ya existen ramas `rick/*` en el repo y Git no permite rama `rick` y `rick/...` a la vez.)
  - **El stack (Worker, Dispatcher, crons) sigue ejecutando código de `main`.** Cada script que arranca el Worker, el Dispatcher o un cron llama a `scripts/vps/ensure-main-for-run.sh`, que hace `git checkout main && git pull origin main` antes de ejecutar. Así el código en producción es siempre el de `main` (ya mergeado), aunque cuando tú hagas `cd ~/umbral-agent-stack` el repo esté en la rama `rick`.

Resumen: **tú trabajas en `rick/vps`; el servidor corre desde `main`.**

---

## 2. Pasos que debes hacer en la VPS (una sola vez)

### 2.1 Si ya tienes el repo clonado en `~/umbral-agent-stack`

1. Conéctate por SSH a la VPS.
2. Entra al repo y crea la rama `rick/vps` desde `main` (si aún no existe) y deja el repo en `rick/vps`:

   ```bash
   cd ~/umbral-agent-stack
   git fetch origin
   git checkout main
   git pull origin main
   git checkout -b rick/vps
   git push -u origin rick/vps
   ```

   A partir de ahora, cuando hagas `cd ~/umbral-agent-stack` y `git branch`, deberías ver `* rick/vps`. Los crons y el supervisor ya están modificados para hacer `ensure-main-for-run.sh` antes de ejecutar, así que seguirán corriendo desde `main`; no hace falta que cambies nada más para que el stack funcione.

3. **(Opcional pero recomendado)** Instalar el hook para no hacer push a `main` por error:

   ```bash
   cd ~/umbral-agent-stack
   echo '#!/bin/sh
   bash scripts/vps/rick-ensure-not-pushing-main.sh || exit 1' > .git/hooks/pre-push
   chmod +x .git/hooks/pre-push
   ```

### 2.2 Si vas a clonar el repo por primera vez en la VPS

1. Clona y entra en la rama `rick/vps`:

   ```bash
   cd ~
   git clone git@github.com:Umbral-Bot/umbral-agent-stack.git umbral-agent-stack
   cd umbral-agent-stack
   bash scripts/vps/rick-branch-for-change.sh
   git push -u origin rick/vps
   ```

2. Configura env, venv, Redis, crons, etc. según el runbook ([docs/62-operational-runbook.md](62-operational-runbook.md)). Los scripts de cron y el supervisor ya incluyen la lógica para ejecutar desde `main`.

---

## 3. Flujo de trabajo diario (después de la configuración)

- **Para editar código o docs desde la VPS:** Ya estás en la rama `rick/vps`. Haz cambios, commit, `git push origin rick/vps`, abre PR a `main` (por GitHub o con `GITHUB_TOKEN` en env). **No** mergees el PR; lo hace David/Cursor.
- **Después de que David/Cursor mergee tu PR:** Actualiza tu rama `rick/vps` con lo nuevo de `main`:
  ```bash
  cd ~/umbral-agent-stack
  git checkout main && git pull origin main
  git checkout rick/vps && git merge main
  ```
- **Para comprobar que el stack corre bien:** El supervisor y los crons ya hacen `ensure-main-for-run.sh`; el Worker y el Dispatcher se arrancan con código de `main`. Puedes ejecutar `bash scripts/vps/supervisor.sh` para ver estado; si reinicia algo, usará main automáticamente.

---

## 4. Enlaces útiles

- **Rama rick/vps en GitHub:** https://github.com/Umbral-Bot/umbral-agent-stack/tree/rick/vps  
- **Crear PR rick/vps → main:** https://github.com/Umbral-Bot/umbral-agent-stack/compare/main...rick/vps  
- Runbook (política Git y verificación VPS): [docs/62-operational-runbook.md](62-operational-runbook.md) §7.0 y §7.0.1  
- Token GitHub y deploy key: [docs/34-rick-github-token-setup.md](34-rick-github-token-setup.md)

---

## 5. Mensaje para David/Cursor

Cuando hayas aplicado estos pasos en la VPS (y, si aplica, instalado el hook y comprobado que el stack sigue en marcha), **edita el archivo [.agents/rick-vps-message.md](../.agents/rick-vps-message.md)** en la rama `rick/vps`: escribe qué hiciste, si algo falló o si hay algo que David deba revisar. Haz commit y push de ese archivo a la rama `rick/vps`. David/Cursor leerá ese mensaje en el repo (o en el PR de rick/vps a main).
