# PowerShell script to run Dream.OS
$ErrorActionPreference = "Stop"

# Get the script directory
$scriptPath = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $scriptPath

# Activate virtual environment
$venvPath = Join-Path $scriptPath "venv"
$activateScript = Join-Path $venvPath "Scripts\Activate.ps1"

if (Test-Path $activateScript) {
    Write-Host "Activating virtual environment..."
    & $activateScript
} else {
    Write-Error "Virtual environment not found at: $venvPath"
    exit 1
}

# Set PYTHONPATH to include the project root
$env:PYTHONPATH = $scriptPath

# Get Python executable path
$pythonExe = Join-Path $venvPath "Scripts\python.exe"

if (Test-Path $pythonExe) {
    Write-Host "Running Dream.OS..."
    & $pythonExe -m interfaces.pyqt
} else {
    Write-Error "Python executable not found at: $pythonExe"
    exit 1
} 