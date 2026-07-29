[CmdletBinding()]
param(
    [string]$SshTarget = "note-keeper-vps",
    [string]$BackupDirectory = "$env:USERPROFILE\Backups\planbot",
    [ValidateRange(1, 3650)]
    [int]$RetentionCount = 14
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$ProfileRoot = [System.IO.Path]::GetFullPath($env:USERPROFILE)
$ResolvedBackupDirectory = [System.IO.Path]::GetFullPath($BackupDirectory)
$ProfilePrefix = $ProfileRoot.TrimEnd("\") + "\"
if (-not $ResolvedBackupDirectory.StartsWith(
    $ProfilePrefix,
    [System.StringComparison]::OrdinalIgnoreCase
)) {
    throw "BackupDirectory must be inside the current user profile."
}

New-Item -ItemType Directory -Path $ResolvedBackupDirectory -Force | Out-Null

$Today = Get-Date -Format "yyyyMMdd"
$ExistingToday = Get-ChildItem `
    -LiteralPath $ResolvedBackupDirectory `
    -File `
    -Filter "planbot-$Today-*.db" `
    -ErrorAction SilentlyContinue
if ($ExistingToday) {
    Write-Output "A successful planbot backup already exists for today."
    exit 0
}

$Timestamp = Get-Date -Format "yyyyMMdd-HHmmss"
$RemoteTemp = "/tmp/planbot-pc-backup-$([guid]::NewGuid().ToString('N')).db"
$PartialPath = Join-Path $ResolvedBackupDirectory "planbot-$Timestamp.db.partial"
$FinalPath = Join-Path $ResolvedBackupDirectory "planbot-$Timestamp.db"
$SshExecutable = (Get-Command ssh.exe -ErrorAction Stop).Source
$ScpExecutable = (Get-Command scp.exe -ErrorAction Stop).Source
$SshOptions = @(
    "-o", "BatchMode=yes",
    "-o", "ConnectTimeout=15",
    "-o", "ServerAliveInterval=10",
    "-o", "ServerAliveCountMax=2"
)

$RemoteBackupCode = @'
import hashlib
import json
import os
import sqlite3

source = sqlite3.connect("/opt/planbot/data/plan.db", timeout=30)
destination = sqlite3.connect("__REMOTE_TEMP__", timeout=30)
source.backup(destination)
integrity = destination.execute("PRAGMA integrity_check").fetchone()[0]
plans = destination.execute("SELECT count(*) FROM plans").fetchone()[0]
destination.close()
source.close()

if integrity != "ok":
    raise RuntimeError(f"backup integrity check failed: {integrity}")

os.chmod("__REMOTE_TEMP__", 0o600)
digest = hashlib.sha256()
with open("__REMOTE_TEMP__", "rb") as backup_file:
    for block in iter(lambda: backup_file.read(1024 * 1024), b""):
        digest.update(block)

print(json.dumps({
    "integrity": integrity,
    "plans": plans,
    "size": os.path.getsize("__REMOTE_TEMP__"),
    "sha256": digest.hexdigest(),
}))
'@.Replace("__REMOTE_TEMP__", $RemoteTemp)

$RemoteCleanupCode = @'
import os

path = "__REMOTE_TEMP__"
if os.path.exists(path):
    os.unlink(path)
'@.Replace("__REMOTE_TEMP__", $RemoteTemp)

try {
    $EncodedBackupCode = [Convert]::ToBase64String(
        [Text.Encoding]::UTF8.GetBytes($RemoteBackupCode)
    )
    $RemoteOutput = & $SshExecutable @SshOptions $SshTarget `
        "echo $EncodedBackupCode | base64 -d | python3"
    if ($LASTEXITCODE -ne 0) {
        throw "Could not create a consistent server backup."
    }

    $Metadata = $RemoteOutput |
        Select-Object -Last 1 |
        ConvertFrom-Json
    if ($Metadata.integrity -ne "ok" -or $Metadata.plans -lt 1) {
        throw "The server returned invalid backup metadata."
    }

    $RemoteSource = "${SshTarget}:$RemoteTemp"
    & $ScpExecutable -q @SshOptions $RemoteSource $PartialPath
    if ($LASTEXITCODE -ne 0 -or -not (Test-Path -LiteralPath $PartialPath)) {
        throw "Could not download the server backup."
    }

    $DownloadedFile = Get-Item -LiteralPath $PartialPath
    $DownloadedHash = (
        Get-FileHash -LiteralPath $PartialPath -Algorithm SHA256
    ).Hash.ToLowerInvariant()
    if (
        $DownloadedFile.Length -ne [long]$Metadata.size -or
        $DownloadedHash -ne [string]$Metadata.sha256
    ) {
        throw "The downloaded backup does not match the server copy."
    }

    Move-Item -LiteralPath $PartialPath -Destination $FinalPath

    $ExpiredBackups = Get-ChildItem `
        -LiteralPath $ResolvedBackupDirectory `
        -File `
        -Filter "planbot-????????-??????.db" |
        Sort-Object LastWriteTimeUtc -Descending |
        Select-Object -Skip $RetentionCount
    foreach ($ExpiredBackup in $ExpiredBackups) {
        Remove-Item -LiteralPath $ExpiredBackup.FullName -Force
    }

    $Success = [ordered]@{
        completed_at = (Get-Date).ToString("o")
        file = $FinalPath
        plans = [int]$Metadata.plans
        size = [long]$Metadata.size
        sha256 = [string]$Metadata.sha256
    } | ConvertTo-Json
    Set-Content `
        -LiteralPath (Join-Path $ResolvedBackupDirectory "last-success.json") `
        -Value $Success `
        -Encoding UTF8

    Write-Output "Backup saved: $FinalPath"
}
catch {
    Set-Content `
        -LiteralPath (Join-Path $ResolvedBackupDirectory "last-error.txt") `
        -Value ("{0:o} {1}" -f (Get-Date), $_.Exception.Message) `
        -Encoding UTF8
    throw
}
finally {
    $EncodedCleanupCode = [Convert]::ToBase64String(
        [Text.Encoding]::UTF8.GetBytes($RemoteCleanupCode)
    )
    & $SshExecutable @SshOptions $SshTarget `
        "echo $EncodedCleanupCode | base64 -d | python3" 2>$null

    if (Test-Path -LiteralPath $PartialPath) {
        Remove-Item -LiteralPath $PartialPath -Force
    }
}
