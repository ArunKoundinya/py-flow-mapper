import argparse
from pathlib import Path
import sys
from typing import Optional

from .analyzer import ProjectAnalyzer
from .mermaid_generator import MermaidGenerator
from .utils import get_project_structure
from . import __version__,__author__,__github__,__gitpages__

def main():
    parser = argparse.ArgumentParser(
        description="Python Project Flow Mapper - Analyze and visualize Python project structure and dependencies"
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Commands')
    
    # Analyze command
    analyze_parser = subparsers.add_parser('analyze', help='Analyze a Python project')
    analyze_parser.add_argument('path', type=str, help='Path to the project directory')
    analyze_parser.add_argument('--entry-point', type=str, default=None, 
                               help='Entry point file (default: auto-detect)')
    
    # Generate diagrams command
    diagram_parser = subparsers.add_parser('diagram', help='Generate diagrams from metadata')
    diagram_parser.add_argument('metadata', type=str, help='Path to metadata JSON file')
    # https://github.com/ArunKoundinya/py-flow-mapper/issues/1 : forced external
    diagram_parser.add_argument( "--include-external", type=str, default="",
                                help="Comma-separated list of external libraries to include in diagrams"
                                )

    # Structure command
    struct_parser = subparsers.add_parser('structure', help='Show project structure')
    struct_parser.add_argument('path', type=str, help='Path to the project directory')
    
    # Version command
    subparsers.add_parser('version', help='Show version information')
    
    args = parser.parse_args()
    
    if args.command == 'analyze':
        analyze_project(args)
    elif args.command == 'diagram':
        generate_diagrams(args)
    elif args.command == 'structure':
        show_structure(args)
    elif args.command == 'version':
        print(f"PyFlowMapper v{__version__}")
        print(f"Author for this Package: {__author__}")
        print(f"GitHub:{__github__}")
        print(f"Help Documents: {__gitpages__}")

    else:
        parser.print_help()

def analyze_project(args):
    """Analyze a Python project and generate metadata."""
    project_path = Path(args.path).resolve()
    
    if not project_path.exists():
        print(f"Error: Path '{args.path}' does not exist")
        sys.exit(1)
    
    print(f"Analyzing project at: {project_path}")
    
    analyzer = ProjectAnalyzer(
        base_path=str(project_path),
        entry_point=args.entry_point or 'main.py'
    )
    
    try:
        metadata = analyzer.analyze()
        
        print("\nAnalysis Complete!")
        print(f"  Modules: {len(metadata['modules'])}")
        print(f"  Functions: {metadata['project']['total_functions']}")
        print(f"  Classes: {metadata['project']['total_classes']}")
        print(f"  External Dependencies: {len(metadata['dependencies']['external'])}")
        print(f"\nMetadata saved to: {project_path / 'project_meta.json'}")
        
        # List top dependencies
        if metadata['dependencies']['external']:
            print("\nTop External Dependencies:")
            for dep in metadata['dependencies']['external'][:10]:
                print(f"  - {dep}")
            if len(metadata['dependencies']['external']) > 10:
                print(f"  ... and {len(metadata['dependencies']['external']) - 10} more")
        
    except Exception as e:
        print(f"Error during analysis: {e}")
        sys.exit(1)

def generate_diagrams(args):
    """Generate Mermaid diagrams from metadata."""
    metadata_path = Path(args.metadata).resolve()
    
    if not metadata_path.exists():
        print(f"Error: Metadata file '{args.metadata}' does not exist")
        sys.exit(1)
    
    print(f"Generating diagrams from: {metadata_path}")
    
    generator = MermaidGenerator(metadata_path,include_external=args.include_external)
    
    try:    
        master_path = generator.generate_all_diagrams()
        print(f"\nAll diagrams generated in: {master_path}")
        
        print("\nDiagrams are ready! You can view them:")
        print("1. Copy the content to Mermaid Live Editor: https://mermaid.live/")
        print("2. Use VS Code with Mermaid extension")
        print("3. Use GitHub/Markdown viewers that support Mermaid")
        
    except Exception as e:
        print(f"Error generating diagrams: {e}")
        sys.exit(1)

def show_structure(args):
    """Display project structure."""
    project_path = Path(args.path).resolve()
    
    if not project_path.exists():
        print(f"Error: Path '{args.path}' does not exist")
        sys.exit(1)
    
    print(f"Project Structure: {project_path}\n")
    
    def print_tree(data, prefix=""):
        items = list(data.items())
        for i, (key, value) in enumerate(items):
            is_last = i == len(items) - 1
            connector = "└── " if is_last else "├── "
            print(prefix + connector + key)
            
            if isinstance(value, dict):
                extension = "    " if is_last else "│   "
                print_tree(value, prefix + extension)
    
    structure = get_project_structure(project_path)
    print_tree(structure)

if __name__ == "__main__":
    main()