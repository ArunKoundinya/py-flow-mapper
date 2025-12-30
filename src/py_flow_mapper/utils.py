import ast
import json
from pathlib import Path
from typing import Any, Dict, List, Optional
import sys

def is_stdlib_module(module_name: str) -> bool:
    """Check if a module is from Python standard library."""
    stdlib_paths = [Path(p) for p in sys.path if 'site-packages' not in p and 'dist-packages' not in p]
    
    # Quick check for built-in modules
    if module_name in sys.builtin_module_names:
        return True
    
    # Try to import and check location
    try:
        spec = importlib.util.find_spec(module_name)
        if spec and spec.origin:
            origin_path = Path(spec.origin)
            return any(origin_path.is_relative_to(p) for p in stdlib_paths)
    except (ImportError, AttributeError):
        pass
    
    return False

def extract_docstring(node: ast.AST) -> Optional[str]:
    """Extract docstring from an AST node."""
    if not isinstance(node, (ast.Module, ast.FunctionDef, ast.ClassDef, ast.AsyncFunctionDef)):
        return None
    
    if node.body and isinstance(node.body[0], ast.Expr):
        if isinstance(node.body[0].value, ast.Constant):
            return node.body[0].value.value
    
    return None

def get_function_signature(node: ast.FunctionDef) -> Dict[str, Any]:
    """Extract function signature information."""
    args = []
    
    # Positional arguments
    for arg in node.args.args:
        args.append({
            'name': arg.arg,
            'type': 'arg',
            'annotation': ast.unparse(arg.annotation) if arg.annotation else None
        })
    
    # Default arguments
    defaults = node.args.defaults
    
    # Keyword-only arguments
    for arg in node.args.kwonlyargs:
        args.append({
            'name': arg.arg,
            'type': 'kwarg',
            'annotation': ast.unparse(arg.annotation) if arg.annotation else None
        })
    
    # Vararg and kwarg
    if node.args.vararg:
        args.append({
            'name': node.args.vararg.arg,
            'type': 'vararg',
            'annotation': ast.unparse(node.args.vararg.annotation) if node.args.vararg.annotation else None
        })
    
    if node.args.kwarg:
        args.append({
            'name': node.args.kwarg.arg,
            'type': 'kwarg',
            'annotation': ast.unparse(node.args.kwarg.annotation) if node.args.kwarg.annotation else None
        })
    
    # Return annotation
    return_annotation = ast.unparse(node.returns) if node.returns else None
    
    return {
        'args': args,
        'return_annotation': return_annotation
    }

def format_module_name(file_path: Path, base_path: Path) -> str:
    """Format file path as Python module name."""
    rel_path = file_path.relative_to(base_path)
    module_name = str(rel_path).replace('.py', '').replace('/', '.').replace('\\', '.')
    
    if module_name.endswith('.__init__'):
        module_name = module_name[:-9]
    
    return module_name

def find_entry_point(base_path: Path) -> Optional[str]:
    """Find the entry point of a Python project."""
    possible_entry_points = ['main.py', '__main__.py', 'app.py', 'run.py']
    
    for entry_point in possible_entry_points:
        if (base_path / entry_point).exists():
            return entry_point
    
    # Check for setup.py or pyproject.toml
    if (base_path / 'setup.py').exists():
        with open(base_path / 'setup.py', 'r') as f:
            content = f.read()
            if '__main__' in content or 'main()' in content:
                return 'setup.py'
    
    return None

def save_json(data: Any, file_path: Path, indent: int = 2):
    """Save data as JSON with proper formatting."""
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=indent, ensure_ascii=False, default=str)

def load_json(file_path: Path) -> Any:
    """Load JSON data from file."""
    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)

def get_project_structure(base_path: Path, exclude_dirs: List[str] = None) -> Dict[str, Any]:
    """Get the project directory structure."""
    if exclude_dirs is None:
        exclude_dirs = [
            "venv", ".venv", "env", ".env", "virtualenv",
            "__pycache__", ".mypy_cache", ".pytest_cache", ".ruff_cache",
            ".coverage", "htmlcov",
            ".git", ".hg", ".svn",
            ".idea", ".vscode", ".DS_Store", "__MACOSX",
            "build", "dist", ".eggs", ".tox", ".nox",
            "node_modules", "site-packages",
            "docs", "doc", "notebooks", ".ipynb_checkpoints",
            "models", "outputs", "results",
            "logs", "tmp", "temp",
        ]

    exclude_set = set(exclude_dirs)
    structure: Dict[str, Any] = {}

    for item in sorted(base_path.iterdir(), key=lambda p: p.name):
        name = item.name

        # Unified exclusion logic (works for both files and dirs)
        if (
            name in exclude_set
            or name.endswith(".egg-info")                          # e.g., mypkg.egg-info
            or any(name.startswith(excl) for excl in exclude_set)  # e.g., venv311, build_temp
        ):
            continue

        if item.is_dir():
            structure[name] = get_project_structure(item, exclude_dirs)
        else:
            structure[name] = "file"

    return structure
