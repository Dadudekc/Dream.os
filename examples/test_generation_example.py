#!/usr/bin/env python3
"""
test_generation_example.py

Example demonstrating the TestGeneratorService with feedback-driven test regeneration.
This script shows how to:

1. Generate initial tests for a module
2. Analyze test coverage
3. Regenerate tests based on feedback
4. Track coverage improvements over time
"""

import sys
import os
import logging
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

# Import the TestGeneratorService
from core.services.TestGeneratorService import TestGeneratorService
from core.services.TestCoverageAnalyzer import TestCoverageAnalyzer

# Set up logging
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

def setup_test_environment():
    """Create a simple test module to demonstrate test generation."""
    test_module_path = Path("examples/sample_module.py")
    
    # Create a simple module to test
    sample_code = """
#!/usr/bin/env python3
\"\"\"
Sample module for testing the TestGeneratorService.
\"\"\"

def add(a, b):
    \"\"\"Add two numbers and return the result.\"\"\"
    return a + b

def subtract(a, b):
    \"\"\"Subtract b from a and return the result.\"\"\"
    return a - b

def multiply(a, b):
    \"\"\"Multiply two numbers and return the result.\"\"\"
    return a * b

def divide(a, b):
    \"\"\"Divide a by b and return the result.\"\"\"
    if b == 0:
        raise ValueError("Cannot divide by zero")
    return a / b

class Calculator:
    \"\"\"A simple calculator class.\"\"\"
    
    def __init__(self, initial_value=0):
        \"\"\"Initialize with an optional starting value.\"\"\"
        self.value = initial_value
    
    def add(self, x):
        \"\"\"Add x to the current value.\"\"\"
        self.value += x
        return self.value
    
    def subtract(self, x):
        \"\"\"Subtract x from the current value.\"\"\"
        self.value -= x
        return self.value
    
    def multiply(self, x):
        \"\"\"Multiply the current value by x.\"\"\"
        self.value *= x
        return self.value
    
    def divide(self, x):
        \"\"\"Divide the current value by x.\"\"\"
        if x == 0:
            raise ValueError("Cannot divide by zero")
        self.value /= x
        return self.value
    
    def clear(self):
        \"\"\"Reset the calculator to zero.\"\"\"
        self.value = 0
        return self.value
"""
    
    # Create the module file
    test_module_path.parent.mkdir(exist_ok=True)
    with open(test_module_path, "w") as f:
        f.write(sample_code)
        
    return test_module_path

def main():
    """Main function to demonstrate the TestGeneratorService."""
    print("📝 Test Generation Example")
    print("=========================")
    
    # Setup test environment
    module_path = setup_test_environment()
    print(f"✅ Created sample module: {module_path}")
    
    # Initialize services
    coverage_analyzer = TestCoverageAnalyzer(project_root=".")
    test_generator = TestGeneratorService(
        project_root=".",
        coverage_analyzer=coverage_analyzer
    )
    print("✅ Initialized TestGeneratorService with coverage analyzer")
    
    # Step 1: Generate initial tests
    print("\n🧪 Step 1: Generating initial tests...")
    test_code = test_generator.generate_tests(
        str(module_path), 
        mode="post_implementation"
    )
    
    if test_code:
        print(f"✅ Test skeleton generated successfully")
        
        # Show the first few lines
        print("\nPreview of generated test code:")
        for line in test_code.split("\n")[:10]:
            print(f"  {line}")
        print("  ...")
    else:
        print("❌ Failed to generate test skeleton")
        return
    
    # Step 2: Analyze coverage
    print("\n📊 Step 2: Analyzing test coverage...")
    coverage_report = coverage_analyzer.get_coverage_report(str(module_path))
    
    if "error" not in coverage_report:
        initial_coverage = coverage_report.get("current_coverage", 0)
        print(f"✅ Initial coverage: {initial_coverage}%")
        
        # Show uncovered functions
        print("\nUncovered functions:")
        for func in coverage_report.get("uncovered_functions", []):
            print(f"  - {func}")
    else:
        print(f"❌ Coverage analysis failed: {coverage_report.get('error')}")
    
    # Step 3: Create mock test feedback (simulating failed tests)
    print("\n🔄 Step 3: Simulating test feedback...")
    test_feedback = {
        "success": False,
        "output": """
FAIL: test_divide (test_sample_module.TestSampleModule)
AssertionError: Division test failed

ERROR: test_calculator_divide (test_sample_module.TestSampleModule)
TypeError: Calculator.divide() takes exactly 2 arguments (1 given)
""",
        "failed_tests": [
            "test_divide",
            "test_calculator_divide"
        ]
    }
    print("✅ Created mock test feedback with failing tests")
    
    # Step 4: Regenerate tests based on feedback
    print("\n🔄 Step 4: Regenerating tests based on feedback...")
    updated_test_code = test_generator.regenerate_tests_based_on_feedback(
        str(module_path),
        test_feedback
    )
    
    if updated_test_code:
        print(f"✅ Tests regenerated successfully")
        
        # Show a preview of the update
        print("\nPreview of regenerated test code:")
        for line in updated_test_code.split("\n")[:15]:
            print(f"  {line}")
        print("  ...")
    else:
        print("❌ Failed to regenerate tests")
    
    # Step 5: Analyze coverage trend
    print("\n📈 Step 5: Analyzing coverage trend...")
    trend_analysis = test_generator.analyze_test_coverage_trend(str(module_path))
    
    print(f"✅ Current coverage: {trend_analysis.get('current_coverage', 0)}%")
    print(f"✅ Coverage trend: {trend_analysis.get('trend', 'unknown')}")
    print(f"✅ Generation count: {trend_analysis.get('generation_count', 0)}")
    
    if trend_analysis.get("needs_improvement", False):
        print("⚠️ Test coverage still needs improvement")
    else:
        print("✅ Test coverage is satisfactory")
    
    print("\n🎉 Test generation example complete!")

if __name__ == "__main__":
    main() 
