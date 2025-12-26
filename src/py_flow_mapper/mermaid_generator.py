import json
from typing import Dict, List, Any
from pathlib import Path

class MermaidGenerator:
    """Generate Mermaid diagrams from project metadata with data flow."""
    
    def __init__(self, metadata_path: Path):
        self.metadata = self._load_metadata(metadata_path)
        self.output_dir = metadata_path.parent
    
    def _load_metadata(self, metadata_path: Path) -> Dict[str, Any]:
        """Load metadata from JSON file."""
        with open(metadata_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def generate_flow_graph(self, output_file: str = "flow_graph.mmd") -> str:
        """Generate Mermaid flow graph showing data flow between functions."""
        lines = [
            "```mermaid",
            "graph TD",
        ]
        
        function_map = self.metadata.get('function_map', {})
        data_flow_edges = self.metadata.get('data_flow_edges', [])
        
        # Add nodes with simple names
        node_names = {}
        for i, func_name in enumerate(function_map.keys()):
            simple_name = func_name.split('.')[-1]
            node_id = f"func_{i}"
            node_names[func_name] = node_id
            lines.append(f"    {node_id}[{simple_name}]")
        
        # Add direct call edges (black arrows)
        for func_name, func_info in function_map.items():
            source_id = node_names[func_name]
            for call in func_info.get('calls', []):
                # Find the called function
                target_func = self._find_function_full_name(call, func_info.get('module', ''))
                if target_func and target_func in node_names:
                    target_id = node_names[target_func]
                    lines.append(f"    {source_id} --> {target_id}")
        
        # Add data flow edges (dashed arrows with labels)
        for edge in data_flow_edges:
            source = edge.get('source')
            target = edge.get('target')
            variable = edge.get('variable', 'result')
            
            if source in node_names and target in node_names:
                source_id = node_names[source]
                target_id = node_names[target]
                lines.append(f"    {source_id} -.->|{variable}| {target_id}")
        
        lines.append("```")
        
        content = "\n".join(lines)
        
        # Save to file
        output_path = self.output_dir / output_file
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        print(f"✓ Flow graph generated: {output_path}")
        return content
    
    def generate_detailed_flow_graph(self, output_file: str = "detailed_flow.mmd") -> str:
        """Generate detailed flow graph showing both calls and data flow with modules."""
        lines = [
            "```mermaid",
            "graph TD",
        ]
        
        function_map = self.metadata.get('function_map', {})
        modules = self.metadata.get('modules', {})
        
        # Group functions by module
        module_functions = {}
        for func_name, func_info in function_map.items():
            module = func_info.get('module', '')
            if module not in module_functions:
                module_functions[module] = []
            module_functions[module].append(func_name)
        
        # Create subgraphs for each module
        for module_name, funcs in module_functions.items():
            if funcs:  # Only create subgraph if there are functions
                short_module = module_name.split('.')[-1] or module_name
                lines.append(f"    subgraph {short_module} [{short_module}]")
                
                for func_name in funcs:
                    simple_name = func_name.split('.')[-1]
                    lines.append(f"        {func_name.replace('.', '_')}[{simple_name}]")
                
                lines.append("    end")
        
        # Add call edges
        for caller, info in function_map.items():
            call_args = info.get("call_arguments", {})

            for callee, vars_used in call_args.items():
                target = self._find_function_full_name(callee, info.get("module", ""))
                if not target or target not in function_map:
                    continue

                source_id = caller.replace(".", "_")
                target_id = target.replace(".", "_")

                label = ",".join(sorted(set(vars_used)))
                lines.append(f"    {source_id} --> |{label}| {target_id}")

        
        # Add data flow edges from return assignments
        for func_name, func_info in function_map.items():
            return_assignments = func_info.get('return_assignments', {})
            for var_name, called_funcs in return_assignments.items():
                for called_func in called_funcs:
                    target_func = self._find_function_full_name(called_func, func_info.get('module', ''))
                    if target_func:
                        source_id = target_func.replace('.', '_')
                        target_id = func_name.replace('.', '_')
                        lines.append(f"    {source_id} -.->|{var_name}| {target_id}")
        
        lines.append("```")
        
        content = "\n".join(lines)
        
        output_path = self.output_dir / output_file
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        print(f"✓ Detailed flow graph generated: {output_path}")
        return content
    
    def generate_call_graph(self, output_file: str = "call_graph.mmd") -> str:
        """Generate Mermaid call graph (simplified version)."""
        lines = [
            "```mermaid",
            "graph TD",
        ]
        
        function_map = self.metadata.get('function_map', {})
        
        # Add nodes with module prefixes
        for func_name in function_map:
            lines.append(f"    {func_name.replace('.', '_')}[{func_name}]")
        
        # Add edges
        for func_name, func_info in function_map.items():
            for call in func_info.get('calls', []):
                target_func = self._find_function_full_name(call, func_info.get('module', ''))
                if target_func and target_func in function_map:
                    source_id = func_name.replace('.', '_')
                    target_id = target_func.replace('.', '_')
                    lines.append(f"    {source_id} --> {target_id}")
        
        lines.append("```")
        
        content = "\n".join(lines)
        
        output_path = self.output_dir / output_file
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        return content
    
    def _find_function_full_name(self, func_name: str, current_module: str) -> str:
        """Find the full name of a function in the metadata."""
        function_map = self.metadata.get('function_map', {})
        
        # Direct match
        if func_name in function_map:
            return func_name
        
        # Check if it's a function in the current module
        potential_key = f"{current_module}.{func_name}"
        if potential_key in function_map:
            return potential_key
        
        # Search by function name across all modules
        for full_name in function_map:
            if full_name.endswith(f".{func_name}"):
                return full_name
        
        return ""
    
    def generate_all_diagrams(self):
        """Generate all available diagrams."""
        diagrams = {
            "flow_graph": self.generate_flow_graph(),
            "detailed_flow": self.generate_detailed_flow_graph(),
            "call_graph": self.generate_call_graph()
        }
        
        # Create a master markdown file
        master_content = "# Project Flow Diagrams\n\n"
        for name, content in diagrams.items():
            master_content += f"## {name.replace('_', ' ').title()}\n\n"
            master_content += content + "\n\n"
        
        master_path = self.output_dir / "all_flow_diagrams.md"
        with open(master_path, 'w', encoding='utf-8') as f:
            f.write(master_content)
        
        print(f"✓ All diagrams generated in: {master_path}")
        return master_path