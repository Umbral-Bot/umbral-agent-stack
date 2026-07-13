<#
.SYNOPSIS
    Exporta toda la configuración de VS Code, skills, agentes y extensiones
    para replicar el setup en otra máquina.

.DESCRIPTION
    Crea un ZIP con:
    - settings.json y keybindings.json
    - Prompts e instrucciones de usuario
    - Agentes custom (.agent.md)
    - Skills custom (.copilot/skills, .claude/skills, .agents/skills)
    - Config de Claude (settings, plugins instalados)
    - Lista de extensiones (para reinstalar con code --install-extension)
    - MCP config si existe

.PARAMETER OutputPath
    Ruta donde se creará el ZIP. Default: Desktop\vscode-config-export.zip

.EXAMPLE
    .\export-vscode-config.ps1
    .\export-vscode-config.ps1 -OutputPath "D:\backup\mi-vscode.zip"
#>

param(
    [string]$OutputPath
)

if (-not $OutputPath) {
    # Detect Desktop location (OneDrive or local)
    $desktop = if (Test-Path "$env:USERPROFILE\OneDrive\Desktop") {
        "$env:USERPROFILE\OneDrive\Desktop"
    } else {
        [Environment]::GetFolderPath("Desktop")
    }
    $OutputPath = Join-Path $desktop "vscode-config-export.zip"
}

$ErrorActionPreference = "Stop"
$timestamp = Get-Date -Format "yyyy-MM-dd_HHmmss"
$tempDir = Join-Path $env:TEMP "vscode-export-$timestamp"

Write-Host "`n=== Exportador de configuración VS Code ===" -ForegroundColor Cyan
Write-Host "Destino: $OutputPath`n"

# Create temp staging directory
New-Item -ItemType Directory -Path $tempDir -Force | Out-Null

function Copy-IfExists {
    param([string]$Source, [string]$DestRelative)
    $dest = Join-Path $tempDir $DestRelative
    if (Test-Path $Source) {
        $destDir = Split-Path $dest -Parent
        if (-not (Test-Path $destDir)) {
            New-Item -ItemType Directory -Path $destDir -Force | Out-Null
        }
        if ((Get-Item $Source).PSIsContainer) {
            Copy-Item $Source $dest -Recurse -Force
            $count = (Get-ChildItem $dest -Recurse -File -ErrorAction SilentlyContinue).Count
            Write-Host "  [OK] $DestRelative ($count archivos)" -ForegroundColor Green
        } else {
            Copy-Item $Source $dest -Force
            Write-Host "  [OK] $DestRelative" -ForegroundColor Green
        }
    } else {
        Write-Host "  [--] $DestRelative (no existe, saltando)" -ForegroundColor DarkGray
    }
}

# ── 1. VS Code User Settings ──
Write-Host "`n1. Configuración de VS Code" -ForegroundColor Yellow
$codeUser = "$env:APPDATA\Code\User"
Copy-IfExists "$codeUser\settings.json"    "vscode-user\settings.json"
Copy-IfExists "$codeUser\keybindings.json" "vscode-user\keybindings.json"
Copy-IfExists "$codeUser\snippets"         "vscode-user\snippets"

# ── 2. Prompts e instrucciones de usuario ──
Write-Host "`n2. Prompts e instrucciones" -ForegroundColor Yellow
Copy-IfExists "$codeUser\prompts" "vscode-user\prompts"

# ── 3. Copilot Custom Agents (.agent.md) ──
Write-Host "`n3. Agentes custom de Copilot" -ForegroundColor Yellow
Copy-IfExists "$env:USERPROFILE\.copilot\agents" "copilot\agents"

# ── 4. Copilot Skills (user-level) ──
Write-Host "`n4. Skills de Copilot (user-level)" -ForegroundColor Yellow
Copy-IfExists "$env:USERPROFILE\.copilot\skills" "copilot\skills"

