# 34 — Token GitHub para Rick: descargar, leer, commit y PR (sin merge)

Rick (en la VPS) necesita acceso al repo para: `git clone`, `git pull`, leer archivos, hacer commit, push a ramas y abrir Pull Requests. **No** debe poder hacer merge de PRs; eso lo hace David (o Cursor).

**Configuración actual (dos mecanismos):**

- **Git (clone, pull, push):** SSH con **deploy key** del repo (`vps-rickm`). La deploy key solo permite operaciones git; no puede mergear PRs ni usar la API.
- **API (crear PR, comentar en PRs):** **PAT** (Fine-grained) en `GITHUB_TOKEN`. Los PRs y comentarios aparecen con la identidad de la cuenta del token (ej. UmbralBIM); Rick puede dejar comentarios indicando que es el agente.
- **Worker tasks `github.*`:** Los handlers `github.preflight`, `github.create_branch`, `github.commit_and_push`, `github.open_pr` y `github.orchestrate_tournament` consumen el PAT automáticamente (via `config.GITHUB_TOKEN`) para operaciones API (`gh` CLI), y la deploy key SSH para operaciones git (`git push/fetch`). Ver skill `github-ops` para documentación completa de cada handler.

> **Nota de identidad:** Los commits llevan la identidad de git configurada en la VPS (`Rick (AI Orchestrator) <rick.asistente@gmail.com>`). Los PRs y comentarios en GitHub aparecen como **UmbralBIM** (dueño del PAT). Solo los commits son atribuibles a Rick por identidad propia.

---

## 1. Deploy key SSH (git push / pull)

Para que Rick pueda hacer `git push` sin depender del PAT por HTTPS (que en algunas orgs falla para git):

1. **En la VPS:** Rick (o el setup) genera una clave SSH y expone la **clave pública**:
   ```bash
   ssh-keygen -t ed25519 -C "vps-rickm" -f ~/.ssh/id_ed25519_umbral -N ""
   cat ~/.ssh/id_ed25519_umbral.pub
   ```
2. **En GitHub:** Repo `Umbral-Bot/umbral-agent-stack` → **Settings** → **Deploy keys** → **Add deploy key**. Título ej. `vps-rickm`, pegar la clave pública, marcar **Allow write access**.
3. **En la VPS:** Remote en SSH y push:
   ```bash
   git remote set-url origin git@github.com:Umbral-Bot/umbral-agent-stack.git
   git push origin <rama>
   ```

Con esto Rick puede push/pull sin token por HTTPS. La deploy key **no** puede mergear PRs ni usar la API; solo operaciones git.

---

## 2. Crear el token en GitHub (API: PR, comentarios)

### Opción A: Fine-grained Personal Access Token (recomendado)

1. En GitHub: **Settings** (tu cuenta) → **Developer settings** → **Personal access tokens** → **Fine-grained tokens** → **Generate new token**.
2. **Token name:** p. ej. `rick-umbral-vps`.
3. **Expiration:** 90 días o "No expiration" si prefieres (luego rotar a mano).
4. **Repository access:** "Only select repositories" → elegir `Umbral-Bot/umbral-agent-stack`.
5. **Permissions** (solo para API: crear PR, comentar; el push va por SSH):
   - **Contents:** Read (opcional; para leer repo vía API).
   - **Pull requests:** Read and write (crear y editar PRs y comentarios).
   - **Metadata:** Read (siempre necesario).
6. **Generate token** y **copiar el token** (solo se muestra una vez).

### Opción B: Classic PAT

1. **Developer settings** → **Personal access tokens** → **Tokens (classic)** → **Generate new token (classic)**.
2. Marcar **repo** (acceso completo al repo).
3. Generar y copiar el token.

El token se usa **solo para la API** (crear PR, comentar). Git push/pull va por SSH (deploy key). Con **branch protection** en `main`, Rick no mergea; el merge lo hace David (o Cursor).

---

## 3. Guardar el token en la VPS

El token debe estar en la VPS donde corre Rick, **nunca** en el repo.

### En `~/.config/openclaw/env`

Añade una línea (con el token real que copiaste):

