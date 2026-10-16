# Run Context Atlas UI on 0.0.0.0:8501 (see platform/.streamlit/config.toml).
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$Platform = Join-Path $Root "platform"
$Python = Join-Path $Platform ".venv\Scripts\python.exe"
if (-not (Test-Path $Python)) {
    Write-Error "Create the venv first: cd platform; python -m venv .venv; pip install -e `".[dev]`""
}

Write-Host "Starting Streamlit (LAN + localhost) on port 8501..."
Write-Host "Local:   http://127.0.0.1:8501"
try {
    $ip = (
        Get-NetIPAddress -AddressFamily IPv4 -ErrorAction SilentlyContinue |
        Where-Object { $_.IPAddress -notlike "127.*" -and $_.PrefixOrigin -ne "WellKnown" } |
        Select-Object -First 1 -ExpandProperty IPAddress
    )
    if ($ip) {
        Write-Host "Network: http://${ip}:8501"
    }
} catch {
    Write-Host "Network: use this PC's IPv4 address with port 8501"
}
Write-Host "If others cannot connect, allow inbound TCP 8501 in Windows Defender Firewall."
Write-Host ""

Set-Location $Platform
& (Join-Path $Platform ".venv\Scripts\streamlit.exe") run migrate_framework\ui\app.py
