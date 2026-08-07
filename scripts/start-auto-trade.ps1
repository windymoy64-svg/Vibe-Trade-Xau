param(
    [int]$BackendPort = 8899,
    [int]$FrontendPort = 5899,
    [switch]$NoBrowser
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
$AgentRoot = Join-Path $ProjectRoot "agent"
$FrontendRoot = Join-Path $ProjectRoot "frontend"
$RuntimeRoot = Join-Path $ProjectRoot ".vibe-dev"
$BackendPidPath = Join-Path $RuntimeRoot "auto-trade-backend.pid"
$FrontendPidPath = Join-Path $RuntimeRoot "auto-trade-frontend.pid"
$BackendLogPath = Join-Path $RuntimeRoot "auto-trade-backend.log"
$BackendErrorLogPath = Join-Path $RuntimeRoot "auto-trade-backend-error.log"
$FrontendLogPath = Join-Path $RuntimeRoot "auto-trade-frontend.log"
$FrontendErrorLogPath = Join-Path $RuntimeRoot "auto-trade-frontend-error.log"

function Test-LocalHttp([string]$Url) {
    try {
        $response = Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec 2
        return $response.StatusCode -ge 200 -and $response.StatusCode -lt 500
    } catch {
        return $false
    }
}

function Get-OwnedProcess([string]$PidPath) {
    $tracked = Get-TrackedProcess $PidPath
    if ($null -ne $tracked) { return $tracked }
    return $null
}

function Get-ProcessCommandLine([int]$ProcessId) {
    try {
        $instance = Get-CimInstance Win32_Process -Filter "ProcessId = $ProcessId" -ErrorAction Stop
        return $instance.CommandLine
    } catch {
        return ""
    }
}

function Test-IsLauncherProcess([int]$ProcessId) {
    $commandLine = Get-ProcessCommandLine $ProcessId
    return $commandLine -match "api_server" -or $commandLine -match "vite"
}

function Assert-PortAvailable([int]$Port, [string]$Name) {
    $listener = Get-NetTCPConnection -LocalAddress "127.0.0.1" -LocalPort $Port -State Listen -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($null -eq $listener) { return }
    $pidPath = if ($Name -eq "Backend") { $BackendPidPath } else { $FrontendPidPath }
    $tracked = Get-OwnProcess $pidPath
    if ($null -ne $tracked -and $tracked.Id -eq $listener.OwningProcess) { return }
    $owner = Get-Process -Id $listener.OwningProcess -ErrorAction SilentlyContinue
    if ($null -ne $owner -and (Test-IsLauncherProcess $owner.Id)) {
        Set-Content -LiteralPath $pidPath -Value $owner.Id -NoNewline
        Write-Host "$Name sudah berjalan (PID $($owner.Id)) dan diadopsi oleh launcher." -ForegroundColor Yellow
        return
    }
    $ownerName = if ($null -ne $owner) { "$($owner.ProcessName) (PID $($owner.Id))" } else { "PID $($listener.OwningProcess)" }
    throw "$Name tidak dapat dimulai: port $Port sedang dipakai oleh $ownerName. Hentikan proses tersebut atau pilih port lain."
}

function Wait-ForHttp([string]$Url, [string]$Name) {
    $deadline = (Get-Date).AddSeconds(45)
    while ((Get-Date) -lt $deadline) {
        if (Test-LocalHttp $Url) { return }
        Start-Sleep -Milliseconds 500
    }
    throw "$Name tidak siap di $Url dalam 45 detik."
}

function Get-TrackedProcess([string]$PidPath) {
    if (-not (Test-Path -LiteralPath $PidPath)) { return $null }
    $pidText = (Get-Content -LiteralPath $PidPath -Raw).Trim()
    if (-not ($pidText -match "^\d+$")) {
        Remove-Item -LiteralPath $PidPath -Force
        return $null
    }
    $process = Get-Process -Id ([int]$pidText) -ErrorAction SilentlyContinue
    if ($null -eq $process) { Remove-Item -LiteralPath $PidPath -Force }
    return $process
}

function Start-TrackedProcess(
    [string]$Name,
    [string]$Executable,
    [string[]]$Arguments,
    [string]$WorkingDirectory,
    [string]$PidPath,
    [string]$LogPath,
    [string]$ErrorLogPath
) {
    $existing = Get-TrackedProcess $PidPath
    if ($null -ne $existing) {
        Write-Host "$Name sudah berjalan (PID $($existing.Id))."
        return $existing
    }
    Remove-Item -LiteralPath $LogPath -Force -ErrorAction SilentlyContinue
    Remove-Item -LiteralPath $ErrorLogPath -Force -ErrorAction SilentlyContinue
    $process = Start-Process -FilePath $Executable -ArgumentList $Arguments -WorkingDirectory $WorkingDirectory -PassThru -RedirectStandardOutput $LogPath -RedirectStandardError $ErrorLogPath
    Set-Content -LiteralPath $PidPath -Value $process.Id -NoNewline
    Write-Host "$Name dimulai (PID $($process.Id))."
    return $process
}

try {
    New-Item -ItemType Directory -Path $RuntimeRoot -Force | Out-Null
    $python = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
    if (-not (Test-Path -LiteralPath $python)) {
        $python = Join-Path $AgentRoot ".venv\Scripts\python.exe"
    }
    if (-not (Test-Path -LiteralPath $python)) {
        throw "Python virtual environment tidak ditemukan. Buat .venv di root proyek atau agent\.venv terlebih dahulu."
    }
    $npm = Get-Command npm.cmd -ErrorAction SilentlyContinue
    if ($null -eq $npm) { throw "npm.cmd tidak ditemukan. Instal Node.js 22 atau lebih baru." }
    $node = Get-Command node.exe -ErrorAction SilentlyContinue
    if ($null -eq $node) { throw "node.exe tidak ditemukan. Instal Node.js 22 atau lebih baru." }
    $viteScript = Join-Path $FrontendRoot "node_modules\vite\bin\vite.js"
    if (-not (Test-Path -LiteralPath $viteScript)) {
        Write-Host "Menginstal dependensi frontend..."
        & $npm.Source install --prefix $FrontendRoot
        if ($LASTEXITCODE -ne 0) { throw "npm install frontend gagal." }
    }
    if (-not (Test-Path -LiteralPath $viteScript)) { throw "Vite tidak ditemukan setelah instalasi frontend." }

    Assert-PortAvailable $BackendPort "Backend"
    Start-TrackedProcess "Backend" $python @("api_server.py", "--host", "127.0.0.1", "--port", "$BackendPort") $AgentRoot $BackendPidPath $BackendLogPath $BackendErrorLogPath | Out-Null
    Wait-ForHttp "http://127.0.0.1:$BackendPort/mt5/auto-trade/status" "Backend"
    Assert-PortAvailable $FrontendPort "Frontend"
    $previousApiUrl = $env:VITE_API_URL
    $env:VITE_API_URL = "http://127.0.0.1:$BackendPort"
    try {
        Start-TrackedProcess "Frontend" $node.Source @("`"$viteScript`"", "--host", "127.0.0.1", "--port", "$FrontendPort") $FrontendRoot $FrontendPidPath $FrontendLogPath $FrontendErrorLogPath | Out-Null
    } finally {
        $env:VITE_API_URL = $previousApiUrl
    }
    Wait-ForHttp "http://127.0.0.1:$FrontendPort/" "Frontend"

    $dashboard = "http://127.0.0.1:$FrontendPort/auto-trade"
    if (-not $NoBrowser) { Start-Process $dashboard }
    Write-Host ""
    Write-Host "Auto Trade siap: $dashboard" -ForegroundColor Green
    Write-Host "Selanjutnya: Settings > isi akun MT5 Demo > Simpan MT5 > Simpan rules > START AUTO TRADE."
    Write-Host "Untuk berhenti: klik stop-auto-trade.cmd"
} catch {
    Write-Host ""
    Write-Host "Startup gagal: $($_.Exception.Message)" -ForegroundColor Red
    if (Test-Path -LiteralPath $BackendErrorLogPath) {
        Write-Host ""
        Write-Host "Backend log terakhir:" -ForegroundColor Yellow
        Get-Content -LiteralPath $BackendErrorLogPath -Tail 25
    }
    exit 1
}
