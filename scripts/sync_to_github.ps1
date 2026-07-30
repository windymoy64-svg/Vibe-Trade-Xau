param(
    [string]$Message = "chore: sync local changes"
)

$ErrorActionPreference = "Stop"
Set-Location (Split-Path -Parent $PSScriptRoot)

Write-Host "Checking for tracked secrets and oversized files..."
$trackedSecrets = git ls-files | Select-String -Pattern '(^|/)(\.env|.*credentials.*|.*secret.*)$' -CaseSensitive:$false
if ($trackedSecrets) {
    throw "Potential secret file is tracked: $($trackedSecrets -join ', ')"
}

$largeFiles = Get-ChildItem -Recurse -File -ErrorAction SilentlyContinue |
    Where-Object { $_.Length -gt 50MB -and $_.FullName -notmatch '\\.git\\' }
if ($largeFiles) {
    throw "Files larger than 50 MB found: $($largeFiles.FullName -join ', ')"
}

git add -A
if (-not (git diff --cached --quiet)) {
    git commit -m $Message
} else {
    Write-Host "No new local changes to commit."
}

git fetch origin main
git pull --rebase origin main
git push origin main
Write-Host "GitHub synchronization completed: $(git rev-parse --short HEAD)"