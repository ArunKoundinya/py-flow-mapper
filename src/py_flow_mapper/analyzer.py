import os
import ast
import json
import importlib.util
from typing import Dict, List, Set, Optional, Any, Tuple
from dataclasses import dataclass, asdict, field
from pathlib import Path
import sys

@dataclass
class DataFlowEdge:
    """Represents data flow between functions."""
    target: str  # Target function (full name)
    source: str  # Source function (full name)
    variable: str  # Variable name being passed
    value_type: str = "return_value"  # Can be "return_value", "parameter", "variable"

@dataclass
class FunctionInfo:
    """Information about a single function."""
    name: str
    module: str
    file_path: str
    lineno: int
    calls: List[str]  # Function names this function directly calls
    called_by: List[str]  # Functions that call this function
    return_variable: Optional[str] = None  # Variable name that stores return value
    returns_to: List[str] = field(default_factory=list)  # Functions that receive this return value
    parameters: List[Tuple[str, str]] = field(default_factory=list)  # (name, type)
    is_async: bool = False
    decorators: List[str] = field(default_factory=list)
    docstring: Optional[str] = None
    return_assignments: Dict[str, List[str]] = field(default_factory=dict)  # {var_name: [called_functions]}
    call_arguments: Dict[str, List[str]] = field(default_factory=dict)
    
    def __post_init__(self):
        if self.decorators is None:
            self.decorators = []

@dataclass 
class ClassInfo:
    """Information about a single class."""
    name: str
    module: str
    file_path: str
    lineno: int
    methods: List[FunctionInfo]
    bases: List[str] = field(default_factory=list)
    decorators: List[str] = field(default_factory=list)
    
    def __post_init__(self):
        if self.bases is None:
            self.bases = []
        if self.decorators is None:
            self.decorators = []

@dataclass
class ModuleInfo:
    """Information about a Python module."""
    name: str
    file_path: str
    relative_path: str
    functions: List[FunctionInfo]
    classes: List[ClassInfo]
    imports: List[str]
    internal_imports: List[str]
    external_imports: List[str]
    import_mapping: Dict[str, str] = field(default_factory=dict)  # alias -> actual module

