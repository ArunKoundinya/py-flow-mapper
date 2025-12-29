import os
import sys
from pathlib import Path

# Add the src directory to Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..","..", "src")))

from py_flow_mapper.analyzer import ProjectAnalyzer
from py_flow_mapper.mermaid_generator import MermaidGenerator


def create_flow_test_project():
    """Create a test project that demonstrates flow analysis."""
    test_project_dir = Path(__file__).parent / "flow_test_project"
    test_project_dir.mkdir(exist_ok=True)
    
    # Create main.py with clear flow
    main_content = '''
"""Main module showing data flow."""

from .utils import helper_function
from .calculator import Calculator
import json

def main_final():
    """Main entry point - shows data flow between functions."""
    print("Starting the application...")
    
    # Call helper function and store result
    result = helper_function("test")
    print(f"Helper result: {result}")
    
    # Use calculator - chain of calls
    calc = Calculator()
    total = calc.add(5, 3)
    print(f"5 + 3 = {total}")
    
    # Process the result from helper_function
    processed = process_data(result)
    print(f"Processed data: {processed}")
    
    # Chain another call
    final_result = finalize(processed, total)
    
    return final_result

def process_data(data):
    """Process data from helper_function."""
    return data.upper()

def finalize(data, number):
    """Final processing combining multiple inputs."""
    return f"{data}_{number}"

if __name__ == "__main__":
    main()
'''
    
    with open(test_project_dir / "main.py", "w") as f:
        f.write(main_content)
    
    # Create utils.py
    utils_content = '''
"""Utility functions."""

def helper_function(name):
    """Helper function that returns a formatted string."""
    result = format_name(name)
    return f"Hello, {result}!"

def format_name(name):
    """Format the name."""
    return name.title()

def another_helper(x, y):
    """Another helper."""
    return x * y
'''
    
    with open(test_project_dir / "utils.py", "w") as f:
        f.write(utils_content)
    
    # Create calculator.py
    calculator_content = '''
"""Calculator module."""

class Calculator:
    """A simple calculator."""
    
    def __init__(self):
        self.history = []
    
    def add(self, a, b):
        """Add two numbers."""
        result = self._actual_add(a, b)
        self.history.append(f"add: {a} + {b} = {result}")
        return result
    
    def _actual_add(self, a, b):
        """Actual addition implementation."""
        return a + b
    
    def multiply(self, a, b):
        """Multiply two numbers."""
        return a * b

def create_calculator():
    """Factory function."""
    return Calculator()
'''
    
    with open(test_project_dir / "calculator.py", "w") as f:
        f.write(calculator_content)
    
    # Create __init__.py
    with open(test_project_dir / "__init__.py", "w") as f:
        f.write('"""Flow test project."""')
    
    print(f"✓ Test project created at: {test_project_dir}")
    return test_project_dir


def test_flow_analysis():
    """Test the flow analysis functionality."""
    print("=" * 60)
    print("Testing Flow Analysis")
    print("=" * 60)
    
    # Create test project
    project_dir = create_flow_test_project()
    
    # Analyze with enhanced analyzer
    analyzer = ProjectAnalyzer(base_path=str(project_dir), entry_point="main.py")
    metadata = analyzer.analyze()
    
    print("\n✓ Analysis Complete")
    print(f"\nFlow Analysis Results:")
    
    # Generate flow graph
    meta_file = project_dir / "project_meta.json"
    generator = MermaidGenerator(meta_file)
    
    print("\n" + "=" * 60)
    print("Generating Flow Diagrams")
    print("=" * 60)
    
    # Also generate detailed flow
    _ = generator.generate_detailed_flow_graph()
    
    # Show the generated flow graph
    print("\nGenerated Flow Graph (flow_graph.mmd):")
    flow_file = project_dir / "flow_graph.mmd"
    if flow_file.exists():
        with open(flow_file, 'r') as f:
            content = f.read()
            print(content[:500] + "..." if len(content) > 500 else content)
    
    return metadata, project_dir



def main():
    """Main test function."""
    print("PyFlowMapper - Flow Analysis Test")
    print("=" * 60)
    
    try:
        # Test the flow analysis
        metadata, project_dir = test_flow_analysis()
        
        # Show expected output        
        print("\n" + "=" * 60)
        print("Test Complete!")
        print("=" * 60)
        
        print(f"\nProject analyzed: {project_dir}")
        print(f"Metadata: {project_dir / 'project_meta.json'}")
        print(f"Flow graph: {project_dir / 'flow_graph.mmd'}")
        
        print("\nTo view the flow graph:")
        print("1. Copy the content from flow_graph.mmd")
        print("2. Paste at https://mermaid.live/")
        print("3. Or use VS Code with Mermaid extension")
        
    except Exception as e:
        print(f"\nError during testing: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())