# ── 5. Claude Config ──
Write-Host "`n5. Claude config" -ForegroundColor Yellow
Copy-IfExists "$env:USERPROFILE\.claude\settings.json"                "claude\settings.json"
Copy-IfExists "$env:USERPROFILE\.claude\skills"                       "claude\skills"
Copy-IfExists "$env:USERPROFILE\.claude\plugins\installed_plugins.json" "claude\plugins\installed_plugins.json"
Copy-IfExists "$env:USERPROFILE\.claude\plugins\known_marketplaces.json" "claude\plugins\known_marketplaces.json"

# ── 6. .agents skills (AI Toolkit / Foundry) ──
Write-Host "`n6. Skills de .agents (AI Toolkit)" -ForegroundColor Yellow
Copy-IfExists "$env:USERPROFILE\.agents\skills"          "agents\skills"
Copy-IfExists "$env:USERPROFILE\.agents\.skill-lock.json" "agents\.skill-lock.json"

# ── 7. Agent Plugins (installed by extensions like awesome-copilot) ──
Write-Host "`n7. Agent Plugins" -ForegroundColor Yellow
# These are large (3000+ files) and auto-installed by extensions.
# We export only the top-level manifest to know which plugins are installed.
$agentPluginsPath = "$env:USERPROFILE\.vscode\agent-plugins"
if (Test-Path $agentPluginsPath) {
    # Copy only .md and .yaml/.yml files (skill definitions), skip node_modules and caches
    $pluginFiles = Get-ChildItem $agentPluginsPath -Recurse -File -ErrorAction SilentlyContinue |
        Where-Object { $_.Extension -in '.md','.yaml','.yml','.json' -and $_.FullName -notmatch 'node_modules|\.cache|__pycache__' }
    $pluginDest = Join-Path $tempDir "agent-plugins"
    foreach ($f in $pluginFiles) {
        $rel = $f.FullName.Substring($agentPluginsPath.Length)
        $targetFile = Join-Path $pluginDest $rel
        $targetDir = Split-Path $targetFile -Parent
        if (-not (Test-Path $targetDir)) {
            New-Item -ItemType Directory -Path $targetDir -Force | Out-Null
        }
        Copy-Item $f.FullName $targetFile -Force
    }
    Write-Host "  [OK] agent-plugins ($($pluginFiles.Count) archivos de config/skills)" -ForegroundColor Green
} else {
    Write-Host "  [--] agent-plugins (no existe)" -ForegroundColor DarkGray
}

# ── 8. MCP Config ──
Write-Host "`n8. MCP config" -ForegroundColor Yellow
Copy-IfExists "$codeUser\globalStorage\github.copilot-chat\mcp.json" "vscode-user\mcp.json"
# Also check settings.json for MCP server definitions (they're inline in settings)
# The settings.json already copied covers this

# ── 9. Extension List ──
Write-Host "`n9. Lista de extensiones" -ForegroundColor Yellow
$extDir = "$env:USERPROFILE\.vscode\extensions"
$extensions = Get-ChildItem $extDir -Directory -ErrorAction SilentlyContinue |
    Where-Object { $_.Name -notmatch '^\.' } |
    ForEach-Object {
        # Parse extension id from folder name (publisher.name-version)
        if ($_.Name -match '^(.+)-(\d+\.\d+\.\d+.*)$') {
            $Matches[1]
        } else {
            $_.Name
        }
    } | Sort-Object -Unique

$extListPath = Join-Path $tempDir "extensions.txt"
$extensions | Set-Content $extListPath -Encoding UTF8
Write-Host "  [OK] extensions.txt ($($extensions.Count) extensiones)" -ForegroundColor Green

# Also create a batch install script
$installScript = @"
# Instalar extensiones de VS Code
# Ejecutar en PowerShell:
#   .\install-extensions.ps1

`$extensions = @(
$($extensions | ForEach-Object { "    `"$_`"" } | Join-String -Separator "`n")
)

foreach (`$ext in `$extensions) {
    Write-Host "Instalando `$ext..." -ForegroundColor Cyan
    code --install-extension `$ext --force
}
Write-Host "`nTodas las extensiones instaladas." -ForegroundColor Green
"@
$installScriptPath = Join-Path $tempDir "install-extensions.ps1"
$installScript | Set-Content $installScriptPath -Encoding UTF8
Write-Host "  [OK] install-extensions.ps1 (script de instalación)" -ForegroundColor Green

