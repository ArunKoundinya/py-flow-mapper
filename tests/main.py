import os
import sys
from pathlib import Path

# Add the src directory to Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))

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

def main():
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
    
    # Show function map with return assignments
    function_map = metadata.get('function_map', {})
    print(f"\nFunctions with Return Value Flow:")
    
    for func_name, func_info in function_map.items():
        if func_info.get('return_assignments'):
            print(f"\n{func_name}:")
            for var, calls in func_info['return_assignments'].items():
                print(f"  {var} ← {calls}")
    
    # Show data flow edges
    data_flow = metadata.get('data_flow_edges', [])
    if data_flow:
        print(f"\nData Flow Edges ({len(data_flow)} found):")
        for edge in data_flow:
            print(f"  {edge['source']} --[{edge['variable']}]--> {edge['target']}")
    
    # Generate flow graph
    meta_file = project_dir / "project_meta.json"
    generator = MermaidGenerator(meta_file)
    
    print("\n" + "=" * 60)
    print("Generating Flow Diagrams")
    print("=" * 60)
    
    # Generate the flow graph you wanted
    flow_graph = generator.generate_flow_graph()
    
    # Also generate detailed flow
    detailed_graph = generator.generate_detailed_flow_graph()
    
    # Show the generated flow graph
    print("\nGenerated Flow Graph (flow_graph.mmd):")
    flow_file = project_dir / "flow_graph.mmd"
    if flow_file.exists():
        with open(flow_file, 'r') as f:
            content = f.read()
            print(content[:500] + "..." if len(content) > 500 else content)
    
    return metadata, project_dir


def show_expected_output():
    """Show the expected output format."""
    print("\n" + "=" * 60)
    print("Expected Output Format")
    print("=" * 60)
    
    expected = '''graph TD
    main.main[main]
    main.process_data
    utils.helper_function
    calculator.add
    main.main --> utils.helper_function
    main.main --> calculator.add
    utils.helper_function --[result]--> main.process_data'''
    
    print("\nThe analyzer should produce graphs like this:")
    print(expected)
    
    print("\nKey features:")
    print("1. Shows which functions call which other functions")
    print("2. Shows how return values flow between functions")
    print("3. Uses dotted/dashed lines for data flow")
    print("4. Labels edges with variable names")


def main():
    """Main test function."""
    print("PyFlowMapper - Flow Analysis Test")
    print("=" * 60)
    
    try:
        # Test the flow analysis
        metadata, project_dir = test_flow_analysis()
        
        # Show expected output
        show_expected_output()
        
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