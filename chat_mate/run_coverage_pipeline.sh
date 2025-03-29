#!/bin/bash
# Bash script to run the complete test coverage pipeline
# Usage: ./run_coverage_pipeline.sh [--threshold=<percentage>] [--visualize] [--auto-generate]

# Default values
THRESHOLD=70
VISUALIZE=false
AUTO_GENERATE=false
USE_OLLAMA=false
MODULE=""
MOCK_DATA=false

# Parse command line arguments
for arg in "$@"; do
    case $arg in
        --threshold=*)
            THRESHOLD="${arg#*=}"
            ;;
        --visualize)
            VISUALIZE=true
            ;;
        --auto-generate)
            AUTO_GENERATE=true
            ;;
        --use-ollama)
            USE_OLLAMA=true
            ;;
        --module=*)
            MODULE="${arg#*=}"
            ;;
        --mock-data)
            MOCK_DATA=true
            ;;
        *)
            echo "Unknown argument: $arg"
            echo "Usage: ./run_coverage_pipeline.sh [--threshold=<percentage>] [--visualize] [--auto-generate] [--use-ollama] [--module=<name>] [--mock-data]"
            exit 1
            ;;
    esac
done

# Configuration
PROJECT_ROOT=$(pwd)
REPORTS_DIR="$PROJECT_ROOT/reports/coverage"

# Create reports directory if it doesn't exist
mkdir -p "$REPORTS_DIR"

# Helper function to print section headers
print_section() {
    echo -e "\n\033[1;36m=========================================="
    echo -e " $1"
    echo -e "==========================================\033[0m"
}

# Check if required Python packages are installed
print_section "CHECKING DEPENDENCIES"
required_packages=("pytest" "pytest-cov" "tabulate" "matplotlib")
for package in "${required_packages[@]}"; do
    if ! python -m pip show "$package" &> /dev/null; then
        echo -e "\033[1;33mInstalling $package...\033[0m"
        python -m pip install "$package"
    else
        echo -e "\033[1;32m$package is already installed.\033[0m"
    fi
done

# Step 1: Run existing tests and measure coverage
print_section "STEP 1: Running existing tests with coverage"
if ! python -m pytest --cov=chat_mate --cov-report=term --cov-report=html:"$REPORTS_DIR" tests/; then
    echo -e "\033[1;31mError running tests\033[0m"
    if [ "$MOCK_DATA" = false ]; then
        read -p "Would you like to continue with mock data? (y/n) " choice
        if [ "$choice" != "y" ]; then
            echo -e "\033[1;31mExiting coverage pipeline.\033[0m"
            exit 1
        fi
        MOCK_DATA=true
    fi
fi

# Step 2: Analyze coverage
print_section "STEP 2: Analyzing test coverage"
VISUALIZE_ARG=""
if $VISUALIZE; then
    VISUALIZE_ARG="--visualize"
fi

MOCK_DATA_ARG=""
if $MOCK_DATA; then
    MOCK_DATA_ARG="--mock-data"
fi

python analyze_test_coverage.py --threshold="$THRESHOLD" $VISUALIZE_ARG $MOCK_DATA_ARG

# If using mock data, we can skip the next step if no module specified
if $MOCK_DATA && [ -z "$MODULE" ]; then
    print_section "STEP 3: Skipping file analysis in mock data mode"
else
    # Step 3: Identify files without tests
    print_section "STEP 3: Identifying files without tests"
    AUTO_GEN_ARG=""
    if $AUTO_GENERATE; then
        AUTO_GEN_ARG="--auto-generate"
    fi

    OLLAMA_ARG=""
    if $USE_OLLAMA; then
        OLLAMA_ARG="--use-ollama"
    fi

    MODULE_ARG=""
    if [ -n "$MODULE" ]; then
        MODULE_ARG="--module=$MODULE"
    fi

    python generate_missing_tests.py $AUTO_GEN_ARG --run-tests $OLLAMA_ARG $MODULE_ARG
fi

# Step 4: Run overnight test generator if requested
if $USE_OLLAMA && ! $MOCK_DATA; then
    print_section "STEP 4: Running overnight test generator"
    COVERAGE_ONLY_ARG="--coverage-only"
    
    if [ -n "$MODULE" ]; then
        python overnight_test_generator.py $COVERAGE_ONLY_ARG --module="$MODULE"
    else
        python overnight_test_generator.py $COVERAGE_ONLY_ARG
    fi
fi

# Step 5: Provide summary
print_section "TEST COVERAGE SUMMARY"
echo -e "\033[1;32mCoverage report directory: $REPORTS_DIR\033[0m"
echo -e "\033[1;32mCoverage dashboard: $REPORTS_DIR/index.html\033[0m"

if $VISUALIZE; then
    echo -e "\033[1;32mVisualizations: $REPORTS_DIR/visualizations/\033[0m"
fi

if $MOCK_DATA; then
    echo -e "\n\033[1;33mNOTE: Coverage data was generated using mock values.\033[0m"
    echo -e "\033[1;33mThis is for visualization purposes only and does not reflect actual code coverage.\033[0m"
fi

# Open the coverage report in the default browser
if [ -f "$REPORTS_DIR/index.html" ]; then
    read -p "Would you like to open the coverage report? (y/n) " choice
    if [ "$choice" = "y" ]; then
        if [ "$(uname)" == "Darwin" ]; then
            # macOS
            open "$REPORTS_DIR/index.html"
        elif [ "$(expr substr $(uname -s) 1 5)" == "Linux" ]; then
            # Linux
            if [ -n "$(command -v xdg-open)" ]; then
                xdg-open "$REPORTS_DIR/index.html"
            else
                echo "Could not detect a method to open the browser. Please open $REPORTS_DIR/index.html manually."
            fi
        fi
    fi
fi

echo -e "\n\033[1;32mCoverage pipeline complete!\033[0m"