# ── 10. Restore instructions ──
Write-Host "`n10. Generando instrucciones de restauración..." -ForegroundColor Yellow
$readme = @"
# Restaurar configuración VS Code

Exportado: $timestamp
Desde: $env:COMPUTERNAME

## Pasos para restaurar en la notebook:

### 1. Instalar extensiones
``````powershell
.\install-extensions.ps1
``````

### 2. Copiar configuración de VS Code
``````powershell
Copy-Item "vscode-user\settings.json"    "`$env:APPDATA\Code\User\settings.json" -Force
Copy-Item "vscode-user\keybindings.json" "`$env:APPDATA\Code\User\keybindings.json" -Force
# Prompts e instrucciones
Copy-Item "vscode-user\prompts" "`$env:APPDATA\Code\User\prompts" -Recurse -Force
# Snippets (si existen)
if (Test-Path "vscode-user\snippets") {
    Copy-Item "vscode-user\snippets" "`$env:APPDATA\Code\User\snippets" -Recurse -Force
}
``````

### 3. Copiar agentes y skills de Copilot
``````powershell
Copy-Item "copilot\agents" "`$env:USERPROFILE\.copilot\agents" -Recurse -Force
Copy-Item "copilot\skills" "`$env:USERPROFILE\.copilot\skills" -Recurse -Force
``````

### 4. Copiar config de Claude
``````powershell
Copy-Item "claude\settings.json" "`$env:USERPROFILE\.claude\settings.json" -Force
Copy-Item "claude\skills" "`$env:USERPROFILE\.claude\skills" -Recurse -Force
# Plugins (reinstalar desde Claude):
# Los plugins se reinstalan solos; el archivo installed_plugins.json es solo referencia.
``````

### 5. Copiar skills de .agents (AI Toolkit)
``````powershell
Copy-Item "agents\skills" "`$env:USERPROFILE\.agents\skills" -Recurse -Force
Copy-Item "agents\.skill-lock.json" "`$env:USERPROFILE\.agents\.skill-lock.json" -Force
``````

### 6. Agent Plugins
Los agent-plugins se instalan automáticamente con las extensiones
(GitHub Copilot Chat + awesome-copilot). Solo se exportaron los archivos
de definición como referencia. Al instalar las extensiones, se descargan solos.

### 7. Config de repositorios
La config por repo (.github/copilot-instructions.md, AGENTS.md, .agents/,
.claude/, .cursor/rules/) viaja con git. Solo clonando los repos ya la tenés.

### 8. MCP Servers
Si usás MCP servers, la config está en settings.json (ya copiado en paso 2).
Verificá que los binarios/servicios MCP estén instalados en la notebook.

## Notas
- Las credenciales (.claude/.credentials.json, tokens, .env) NO se exportan.
  Configurá las credenciales manualmente en la notebook.
- Si usás Settings Sync de VS Code, podés sincronizar settings.json y
  extensiones automáticamente con tu cuenta de GitHub/Microsoft.
"@
$readmePath = Join-Path $tempDir "RESTORE-README.md"
$readme | Set-Content $readmePath -Encoding UTF8
Write-Host "  [OK] RESTORE-README.md" -ForegroundColor Green

# ── Create ZIP ──
Write-Host "`n=== Comprimiendo... ===" -ForegroundColor Cyan
if (Test-Path $OutputPath) {
    Remove-Item $OutputPath -Force
}
Compress-Archive -Path "$tempDir\*" -DestinationPath $OutputPath -CompressionLevel Optimal
$zipSize = [math]::Round((Get-Item $OutputPath).Length / 1MB, 2)
Write-Host "ZIP creado: $OutputPath ($zipSize MB)" -ForegroundColor Green

# Cleanup
Remove-Item $tempDir -Recurse -Force -ErrorAction SilentlyContinue

Write-Host "`n=== Exportación completa ===" -ForegroundColor Cyan
Write-Host "Copiá el ZIP a tu notebook y seguí las instrucciones en RESTORE-README.md`n"
