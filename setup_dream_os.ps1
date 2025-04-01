# PowerShell script to set up Dream.OS environment
$ErrorActionPreference = "Stop"

# Get the script directory
$scriptPath = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $scriptPath

Write-Host "Setting up Dream.OS environment..."

# Function to check if Python is installed
function Find-Python {
    try {
        $pythonPath = Get-Command python -ErrorAction SilentlyContinue
        if ($pythonPath) {
            $version = & python -V 2>&1
            Write-Host "Found Python: $version at $($pythonPath.Source)"
            return $pythonPath.Source
        }
    }
    catch {
        Write-Host "Error checking Python: $_"
    }
    return $null
}

# Function to create and activate virtual environment
function Setup-VirtualEnv {
    try {
        # Remove existing venv if it exists
        if (Test-Path "venv") {
            Write-Host "Removing existing virtual environment..."
            Remove-Item -Recurse -Force "venv"
        }

        # Create new virtual environment
        Write-Host "Creating new virtual environment..."
        python -m venv venv

        # Activate virtual environment
        Write-Host "Activating virtual environment..."
        .\venv\Scripts\Activate.ps1

        # Upgrade pip
        Write-Host "Upgrading pip..."
        python -m pip install --upgrade pip

        # Install requirements
        Write-Host "Installing requirements..."
        pip install -r requirements.txt

        # Install package in development mode
        Write-Host "Installing package in development mode..."
        pip install -e .

        return $true
    }
    catch {
        Write-Host "Error setting up virtual environment: $_"
        return $false
    }
}

# Function to run the application
function Run-DreamOS {
    try {
        Write-Host "Starting Dream.OS..."
        python -m interfaces.pyqt
    }
    catch {
        Write-Host "Error running Dream.OS: $_"
        return $false
    }
}

# Main script
try {
    # Check Python installation
    $pythonPath = Find-Python
    if (-not $pythonPath) {
        throw "Python not found. Please install Python 3.11 or later."
    }

    # Setup virtual environment and install dependencies
    if (-not (Setup-VirtualEnv)) {
        throw "Failed to set up virtual environment."
    }

    # Run the application
    Run-DreamOS
}
catch {
    Write-Host "Error: $_" -ForegroundColor Red
    exit 1
} 