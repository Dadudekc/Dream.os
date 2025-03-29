# PowerShell script to run the complete test coverage pipeline
# Usage: .\run_coverage_pipeline.ps1 [--threshold=<percentage>] [--visualize] [--auto-generate]

param (
    [int]$threshold = 70,
    [switch]$visualize = $false,
    [switch]$autoGenerate = $false,
    [switch]$useOllama = $false,
    [string]$module = "",
    [switch]$mockData = $false
)

# Configuration
$PROJECT_ROOT = Get-Location
$REPORTS_DIR = Join-Path $PROJECT_ROOT "reports/coverage"
$MIN_COVERAGE = $threshold

# Create reports directory if it doesn't exist
if (-not (Test-Path $REPORTS_DIR)) {
    New-Item -ItemType Directory -Path $REPORTS_DIR -Force | Out-Null
}

# Helper function to print section headers
function Print-Section {
    param ([string]$title)
    Write-Host "`n==========================================" -ForegroundColor Cyan
    Write-Host " $title" -ForegroundColor Cyan
    Write-Host "==========================================" -ForegroundColor Cyan
}

# Check if required Python packages are installed
Print-Section "CHECKING DEPENDENCIES"
$requiredPackages = @("pytest", "pytest-cov", "tabulate", "matplotlib")
foreach ($package in $requiredPackages) {
    $checkCmd = "pip show $package"
    $result = Invoke-Expression $checkCmd
    if (-not $result) {
        Write-Host "Installing $package..." -ForegroundColor Yellow
        Invoke-Expression "pip install $package"
    } else {
        Write-Host "$package is already installed." -ForegroundColor Green
    }
}

# Step 1: Run existing tests and measure coverage
Print-Section "STEP 1: Running existing tests with coverage"
$testResult = $null
try {
    $testResult = python -m pytest --cov=chat_mate --cov-report=term --cov-report=html:$REPORTS_DIR tests/
}
catch {
    Write-Host "Error running tests: $_" -ForegroundColor Red
    if (-not $mockData) {
        $choice = Read-Host "Would you like to continue with mock data? (y/n)"
        if ($choice -ne "y") {
            Write-Host "Exiting coverage pipeline." -ForegroundColor Red
            exit 1
        }
        $mockData = $true
    }
}

# Step 2: Analyze coverage
Print-Section "STEP 2: Analyzing test coverage"
$visualizeArg = if ($visualize) { "--visualize" } else { "" }
$mockDataArg = if ($mockData) { "--mock-data" } else { "" }
python analyze_test_coverage.py --threshold=$MIN_COVERAGE $visualizeArg $mockDataArg

# If using mock data, we can skip the next step if no module specified
if ($mockData -and -not $module) {
    Print-Section "STEP 3: Skipping file analysis in mock data mode"
} else {
    # Step 3: Identify files without tests
    Print-Section "STEP 3: Identifying files without tests"
    $autoGenArg = if ($autoGenerate) { "--auto-generate" } else { "" }
    $ollamaArg = if ($useOllama) { "--use-ollama" } else { "" }
    $moduleArg = if ($module) { "--module=$module" } else { "" }

    python generate_missing_tests.py $autoGenArg --run-tests $ollamaArg $moduleArg
}

# Step 4: Run overnight test generator if requested
if ($useOllama -and -not $mockData) {
    Print-Section "STEP 4: Running overnight test generator"
    $coverageOnlyArg = "--coverage-only"
    
    if ($module) {
        python overnight_test_generator.py $coverageOnlyArg --module=$module
    } else {
        python overnight_test_generator.py $coverageOnlyArg
    }
}

# Step 5: Provide summary
Print-Section "TEST COVERAGE SUMMARY"
Write-Host "Coverage report directory: $REPORTS_DIR" -ForegroundColor Green
Write-Host "Coverage dashboard: $REPORTS_DIR\index.html" -ForegroundColor Green

if ($visualize) {
    Write-Host "Visualizations: $REPORTS_DIR\visualizations\" -ForegroundColor Green
}

if ($mockData) {
    Write-Host "`nNOTE: Coverage data was generated using mock values." -ForegroundColor Yellow
    Write-Host "This is for visualization purposes only and does not reflect actual code coverage." -ForegroundColor Yellow
}

# Open the coverage report in the default browser
if (Test-Path "$REPORTS_DIR\index.html") {
    $choice = Read-Host "Would you like to open the coverage report? (y/n)"
    if ($choice -eq "y") {
        Start-Process "$REPORTS_DIR\index.html"
    }
}

Write-Host "`nCoverage pipeline complete!" -ForegroundColor Green 