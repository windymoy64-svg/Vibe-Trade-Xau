$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
$RuntimeRoot = Join-Path $ProjectRoot ".vibe-dev"

function Stop-TrackedProcess([string]$Name, [string]$PidPath) {
    if (-not (Test-Path -LiteralPath $PidPath)) {
        Write-Host "$Name tidak dijalankan oleh launcher."
        return
    }
    $pidText = (Get-Content -LiteralPath $PidPath -Raw).Trim()
    if ($pidText -match "^\d+$") {
        $process = Get-Process -Id ([int]$pidText) -ErrorAction SilentlyContinue
        if ($null -ne $process) {
            Stop-Process -Id $process.Id -Force
            Write-Host "$Name dihentikan (PID $($process.Id))."
        } else {
            Write-Host "$Name sudah tidak berjalan."
        }
    }
    Remove-Item -LiteralPath $PidPath -Force -ErrorAction SilentlyContinue
}

Stop-TrackedProcess "Frontend" (Join-Path $RuntimeRoot "auto-trade-frontend.pid")
Stop-TrackedProcess "Backend" (Join-Path $RuntimeRoot "auto-trade-backend.pid")
