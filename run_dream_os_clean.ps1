# PowerShell script to run Dream.OS with clean Python paths
$ErrorActionPreference = "Stop"

# Get the script directory
$scriptPath = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $scriptPath

# Clear Python-related environment variables
$env:PYTHONPATH = $scriptPath
$env:PYTHONHOME = ""
$env:CONDA_PREFIX = ""
$env:CONDA_DEFAULT_ENV = ""
$env:CONDA_PYTHON_EXE = ""

# Remove Anaconda from PATH
$env:PATH = ($env:PATH.Split(';') | Where-Object { $_ -notlike "*anaconda3*" }) -join ';'

# Get virtual environment paths
$venvPath = Join-Path $scriptPath "venv"
$pythonExe = Join-Path $venvPath "Scripts\python.exe"
$pipExe = Join-Path $venvPath "Scripts\pip.exe"

Write-Host "Using Python at: $pythonExe"

if (-not (Test-Path $pythonExe)) {
    Write-Error "Python executable not found at: $pythonExe"
    exit 1
}

# Install requirements if needed
if (Test-Path "requirements.txt") {
    Write-Host "Installing requirements..."
    & $pipExe install -r requirements.txt
}

# Run the application
Write-Host "Running Dream.OS..."
& $pythonExe -m interfaces.pyqt 