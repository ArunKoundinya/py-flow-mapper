import json
from typing import Dict, List, Any
from pathlib import Path

COMMON_ALIAS_MAP = {
    "pd": "pandas",
    "np": "numpy",
    "plt": "matplotlib",
    "sns": "seaborn",
    "sk": "sklearn",
}


class MermaidGenerator:
    """Generate Mermaid diagrams from project metadata with data flow."""
    
    def __init__(self, metadata_path: Path,include_external: str = ""):
        self.metadata = self._load_metadata(metadata_path)
        self.output_dir = metadata_path.parent
        # https://github.com/ArunKoundinya/py-flow-mapper/issues/1 : forced external
        self.force_external = {
            x.strip() for x in include_external.split(",") if x.strip()
        }
    
    def _load_metadata(self, metadata_path: Path) -> Dict[str, Any]:
        """Load metadata from JSON file."""
        with open(metadata_path, 'r', encoding='utf-8') as f:
            return json.load(f)
        
      
    def generate_detailed_flow_graph(self, output_file: str = "detailed_flow.mmd") -> str:
        """
        Blended detailed flow graph (stable + readable):
        - Internal functions grouped by module subgraphs.
        - Call edges are emitted in main-flow order (DFS from entry), with labels from call_arguments when available.
        - Data flow uses return_assignments (dashed edges with variable labels).
        - External nodes included only when meaningful (filtered heuristics).
        - Adds a generic pipeline edge between two external tool-like nodes when file-ish arguments suggest a handoff.
        - Adds a Done node when output-generation-like calls are detected.
        """
        lines = ["```mermaid", "graph LR"]

        function_map = self.metadata.get("function_map", {}) or {}
        internal_funcs = set(function_map.keys())
        modules = self.metadata.get("modules", {}) or {}

        # ---- internal class names (avoid misclassifying internal classes as "External") ----
        internal_classes = set()
        for mod_info in modules.values():
            for c in (mod_info.get("classes") or []):
                cname = c.get("name")
                if cname:
                    internal_classes.add(cname)

        # ---------- helpers ----------
        def nid(name: str) -> str:
            # Mermaid-safe id
            return (name or "").replace(".", "_").replace(":", "_").replace("-", "_")

        def short_label(name: str) -> str:
            return (name or "").split(".")[-1]

        def is_camel_case(s: str) -> bool:
            return bool(s) and s[0].isupper() and any(c.islower() for c in s[1:])

        def normalize_vars(vars_used) -> str:
            if not vars_used:
                return ""
            cleaned = [v for v in vars_used if isinstance(v, str) and v.isidentifier()]
            if not cleaned:
                return ""
            return ",".join(sorted(set(cleaned)))
        

        def module_import_mapping(mod: str) -> dict:
            return (modules.get(mod, {}) or {}).get("import_mapping", {}) or {}

        def external_root_name(call_name: str, current_module: str) -> str:
            if not call_name:
                return ""
            root = call_name.split(".")[0]
            imp_map = module_import_mapping(current_module)
            merged_map = {**COMMON_ALIAS_MAP, **imp_map}
            return merged_map.get(root, root)

        # Keep the graph clean: ignore common builtins + attribute-noise
        NOISY_EXTERNAL = {
            "print", "open", "len", "str", "int", "float", "bool", "dict", "list", "set", "tuple",
            "items", "get", "range", "enumerate", "sorted", "sum", "min", "max", "any", "all",
            "read", "write", "exists", "glob", "join", "split", "format",
            "traceback", "print_exc",
            "Path",
        }

        def keep_external(call_name: str, current_module: str) -> bool:
            if not call_name:
                return False

            base = short_label(call_name)

            root = external_root_name(call_name, current_module)
            if root and root in self.force_external:
                return True
            if base in self.force_external:
                return True

            imp_map = module_import_mapping(current_module)
            if base in imp_map:
                mapped = imp_map[base]
                mapped_module = ".".join(mapped.split(".")[:-1])
                if mapped_module in modules:
                    return False
                return True

            if base in internal_classes:
                return False

            if base in NOISY_EXTERNAL:
                return False

            if "." in call_name:
                return False

            return is_camel_case(base)

        def resolve_internal(call: str, current_module: str) -> str:
            # First try your normal resolver
            target = self._find_function_full_name(call, current_module)
            if target and target in internal_funcs:
                return target

            # ✅ NEW: if call is like "obj.method", try to map by method name
            if "." in (call or ""):
                method = call.split(".")[-1]
                matches = [k for k in internal_funcs if k.endswith("." + method)]
                if len(matches) == 1:
                    return matches[0]

            return ""


        def is_outputish_call(name: str) -> bool:
            n = (name or "").lower()
            return n.startswith(("generate", "render", "export")) or ("graph" in n) or ("diagram" in n)

        def is_fileish_arg(arg: str) -> bool:
            a = (arg or "").lower()
            return any(k in a for k in ("meta", "json", "yaml", "yml", "config", "path", "file"))

        def ordered_functions_from_entry(entry_key: str) -> list[str]:
            """DFS from entry, preserving call order from metadata."""
            seen = set()
            order = []

            def visit(fn_key: str):
                if fn_key in seen:
                    return
                seen.add(fn_key)
                order.append(fn_key)

                info = function_map.get(fn_key, {})
                current_module = info.get("module", "") or ""
                #current_module_ctx = current_module
                for c in (info.get("calls") or []):
                    target = self._find_function_full_name(c, current_module)
                    if target and target in function_map:
                        visit(target)

            if entry_key in function_map:
                visit(entry_key)

            for fn in function_map.keys():
                if fn not in seen:
                    order.append(fn)

            return order

        # ---------- group internal functions by module ----------
        module_functions = {}
        for func_name, func_info in function_map.items():
            module = func_info.get("module", "") or "module"
            module_functions.setdefault(module, []).append(func_name)

        for module_name, funcs in module_functions.items():
            if not funcs:
                continue
            short_module = module_name.split(".")[-1] or module_name
            lines.append(f"    subgraph {nid(short_module)} [{short_module}]")
            for fn in sorted(funcs):
                lines.append(f"        {nid(fn)}[{short_label(fn)}]")
            lines.append("    end")

        # ---------- collect external nodes + Done detection ----------
        external_nodes = set()
        uses_done = False

        for _, info in function_map.items():
            current_module = info.get("module", "") or ""
            #current_module_ctx = current_module

            # prefer call_arguments keys
            call_args = info.get("call_arguments", {}) or {}
            for callee in call_args.keys():
                if resolve_internal(callee, current_module):
                    continue
                if keep_external(callee, current_module):
                    external_nodes.add(external_root_name(callee, current_module) or callee)

            # scan raw calls for Done + missed externals
            for callee in (info.get("calls") or []):
                if is_outputish_call(short_label(callee)):
                    uses_done = True

                if resolve_internal(callee, current_module):
                    continue
                if keep_external(callee, current_module):
                    external_nodes.add(external_root_name(callee, current_module) or callee)

        if external_nodes or uses_done:
            lines.append("    subgraph External [External]")
            for n in sorted(external_nodes):
                lines.append(f"        {nid('ext:' + n)}[{short_label(n)}]")
            if uses_done:
                lines.append("        Done((Done))")
            lines.append("    end")

        # ---------- call edges (internal -> internal/external), ordered from entry ----------
        caller_order = ordered_functions_from_entry("main.main")

        for caller in caller_order:
            if caller not in function_map:
                continue

            info = function_map[caller]
            current_module = info.get("module", "") or ""
            #current_module_ctx = current_module
            src = nid(caller)

            call_args = info.get("call_arguments", {}) or {}
            seen = set()

            for callee in (info.get("calls") or []):
                if not callee:
                    continue

                target_internal = resolve_internal(callee, current_module)

                # label (if any)
                vars_used = call_args.get(callee) or (call_args.get(target_internal) if target_internal else []) or []
                label = normalize_vars(vars_used)

                if target_internal:
                    edge_key = (src, nid(target_internal), label)
                    if edge_key in seen:
                        continue
                    seen.add(edge_key)

                    if label:
                        lines.append(f"    {src} --> |{label}| {nid(target_internal)}")
                    else:
                        lines.append(f"    {src} --> {nid(target_internal)}")
                else:
                    if keep_external(callee, current_module):
                        ext = external_root_name(callee, current_module) or callee
                        edge_key = (src, nid("ext:" + callee), label)
                        if edge_key in seen:
                            continue
                        seen.add(edge_key)

                        if label:
                            lines.append(f"    {src} --> |{label}| {nid('ext:' + ext)}")
                        else:
                            lines.append(f"    {src} --> {nid('ext:' + ext)}")

        # ---------- data flow edges (return_assignments) ----------
        for fn in caller_order:
            if fn not in function_map:
                continue

            info = function_map[fn]
            dst = nid(fn)
            current_module = info.get("module", "") or ""
            #current_module_ctx = current_module

            return_assignments = info.get("return_assignments", {}) or {}
            for var_name, producers in return_assignments.items():
                for p in (producers or []):
                    internal_p = resolve_internal(p, current_module)
                    if internal_p:
                        lines.append(f"    {nid(internal_p)} -.->|{var_name}| {dst}")
                    else:
                        if keep_external(p, current_module):
                            ext = external_root_name(p,current_module) or p
                            lines.append(f"    {nid('ext:' + ext)} -.->|{var_name}| {dst}")

        # ---------- pipeline heuristic: external tool A -> external tool B ----------
        for _, info in function_map.items():
            current_module = info.get("module", "") or ""
            #current_module_ctx = current_module
            calls = info.get("calls") or []
            call_args = info.get("call_arguments") or {}

            meaningful = []
            for c in calls:
                if c and keep_external(c,current_module) and not resolve_internal(c, current_module):
                    if c not in meaningful:
                        meaningful.append(c)

            if len(meaningful) < 2:
                continue

            fileish_callee = None
            for callee, args in call_args.items():
                if keep_external(callee, current_module) and any(is_fileish_arg(a) for a in (args or []) if isinstance(a, str)):
                    fileish_callee = callee
                    break

            if not fileish_callee:
                continue

            producer = next((x for x in meaningful if x != fileish_callee), None)
            if not producer:
                continue

            vars_passed = call_args.get(fileish_callee, []) or []
            label = normalize_vars(vars_passed) or "value"
            prod_ext = external_root_name(producer,current_module) or producer
            file_ext = external_root_name(fileish_callee,current_module) or fileish_callee
            lines.append(f"    {nid('ext:' + prod_ext)} -->|{label}| {nid('ext:' + file_ext)}")

        # ---------- Done edge ----------
        if uses_done:
            tool_like = [
                n for n in external_nodes
                if any(k in short_label(n) for k in ("Generator", "Exporter", "Renderer", "Writer"))
            ]
            if tool_like:
                lines.append(f"    {nid('ext:' + sorted(tool_like)[-1])} -->|output| Done")

        lines.append("```")

        content = "\n".join(lines)
        output_path = self.output_dir / output_file
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(content)

        print(f"✓ Detailed flow graph generated: {output_path}")
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
            "detailed_flow": self.generate_detailed_flow_graph(),
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