class ProjectAnalyzer:
    """Analyzes Python projects to create dependency and call graphs with data flow."""
    
    def __init__(self, base_path: str, entry_point: str = "main.py"):
        self.base_path = Path(base_path).resolve()
        self.entry_point = entry_point
        self.modules: Dict[str, ModuleInfo] = {}
        self.function_map: Dict[str, FunctionInfo] = {}
        self.class_map: Dict[str, ClassInfo] = {}
        self.data_flow_edges: List[DataFlowEdge] = []
        self.project_name = self.base_path.name
        
    def analyze(self) -> Dict[str, Any]:
        """Main analysis entry point with enhanced data flow tracking."""
        print(f"Analyzing project: {self.project_name}")
        print(f"Base path: {self.base_path}")
        
        # Find all Python files
        python_files = self._find_python_files()
        print(f"Found {len(python_files)} Python files")
        
        # First pass: Analyze each file to build basic structure
        for file_path in python_files:
            self._analyze_file(file_path)
        
        # Second pass: Build detailed call and data flow relationships
        self._build_data_flow_graph()
        
        # Generate metadata
        metadata = self._generate_metadata()
        
        # Save to JSON
        self._save_metadata(metadata)
        
        return metadata
    
    def _find_python_files(self) -> List[Path]:
        """Find all Python files in the project, excluding virtual environments and other unwanted directories."""
        python_files = []
        
        # Prefixes of directories to exclude        
        exclude_prefixes = (
            "venv", ".venv", "env", ".env", "virtualenv", ".virtualenv",
            "__pycache__", ".mypy_cache", ".pytest_cache", ".ruff_cache",
            ".coverage", "htmlcov", ".hypothesis",
            ".git", ".hg", ".svn",
            "build", "dist", ".eggs", "egg-info", "*.egg-info",
            ".tox", ".nox", ".pdm-build",
            "site-packages", "node_modules", "bower_components",
            "docs", "doc", "site", "_site", "mkdocs",
            ".ipynb_checkpoints", "notebooks", "examples", "experiments", "scratch",
            "data", "datasets", "models", "checkpoints", "outputs", "results",
            "logs", "tmp", "temp", "cache",
            ".idea", ".vscode", ".DS_Store", "__MACOSX",
            ".github", ".gitlab", ".circleci",
            "tests", "test", "testing",
            )

        
        for root, dirs, files in os.walk(self.base_path):
            # Filter out directories that start with any of the exclude prefixes
            dirs[:] = [d for d in dirs if not d.startswith(exclude_prefixes)]
            
            for file in files:
                if file.endswith('.py'):
                    file_path = Path(root) / file
                    python_files.append(file_path)
        
        return python_files
    
    def _analyze_file(self, file_path: Path):
        """Analyze a single Python file with enhanced data flow tracking."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            tree = ast.parse(content, filename=str(file_path))
            rel_path = file_path.relative_to(self.base_path)
            module_name = self._path_to_module_name(rel_path)
            
            # Create visitors
            visitor = ModuleVisitor(file_path, module_name, self.base_path)
            visitor.visit(tree)
            
            # Store module info
            self.modules[module_name] = ModuleInfo(
                name=module_name,
                file_path=str(file_path),
                relative_path=str(rel_path),
                functions=visitor.functions,
                classes=visitor.classes,
                imports=visitor.imports,
                internal_imports=visitor.internal_imports,
                external_imports=visitor.external_imports,
                import_mapping=visitor.import_mapping
            )
            
            # Add to function map with enhanced tracking
            for func in visitor.functions:
                func_key = f"{module_name}.{func.name}"
                # Track return assignments from visitor
                if hasattr(visitor, 'function_return_assignments'):
                    func.return_assignments = visitor.function_return_assignments.get(func.name, {})
                self.function_map[func_key] = func
            
            for cls in visitor.classes:
                cls_key = f"{module_name}.{cls.name}"
                self.class_map[cls_key] = cls
                
        except (SyntaxError, UnicodeDecodeError) as e:
            print(f"Warning: Could not parse {file_path}: {e}")
    
    def _path_to_module_name(self, rel_path: Path) -> str:
        """Convert file path to Python module name."""
        module_name = str(rel_path).replace('.py', '').replace('/', '.').replace('\\', '.')
        if module_name.endswith('.__init__'):
            module_name = module_name[:-9]
        return module_name
    
    def _build_data_flow_graph(self):
        # Call relationships
        for caller_key, caller_func in self.function_map.items():
            for call in caller_func.calls:
                callee_key = self._resolve_function_name(call, caller_func.module)
                if callee_key and callee_key in self.function_map:
                    if caller_key not in self.function_map[callee_key].called_by:
                        self.function_map[callee_key].called_by.append(caller_key)

        # Data flow
        for func_key, func in self.function_map.items():
            for var, called_funcs in func.return_assignments.items():
                for called_func in called_funcs:
                    callee_key = self._resolve_function_name(called_func, func.module)
                    if callee_key:
                        self.data_flow_edges.append(
                            DataFlowEdge(
                                source=callee_key,
                                target=func_key,
                                variable=var
                            )
                        )

    
    def _resolve_function_name(self, func_name: str, current_module: str) -> Optional[str]:
        """Resolve a function name to its full qualified name."""
        # Check if it's already a fully qualified name
        # Fully qualified already
        if '.' in func_name:
            return func_name if func_name in self.function_map else None

        # Direct function in same module
        candidate = f"{current_module}.{func_name}"
        if candidate in self.function_map:
            return candidate

        # Search globally (methods included)
        for full_name in self.function_map:
            if full_name.endswith(f".{func_name}"):
                return full_name

        # Imported symbol
        if current_module in self.modules:
            imports = self.modules[current_module].import_mapping
            if func_name in imports:
                return imports[func_name]

        return None

    
    def _generate_metadata(self) -> Dict[str, Any]:
        """Generate comprehensive metadata dictionary with data flow."""
        serialized_modules = {}
        for module_name, module_info in self.modules.items():
            serialized_modules[module_name] = {
                'file_path': module_info.file_path,
                'relative_path': module_info.relative_path,
                'functions': [
                    {
                        'name': func.name,
                        'lineno': func.lineno,
                        'calls': func.calls,
                        'called_by': func.called_by,
                        'returns_to': func.returns_to,
                        'return_assignments': func.return_assignments,
                        'is_async': func.is_async,
                        'decorators': func.decorators,
                        'docstring': func.docstring
                    }
                    for func in module_info.functions
                ],
                'classes': [
                    {
                        'name': cls.name,
                        'lineno': cls.lineno,
                        'bases': cls.bases,
                        'decorators': cls.decorators,
                        'methods': [
                            {
                                'name': method.name,
                                'lineno': method.lineno,
                                'calls': method.calls
                            }
                            for method in cls.methods
                        ]
                    }
                    for cls in module_info.classes
                ],
                'imports': module_info.imports,
                'internal_imports': module_info.internal_imports,
                'external_imports': module_info.external_imports,
                'import_mapping': module_info.import_mapping
            }
        
        # Generate function map
        function_map = {}
        for func_key, func in self.function_map.items():
            function_map[func_key] = {
                'calls': func.calls,
                'called_by': func.called_by,
                'returns_to': func.returns_to,
                'return_assignments': func.return_assignments,
                'call_arguments': getattr(func, "call_arguments", {}),
                'module': func.module,
                'file_path': func.file_path,
                'lineno': func.lineno
            }
        
        # Data flow edges
        data_flow_edges = [
            {
                'source': edge.source,
                'target': edge.target,
                'variable': edge.variable,
                'value_type': edge.value_type
            }
            for edge in self.data_flow_edges
        ]
        
        metadata = {
            'project': {
                'name': self.project_name,
                'base_path': str(self.base_path),
                'entry_point': self.entry_point,
                'total_modules': len(self.modules),
                'total_functions': len(self.function_map),
                'total_classes': len(self.class_map)
            },
            'modules': serialized_modules,
            'dependencies': {
                'internal': list(set().union(*[m.internal_imports for m in self.modules.values()])),
                'external': sorted(list(set().union(*[m.external_imports for m in self.modules.values()])))
            },
            'function_map': function_map,
            'data_flow_edges': data_flow_edges,
            'call_graph': self._generate_call_graph_data(),
            'import_graph': self._generate_import_graph_data()
        }
        
        return metadata
    
    def _generate_call_graph_data(self) -> Dict[str, List[str]]:
        """Generate call graph data for visualization."""
        call_graph = {}
        for func_key, func in self.function_map.items():
            call_graph[func_key] = func.calls
        return call_graph
    
    def _generate_import_graph_data(self) -> Dict[str, List[str]]:
        """Generate import graph data for visualization."""
        import_graph = {}
        for module_name, module_info in self.modules.items():
            import_graph[module_name] = module_info.imports
        return import_graph
    
    def _save_metadata(self, metadata: Dict[str, Any]):
        """Save metadata to JSON file."""
        output_path = self.base_path / 'project_meta.json'
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2, default=str)
        print(f"Metadata saved to: {output_path}")


class ModuleVisitor(ast.NodeVisitor):
    """AST visitor for analyzing Python modules with data flow tracking."""
    
    def __init__(self, file_path: Path, module_name: str, base_path: Path):
        self.file_path = file_path
        self.module_name = module_name
        self.base_path = base_path
        self.functions: List[FunctionInfo] = []
        self.classes: List[ClassInfo] = []
        self.imports: List[str] = []
        self.internal_imports: List[str] = []
        self.external_imports: List[str] = []
        self.import_mapping: Dict[str, str] = {}  # alias -> full_name
        self.function_return_assignments: Dict[str, Dict[str, List[str]]] = {}  # func_name -> {var: [called_funcs]}
        self.function_call_arguments: Dict[str, Dict[str, List[str]]] = {}
        
    def visit_Import(self, node):
        """Process import statements."""
        for alias in node.names:
            module_name = alias.name
            self.imports.append(module_name)
            
            if self._is_internal_import(module_name):
                self.internal_imports.append(module_name)
                # Map the module alias
                alias_name = alias.asname or alias.name
                self.import_mapping[alias_name] = module_name
            else:
                self.external_imports.append(module_name)
        
        self.generic_visit(node)
    
    def visit_ImportFrom(self, node):
        """Process from ... import statements."""
        module_name = node.module or ""

        for alias in node.names:
            full_import = f"{module_name}.{alias.name}" if module_name else alias.name
            self.imports.append(full_import)

            alias_name = alias.asname or alias.name
            self.import_mapping[alias_name] = full_import

            if self._is_internal_import(module_name):
                self.internal_imports.append(full_import)
            else:
                self.external_imports.append(full_import)

        self.generic_visit(node)

    
    def visit_FunctionDef(self, node):
        """Process function definitions with data flow analysis."""
        # Get decorators
        decorators = []
        for decorator in node.decorator_list:
            if isinstance(decorator, ast.Name):
                decorators.append(decorator.id)
            elif isinstance(decorator, ast.Attribute):
                decorators.append(self._get_attribute_name(decorator))
        
        # Get docstring
        docstring = ast.get_docstring(node)
        
        # Analyze function body for calls and data flow
        flow_analyzer = DataFlowAnalyzer(self.module_name, self.import_mapping)
        flow_analyzer.visit(node)
        
        # Create function info
        function_info = FunctionInfo(
            name=node.name,
            module=self.module_name,
            file_path=str(self.file_path),
            lineno=node.lineno,
            calls=flow_analyzer.calls,
            called_by=[],
            is_async=isinstance(node, ast.AsyncFunctionDef),
            decorators=decorators,
            docstring=docstring,
            call_arguments=flow_analyzer.call_arguments,
        )
        
        # Store return assignments for data flow analysis
        self.function_return_assignments[node.name] = flow_analyzer.return_assignments
        
        self.functions.append(function_info)
        self.generic_visit(node)
    
    def visit_ClassDef(self, node):
        """Process class definitions."""
        bases = []
        for base in node.bases:
            if isinstance(base, ast.Name):
                bases.append(base.id)
        
        decorators = []
        for decorator in node.decorator_list:
            if isinstance(decorator, ast.Name):
                decorators.append(decorator.id)
        
        # Visit methods
        methods = []
        for item in node.body:
            if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                flow_analyzer = DataFlowAnalyzer(self.module_name, self.import_mapping)
                flow_analyzer.visit(item)
                
                method_info = FunctionInfo(
                    name=item.name,
                    module=self.module_name,
                    file_path=str(self.file_path),
                    lineno=item.lineno,
                    calls=flow_analyzer.calls,
                    called_by=[],
                    is_async=isinstance(item, ast.AsyncFunctionDef)
                )
                methods.append(method_info)
        
        class_info = ClassInfo(
            name=node.name,
            module=self.module_name,
            file_path=str(self.file_path),
            lineno=node.lineno,
            methods=methods,
            bases=bases,
            decorators=decorators
        )
        
        self.classes.append(class_info)
        self.generic_visit(node)
    
    def _is_internal_import(self, module_name: str) -> bool:
        """Check if an import is from within the project."""
        if not module_name:
            return False
        
        module_path = module_name.replace('.', '/')
        py_file = self.base_path / f"{module_path}.py"
        if py_file.exists():
            return True
        
        package_dir = self.base_path / module_path
        init_file = package_dir / "__init__.py"
        if init_file.exists():
            return True
        
        return False
    
    def _get_attribute_name(self, node: ast.Attribute) -> str:
        """Get full attribute name."""
        parts = []
        while isinstance(node, ast.Attribute):
            parts.append(node.attr)
            node = node.value
        if isinstance(node, ast.Name):
            parts.append(node.id)
        return '.'.join(reversed(parts))


class DataFlowAnalyzer(ast.NodeVisitor):
    """Analyzes data flow within a function: tracks return values and assignments."""
    
    def __init__(self, module_name: str, import_mapping: Dict[str, str]):
        self.module_name = module_name
        self.import_mapping = import_mapping
        self.calls: List[str] = []
        self.return_assignments: Dict[str, List[str]] = {}  # var_name -> [called_functions]
        self.current_assignment = None
        self.call_arguments: Dict[str, List[str]] = {}
        
    def visit_Assign(self, node):
        """Track assignments of function return values."""
        if node.targets and isinstance(node.targets[0], ast.Name):
            var_name = node.targets[0].id

            if isinstance(node.value, ast.Call):
                call_info = self._extract_call_info(node.value)
                if call_info:
                    self.return_assignments.setdefault(var_name, []).append(call_info["func_name"])

            elif isinstance(node.value, ast.Name):
                pass

        self.generic_visit(node)

    
    def visit_Call(self, node):
        call_info = self._extract_call_info(node)
        if call_info:
            func_name = call_info['func_name']
            self.calls.append(func_name)

            arg_vars = []
            for arg in node.args:
                if isinstance(arg, ast.Name):
                    arg_vars.append(arg.id)

            if arg_vars:
                self.call_arguments.setdefault(func_name, []).extend(arg_vars)

        self.generic_visit(node)

    
    def visit_Return(self, node):
        """Track return statements."""
        if isinstance(node.value, ast.Name):
            # Returning a variable - track data flow
            pass
        elif isinstance(node.value, ast.Call):
            # Returning a function call result directly
            call_info = self._extract_call_info(node.value)
            if call_info:
                self.calls.append(call_info['func_name'])
        
        self.generic_visit(node)
    
    def _extract_call_info(self, node: ast.Call) -> Optional[Dict[str, str]]:
        """Extract information from a function call node."""
        if isinstance(node.func, ast.Name):
            return {'func_name': node.func.id, 'full_name': None}
        elif isinstance(node.func, ast.Attribute):
            # Handle module.function calls
            
            # https://github.com/ArunKoundinya/py-flow-mapper/issues/1 : forced external
            #method_name = node.func.attr

            method_name = self._get_attribute_name(node.func)
            
            return {'func_name': method_name, 'full_name': None}

        return None
    
    def _get_attribute_name(self, node: ast.Attribute) -> str:
        """Get full attribute name."""
        parts = []
        while isinstance(node, ast.Attribute):
            parts.append(node.attr)
            node = node.value
        if isinstance(node, ast.Name):
            parts.append(node.id)
        return '.'.join(reversed(parts))