```bash
# GitHub: Rick puede pull, commit, push a ramas y abrir PR. No merge (branch protection).
GITHUB_TOKEN=ghp_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

Luego:

```bash
chmod 600 ~/.config/openclaw/env
```

Así los scripts que hacen `source ~/.config/openclaw/env` (o `export $(grep -v '^#' ~/.config/openclaw/env | xargs)`) tendrán `GITHUB_TOKEN` disponible.

---

## 4. Git en la VPS: remote por SSH

En la VPS el remote debe apuntar a SSH (no HTTPS), para usar la deploy key:

```bash
cd ~/umbral-agent-stack   # o la ruta del repo
git remote set-url origin git@github.com:Umbral-Bot/umbral-agent-stack.git
git remote -v
```

`git pull`, `git push` usan la deploy key; no hace falta credential helper ni token para git. El **token** (`GITHUB_TOKEN`) se usa solo cuando Rick llama a la **API** de GitHub (crear PR, comentar en PRs).

Opcional: configurar identidad de los commits para que en GitHub se vea la cuenta deseada:

```bash
git config user.name "UmbralBIM"   # o el nombre que deba aparecer
git config user.email "UmbralBIM@users.noreply.github.com"   # o el email de la cuenta
```

---

## 5. Comunicar a Rick qué puede y qué no

En **AGENTS.md** (y en el contexto que Rick lee) debe quedar claro:

- **Git:** remote por SSH (deploy key `vps-rickm`). Rick puede **clone**, **pull**, **commit**, **push a ramas**.
- **API:** `GITHUB_TOKEN` en el entorno. Rick puede **abrir PR** y **comentar en PRs** (los PRs y comentarios salen con la identidad de la cuenta del token).
- Rick **no debe** hacer **merge** de PRs; eso lo hace David (o Cursor). La deploy key no puede mergear; branch protection en `main` lo refuerza.

---

## 6. Comprobar que funciona (en la VPS)

**Git por SSH (deploy key):**

```bash
cd ~/umbral-agent-stack
git remote set-url origin git@github.com:Umbral-Bot/umbral-agent-stack.git
git fetch origin
git pull origin main
```

Si no pide contraseña, la deploy key está bien. Probar push en una rama de prueba:

```bash
git checkout -b rick/test-token
echo "# test" >> README.md
git add README.md && git commit -m "test: token"
git push -u origin rick/test-token
```

Luego borrar la rama desde GitHub o `git push origin --delete rick/test-token`.

**API (PAT):** si Rick usa `GITHUB_TOKEN` para crear PR o comentar, `source ~/.config/openclaw/env` antes de ejecutar lo que llame a la API.

---

## 7. Branch protection (recordatorio)

En el repo: **Settings** → **Branches** → regla para `main`:

- **Require a pull request before merging** (mín. 1 aprobación si quieres).
- Así Rick puede abrir PRs pero no mergear a `main`.

---

## 8. GitHub Copilot — Política operativa

### Estado actual

`gh copilot` **no está instalado** en la VPS. La extensión no está presente y la cuenta no tiene billing de Copilot activo (API retorna 404).

### Política de uso futuro

Si se instala `gh copilot` en la VPS:

| Aspecto | Regla |
|---------|-------|
| **Quién lo usa** | Solo Rick, de forma centralizada. Contestants de torneos **nunca** tienen acceso (sandbox `--network=none`, sin token, sin CLI) |
| **Comandos permitidos** | `gh copilot suggest` y `gh copilot explain` — asistencia local de bajo consumo |
| **Generación masiva** | Preferir Cursor con David para code review, generación masiva, o refactors de alto impacto |
| **Copilot MAX** | Solo si David lo autoriza explícitamente. No activar por iniciativa propia |
| **Créditos** | Monitorear consumo. Si David indica límite, desactivar inmediatamente |
| **Alcance** | Asistencia puntual. No reemplaza el flujo de tournaments ni los handlers existentes |

### Separación GitHub operativo vs. Copilot experimental

- **GitHub operativo** (rama, commit, push, PR): producción, cubierto por los handlers `github.*` y la deploy key + PAT. Siempre disponible.
- **Copilot** (suggest, explain): experimental, dependiente de billing y autorización de David. No es prerequisito para ningún flujo operativo.

### Requisitos para instalación

1. `gh extension install github/gh-copilot`
2. Billing de Copilot activo en la cuenta `UmbralBIM` (o la org)
3. Autorización explícita de David
4. Verificar con `gh copilot --version` y `gh copilot suggest "hello world"`

---

## Referencias

- Doc 28: [Rick: cuenta GitHub y workflow de PRs](28-rick-github-workflow.md)
- GitHub: [Fine-grained tokens](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/managing-your-personal-access-tokens#creating-a-fine-grained-personal-access-token)
- Seguridad: [docs/10-security-notes.md](10-security-notes.md)
