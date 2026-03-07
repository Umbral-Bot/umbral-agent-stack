# Diagnóstico SSH / authorized_keys en la VM (PCRick)
# Ejecutar en la VM como Administrador: .\scripts\vm-ssh-key-diagnostic.ps1
# Genera: docs/audits/vm-ssh-diagnostic-YYYYMMDD-HHMMSS.txt

$ErrorActionPreference = "Continue"
$repoRoot = $null
if (Test-Path "C:\GitHub\umbral-agent-stack\.git") { $repoRoot = "C:\GitHub\umbral-agent-stack" }
if (-not $repoRoot -and $PSScriptRoot) {
    $repoRoot = (Get-Item $PSScriptRoot).Parent.FullName
}
if (-not $repoRoot) { $repoRoot = Get-Location }

$timestamp = Get-Date -Format "yyyyMMdd-HHmmss"
$outDir = Join-Path $repoRoot "docs\audits"
$outFile = Join-Path $outDir "vm-ssh-diagnostic-$timestamp.txt"
if (-not (Test-Path $outDir)) { New-Item -ItemType Directory -Path $outDir -Force | Out-Null }

$sb = [System.Text.StringBuilder]::new()
function Log { param($msg) [void]$sb.AppendLine($msg) }
function Sep { Log ""; Log ("=" * 60) }

Log "VM SSH key diagnostic — $timestamp"
Log "Hostname: $env:COMPUTERNAME"
Log "User: $env:USERNAME"
Sep

# 1. OpenSSH server
Log "1. OpenSSH Server"
try {
    $sshd = Get-Service sshd -ErrorAction Stop
    Log "   Status: $($sshd.Status)"
    Log "   StartType: $($sshd.StartType)"
} catch { Log "   Error: $_" }
$exe = "C:\Windows\System32\OpenSSH\sshd.exe"
if (Test-Path $exe) {
    $ver = (Get-Item $exe).VersionInfo.FileVersion
    Log "   sshd.exe: $exe (Version: $ver)"
}
Sep

# 2. sshd_config
Log "2. sshd_config (relevant lines)"
$cfgPath = "C:\ProgramData\ssh\sshd_config"
if (Test-Path $cfgPath) {
    $lines = Get-Content $cfgPath
    foreach ($line in $lines) {
        $t = $line.Trim()
        if ($t -match "^(PubkeyAuthentication|AuthorizedKeysFile|PasswordAuthentication|PermitRootLogin|Match)" -or $t -match "^#?\s*(Pubkey|Authorized|Password|PermitRoot|Match)") {
            Log "   $line"
        }
    }
} else { Log "   File not found: $cfgPath" }
Sep

# 3. authorized_keys path for rick
$rickHome = "C:\Users\rick"
$authKeysPath = Join-Path $rickHome ".ssh\authorized_keys"
Log "3. authorized_keys path (rick)"
Log "   $authKeysPath"
Log "   Exists: $(Test-Path $authKeysPath)"
Sep

# 4. File content (structure only: first/last chars per line, length)
Log "4. authorized_keys content (structure)"
if (Test-Path $authKeysPath) {
    $raw = [System.IO.File]::ReadAllBytes($authKeysPath)
    Log "   File size: $($raw.Length) bytes"
    $hasBOM = ($raw.Length -ge 3 -and $raw[0] -eq 0xEF -and $raw[1] -eq 0xBB -and $raw[2] -eq 0xBF)
    Log "   UTF-8 BOM: $hasBOM"
    $crlf = 0; $lf = 0
    for ($i = 0; $i -lt $raw.Length - 1; $i++) {
        if ($raw[$i] -eq 13 -and $raw[$i+1] -eq 10) { $crlf++ }
        if ($raw[$i] -eq 10 -and ($i -eq 0 -or $raw[$i-1] -ne 13)) { $lf++ }
    }
    if ($raw.Length -ge 1 -and $raw[-1] -eq 10) { $lf++ }
    Log "   CRLF count: $crlf | LF-only count: $lf"
    $content = [System.Text.Encoding]::UTF8.GetString($raw)
    $lines = $content -split "`n|`r`n|`r"
    $lines = @($lines | Where-Object { $_.Trim() -ne "" })
    Log "   Number of non-empty lines: $($lines.Count)"
    for ($i = 0; $i -lt [Math]::Min(5, $lines.Count); $i++) {
        $l = $lines[$i].Trim()
        $pre = if ($l.Length -gt 30) { $l.Substring(0, 30) } else { $l }
        $suf = if ($l.Length -gt 60) { "..." + $l.Substring($l.Length - 25) } else { "" }
        Log "   Line $($i+1): len=$($l.Length) start=[$pre]$suf"
    }
} else { Log "   File not found." }
Sep

# 5. Permissions (icacls)
Log "5. Permissions"
$dirPath = Join-Path $rickHome ".ssh"
foreach ($p in @($dirPath, $authKeysPath)) {
    if (Test-Path $p) {
        Log "   $p"
        try {
            $icacls = & icacls $p 2>&1
            foreach ($line in $icacls) { Log "      $line" }
        } catch { Log "      Error: $_" }
    }
}
Sep

# 6. First 200 bytes hex (to spot BOM/CRLF)
Log "6. authorized_keys first 200 bytes (hex)"
if (Test-Path $authKeysPath) {
    $bytes = [System.IO.File]::ReadAllBytes($authKeysPath)
    $take = [Math]::Min(200, $bytes.Length)
    $hex = ($bytes[0..($take-1)] | ForEach-Object { $_.ToString("X2") }) -join " "
    Log "   $hex"
}
Sep

# 7. Rick's .ssh (known_hosts, identity) — si ssh se ejecuta desde la VM como Rick
$rickSsh = Join-Path $rickHome ".ssh"
Log "7. C:\Users\Rick\.ssh (when running ssh FROM the VM as Rick)"
if (Test-Path $rickSsh) {
    $knownHosts = Join-Path $rickSsh "known_hosts"
    $idRsa = Join-Path $rickSsh "id_rsa"
    Log "   known_hosts exists: $(Test-Path $knownHosts)"
    if (Test-Path $knownHosts) {
        try { $acl = (Get-Acl $knownHosts -ErrorAction Stop).Access; Log "   known_hosts: icacls below" } catch { Log "   known_hosts: $_" }
        try { $ic = & icacls $knownHosts 2>&1; foreach ($x in $ic) { Log "      $x" } } catch { }
    }
    Log "   id_rsa exists: $(Test-Path $idRsa)  (expected false — David's key is on PC only)"
}
Log "   Expected when running \`"ssh rick@100.109.16.40\`" FROM VM as Rick:"
Log "     - Identity file C:\Users\Rick\.ssh\id_rsa not accessible (Rick has no private key on VM)"
Log "     - hostkeys_foreach failed for known_hosts: Permission denied (if Rick cannot read/write .ssh)"
Log "     - Failed to add the host to the list of known_hosts (same)"
Log "     - Connection reset by 100.109.16.40 port 22"
Log "   Fix: run ssh FROM your PC (David), not from the VM. VPS connects as rick with its own key."
Sep

# 8. Expected key type
Log "8. Note"
Log "   Client key (David PC): id_rsa (RSA). Server must have matching ssh-rsa line in authorized_keys."
Log "   If key is rejected, check: no BOM, LF line endings, rick has (R) on file, no extra chars in line."
Log ""

$report = $sb.ToString()
[System.IO.File]::WriteAllText($outFile, $report, [System.Text.UTF8Encoding]::new($false))
Write-Host "Diagnostic written to: $outFile"
Write-Host $report
