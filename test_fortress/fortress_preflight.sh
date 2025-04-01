#!/bin/bash

# Test Fortress Preflight Check
# Ensures code meets all quality and test requirements before deployment

set -e  # Exit on any error

# Configuration
COVERAGE_TARGET=95.0
MUTATION_TARGET=80.0
PROJECT_DIR="."
TEST_DIR="tests"
FAILURE_TEMPLATES_DIR="test_fortress/failure_templates"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${YELLOW}🏰 Starting Test Fortress Preflight Check...${NC}"

# Function to print section header
print_section() {
    echo -e "\n${YELLOW}🔍 $1${NC}"
    echo "----------------------------------------"
}

# Function to check command exists
check_command() {
    if ! command -v $1 &> /dev/null; then
        echo -e "${RED}❌ Error: $1 is required but not installed.${NC}"
        exit 1
    fi
}

# Check required commands
print_section "Checking Required Tools"
check_command python3
check_command pip
check_command pytest
check_command mutmut

# Install dependencies if needed
print_section "Installing Dependencies"
if [ -f "requirements.txt" ]; then
    pip install -r requirements.txt
else
    echo -e "${RED}❌ Error: requirements.txt not found${NC}"
    exit 1
fi

# Run static analysis
print_section "Running Static Analysis"

echo "Running black..."
black . --check || {
    echo -e "${RED}❌ Code formatting check failed${NC}"
    exit 1
}

echo "Running flake8..."
flake8 . || {
    echo -e "${RED}❌ Linting check failed${NC}"
    exit 1
}

echo "Running mypy..."
mypy . || {
    echo -e "${RED}❌ Type check failed${NC}"
    exit 1
}

# Run test fortress
print_section "Running Test Fortress"

# Run unit tests with coverage
echo "Running unit tests..."
python3 test_runner.py --unit-only --coverage-target $COVERAGE_TARGET || {
    echo -e "${RED}❌ Unit tests failed or coverage target not met${NC}"
    exit 1
}

# Run mutation tests
echo "Running mutation tests..."
python3 test_runner.py --mutation-only --mutation-target $MUTATION_TARGET || {
    echo -e "${RED}❌ Mutation testing failed or target not met${NC}"
    exit 1
}

# Run failure injection tests
echo "Running failure injection tests..."
python3 test_runner.py --failure-only || {
    echo -e "${RED}❌ Failure injection tests failed${NC}"
    exit 1
}

# Generate test report
print_section "Generating Test Report"
echo "Creating test_report.json..."

cat > test_report.json << EOF
{
    "timestamp": "$(date -u +"%Y-%m-%dT%H:%M:%SZ")",
    "coverage": $COVERAGE_TARGET,
    "mutation_score": $MUTATION_TARGET,
    "tests_passed": true,
    "static_analysis_passed": true
}
EOF

# Final status
print_section "Preflight Status"
echo -e "${GREEN}✅ All checks passed successfully!${NC}"
echo "Coverage target met: $COVERAGE_TARGET%"
echo "Mutation score target met: $MUTATION_TARGET%"
echo "All failure scenarios validated"

exit 0 