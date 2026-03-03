import json
from dataclasses import dataclass, field
from typing import Dict, List, Any, Set, Optional
from pathlib import Path

COMMON_ALIAS_MAP = {
    "pd": "pandas",
    "np": "numpy",
    "plt": "matplotlib",
    "sns": "seaborn",
    "sk": "sklearn",
}

# Builtins and attribute fragments that are never meaningful as external nodes
NOISY_EXTERNAL = {
    "print", "open", "len", "str", "int", "float", "bool", "dict", "list", "set", "tuple",
    "items", "get", "range", "enumerate", "sorted", "sum", "min", "max", "any", "all",
    "read", "write", "exists", "glob", "join", "split", "format",
    "traceback", "print_exc",
    "Path",
}


# ---------------------------------------------------------------------------
# Lightweight context object — replaces closure-captured locals
# ---------------------------------------------------------------------------

@dataclass
class _GraphContext:
    """
    Holds all read-only references extracted from metadata for one
    generate_detailed_flow_graph() call. Passed to every render helper
    so they stay stateless and independently testable.
    """
    function_map: Dict[str, Any]
    modules: Dict[str, Any]
    internal_funcs: Set[str]
    internal_classes: Set[str]
    call_edges: List[Dict]


# ---------------------------------------------------------------------------
# Main class
# ---------------------------------------------------------------------------

class MermaidGenerator:
    """Generate Mermaid diagrams from project metadata with data flow."""

    def __init__(
        self,
        metadata_path: Path,
        include_external: str = "",
        layout: str = "TD",
        show_dataflow: bool = False,
    ):
        self.metadata = self._load_metadata(metadata_path)
        self.output_dir = metadata_path.parent
        # https://github.com/ArunKoundinya/py-flow-mapper/issues/1 : forced external
        self.force_external: Set[str] = {
            x.strip() for x in include_external.split(",") if x.strip()
        }
        self.layout = layout.upper() if layout.upper() in ("TD", "LR") else "TD"
        self.show_dataflow = show_dataflow

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def generate_detailed_flow_graph(self, output_file: str = "detailed_flow.mmd") -> str:
        """
        Orchestrates the full diagram:
          1. Build shared context from metadata.
          2. Render internal module subgraphs.
          3. Collect + render external library subgraphs (nested inside External).
          4. Render composition edges between external nodes.
          5. Render call edges (internal → internal/external).
          6. Render data-flow edges (dashed) — only when show_dataflow=True.
          7. Render pipeline-heuristic edges.
          8. Render Done edge if output-like calls were detected.

        Layout direction is controlled by self.layout ("TD" default, "LR" optional).
        Data-flow dashed edges are opt-in via self.show_dataflow (default False).
        """
        ctx = self._build_context()

        lines: List[str] = ["```mermaid", f"graph {self.layout}"]

        # Phase 1 – internal subgraphs
        self._render_internal_subgraphs(ctx, lines)

        # Phase 2 – collect external nodes, render External wrapper
        external_lib_nodes, uses_done = self._collect_external_nodes(ctx)
        self._render_external_subgraphs(external_lib_nodes, uses_done, lines)

        # Phase 3 – composition edges (e.g. ColumnTransformer → OneHotEncoder)
        self._render_composition_edges(ctx, external_lib_nodes, lines)

        # Phase 4 – call edges
        caller_order = self._dfs_caller_order(ctx, entry="main.main")
        self._render_call_edges(ctx, caller_order, lines)

        # Phase 5 – data-flow edges (opt-in; hidden by default to reduce clutter)
        if self.show_dataflow:
            self._render_dataflow_edges(ctx, caller_order, lines)

        # Phase 6 – pipeline heuristic edges
        self._render_pipeline_heuristic_edges(ctx, lines)

        # Phase 7 – Done edge
        if uses_done:
            self._render_done_edge(external_lib_nodes, lines)

        lines.append("```")

        content = "\n".join(lines)
        output_path = self.output_dir / output_file
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(content)

        print(f"✓ Detailed flow graph generated: {output_path}")
        return content

    def generate_all_diagrams(self):
        """
        Generate both layout variants and a master markdown file containing both.

        Files produced:
          flow_TD.mmd  — top-down layout  (best for execution flow reading)
          flow_LR.mmd  — left-right layout (best for project vs external boundary)
          all_flow_diagrams.md — both diagrams combined
        """
        # Temporarily override layout to produce both variants
        original_layout = self.layout

        self.layout = "TD"
        td_content = self.generate_detailed_flow_graph(output_file="flow_TD.mmd")

        self.layout = "LR"
        lr_content = self.generate_detailed_flow_graph(output_file="flow_LR.mmd")

        self.layout = original_layout  # restore

        master_content = (
            "# Project Flow Diagrams\n\n"
            "> **flow_TD.mmd** — top-down layout, best for following execution order.\n"
            "> **flow_LR.mmd** — left-right layout, best for seeing project vs external boundary.\n\n"
            "## Top-Down Flow (TD)\n\n"
            + td_content + "\n\n"
            "## Left-Right Flow (LR)\n\n"
            + lr_content + "\n\n"
        )

        master_path = self.output_dir / "all_flow_diagrams.md"
        with open(master_path, "w", encoding="utf-8") as f:
            f.write(master_content)

        print(f"✓ Both layout diagrams generated in: {self.output_dir}")
        return master_path

    # ------------------------------------------------------------------
    # Context builder
    # ------------------------------------------------------------------

    def _build_context(self) -> _GraphContext:
        """Extract and pre-compute all read-only data needed by render helpers."""
        function_map = self.metadata.get("function_map", {}) or {}
        modules = self.metadata.get("modules", {}) or {}

        internal_classes: Set[str] = set()
        for mod_info in modules.values():
            for c in (mod_info.get("classes") or []):
                cname = c.get("name")
                if cname:
                    internal_classes.add(cname)

        return _GraphContext(
            function_map=function_map,
            modules=modules,
            internal_funcs=set(function_map.keys()),
            internal_classes=internal_classes,
            call_edges=self.metadata.get("call_edges", []) or [],
        )

    # ------------------------------------------------------------------
    # Resolver helpers  (operate on context, no shared mutable state)
    # ------------------------------------------------------------------

    def _module_import_mapping(self, ctx: _GraphContext, mod: str) -> dict:
        return (ctx.modules.get(mod, {}) or {}).get("import_mapping", {}) or {}

    def _merged_alias_map(self, ctx: _GraphContext, mod: str) -> dict:
        return {**COMMON_ALIAS_MAP, **self._module_import_mapping(ctx, mod)}

    def _external_root_name(self, ctx: _GraphContext, call_name: str, current_module: str) -> str:
        """Resolve the alias root of a call to its real library name."""
        if not call_name:
            return ""
        root = call_name.split(".")[0]
        return self._merged_alias_map(ctx, current_module).get(root, root)

    def _resolve_lib_label(self, ctx: _GraphContext, callee: str, current_module: str):
        """
        Return (top_lib, label) for any external callee.

        Cases:
          1. alias.method  e.g. pd.read_csv
             -> top_lib = resolved alias root  (e.g. "pandas")
             -> label   = method               (e.g. "read_csv")

          2. bare name imported via  from pkg.sub import Name
             import_mapping["Name"] = "pkg.sub.Name"
             -> top_lib = first segment        (e.g. "sklearn")
             -> label   = Name                 (e.g. "LogisticRegression")

          3. bare name with no mapping (unknown library)
             -> top_lib = label = callee
        """
        merged = self._merged_alias_map(ctx, current_module)

        if "." in callee:
            root = callee.split(".")[0]
            top_lib = merged.get(root, root)
            label = callee.split(".", 1)[1]
            return top_lib, label

        mapped = merged.get(callee, "")
        if mapped and "." in mapped:
            top_lib = mapped.split(".")[0]
        else:
            top_lib = callee
        return top_lib, callee

    def _ext_node_id(self, ctx: _GraphContext, callee: str, current_module: str) -> str:
        """Stable Mermaid node-id for an external callee."""
        top_lib, label = self._resolve_lib_label(ctx, callee, current_module)
        if top_lib == label:
            return _nid(f"ext__{top_lib}")
        return _nid(f"ext__{top_lib}__{label}")

    def _keep_external(self, ctx: _GraphContext, call_name: str, current_module: str) -> bool:
        """
        Decide whether this callee should appear as an external node.
        Returns True only when the call is meaningful and either explicitly
        requested via force_external or passes the CamelCase heuristic.
        """
        if not call_name:
            return False

        base = _short_label(call_name)
        merged = self._merged_alias_map(ctx, current_module)

        # Explicit force_external match (root or base)
        root = self._external_root_name(ctx, call_name, current_module)
        if root and root in self.force_external:
            return True
        if base in self.force_external:
            return True

        # Dotted calls: keep only if root resolves to a force_external lib
        if "." in call_name:
            resolved_root = merged.get(call_name.split(".")[0], call_name.split(".")[0])
            return resolved_root in self.force_external

        # Bare name from import_mapping
        imp_map = self._module_import_mapping(ctx, current_module)
        if base in imp_map:
            mapped = imp_map[base]
            mapped_module = ".".join(mapped.split(".")[:-1])
            if mapped_module in ctx.modules:
                return False          # it's actually an internal symbol
            top_lib = mapped.split(".")[0]
            if top_lib in self.force_external:
                return True
            return True               # external, even if not force-requested

        if base in ctx.internal_classes:
            return False
        if base in NOISY_EXTERNAL:
            return False

        return _is_camel_case(base)

    def _resolve_internal(self, ctx: _GraphContext, call: str, current_module: str) -> str:
        """Resolve a call string to its full internal function key, or '' if external/unknown."""
        call = call or ""

        target = self._find_function_full_name(call, current_module)
        if target and target in ctx.internal_funcs:
            return target

        imp_map = self._module_import_mapping(ctx, current_module)

        if call in imp_map:
            mapped = imp_map[call]
            if mapped in ctx.internal_funcs:
                return mapped
            target = self._find_function_full_name(mapped, current_module)
            if target and target in ctx.internal_funcs:
                return target

        if "." in call:
            root, rest = call.split(".", 1)
            if root in imp_map:
                candidate = f"{imp_map[root]}.{rest}"
                if candidate in ctx.internal_funcs:
                    return candidate
                target = self._find_function_full_name(candidate, current_module)
                if target and target in ctx.internal_funcs:
                    return target

            method = call.split(".")[-1]
            matches = [k for k in ctx.internal_funcs if k.endswith("." + method)]
            if len(matches) == 1:
                return matches[0]

        return ""

    # ------------------------------------------------------------------
    # DFS call order
    # ------------------------------------------------------------------

    def _dfs_caller_order(self, ctx: _GraphContext, entry: str) -> List[str]:
        """Return functions in DFS call order starting from entry, then any remainder."""
        seen: Set[str] = set()
        order: List[str] = []

        def visit(fn_key: str):
            if fn_key in seen:
                return
            seen.add(fn_key)
            order.append(fn_key)
            info = ctx.function_map.get(fn_key, {})
            current_module = info.get("module", "") or ""
            for c in (info.get("calls") or []):
                target = self._find_function_full_name(c, current_module)
                if target and target in ctx.function_map:
                    visit(target)

        if entry in ctx.function_map:
            visit(entry)

        for fn in ctx.function_map:
            if fn not in seen:
                order.append(fn)

        return order

    # ------------------------------------------------------------------
    # Render phases
    # ------------------------------------------------------------------

    def _render_internal_subgraphs(self, ctx: _GraphContext, lines: List[str]):
        """Emit one subgraph per internal module, containing its functions."""
        module_functions: Dict[str, List[str]] = {}
        for func_name, func_info in ctx.function_map.items():
            module = func_info.get("module", "") or "module"
            module_functions.setdefault(module, []).append(func_name)

        for module_name, funcs in module_functions.items():
            if not funcs:
                continue
            short_module = module_name.split(".")[-1] or module_name
            lines.append(f"    subgraph {_nid(short_module)} [{short_module}]")
            for fn in sorted(funcs):
                lines.append(f"        {_nid(fn)}[{_short_label(fn)}]")
            lines.append("    end")

    def _collect_external_nodes(self, ctx: _GraphContext):
        """
        Scan all function calls and return:
          external_lib_nodes: dict[top_lib -> set[label]]
          uses_done:          bool  (True if any output-like call was found)
        """
        external_lib_nodes: Dict[str, Set[str]] = {}
        uses_done = False

        for _, info in ctx.function_map.items():
            current_module = info.get("module", "") or ""

            for callee in (info.get("call_arguments", {}) or {}).keys():
                if not self._resolve_internal(ctx, callee, current_module):
                    if self._keep_external(ctx, callee, current_module):
                        top_lib, label = self._resolve_lib_label(ctx, callee, current_module)
                        external_lib_nodes.setdefault(top_lib, set()).add(label)

            for callee in (info.get("calls") or []):
                if _is_outputish_call(_short_label(callee)):
                    uses_done = True
                if not self._resolve_internal(ctx, callee, current_module):
                    if self._keep_external(ctx, callee, current_module):
                        top_lib, label = self._resolve_lib_label(ctx, callee, current_module)
                        external_lib_nodes.setdefault(top_lib, set()).add(label)

        return external_lib_nodes, uses_done

    def _render_external_subgraphs(
        self,
        external_lib_nodes: Dict[str, Set[str]],
        uses_done: bool,
        lines: List[str],
    ):
        """
        Emit the outer External subgraph containing one nested subgraph
        per library, each with its individual method nodes.
        """
        if not external_lib_nodes and not uses_done:
            return

        lines.append("    subgraph External [External]")

        for top_lib in sorted(external_lib_nodes):
            labels = external_lib_nodes[top_lib]
            lines.append(f"        subgraph extlib_{_nid(top_lib)} [{top_lib}]")
            for label in sorted(labels):
                if top_lib == label:
                    lines.append(f"            {_nid(f'ext__{top_lib}')}[{label}]")
                else:
                    lines.append(f"            {_nid(f'ext__{top_lib}__{label}')}[{label}]")
            lines.append("        end")

        if uses_done:
            lines.append("        subgraph extlib_done [Done]")
            lines.append("            Done((Done))")
            lines.append("        end")

        lines.append("    end")

    def _render_composition_edges(
        self,
        ctx: _GraphContext,
        external_lib_nodes: Dict[str, Set[str]],
        lines: List[str],
    ):
        """
        Emit edges between external nodes that were recorded as call_edges
        (e.g. ColumnTransformer → OneHotEncoder inside a Pipeline builder).
        """
        seen: Set[tuple] = set()

        for e in ctx.call_edges:
            src_call = e.get("source") or ""
            tgt_call = e.get("target") or ""
            mod = e.get("module") or ""

            if not src_call or not tgt_call:
                continue
            if not self._keep_external(ctx, src_call, mod):
                continue
            if not self._keep_external(ctx, tgt_call, mod):
                continue

            src_lib, _ = self._resolve_lib_label(ctx, src_call, mod)
            tgt_lib, _ = self._resolve_lib_label(ctx, tgt_call, mod)

            if src_lib not in external_lib_nodes or tgt_lib not in external_lib_nodes:
                continue

            k = (src_call, tgt_call, mod)
            if k in seen:
                continue
            seen.add(k)

            lines.append(
                f"    {self._ext_node_id(ctx, src_call, mod)} --> "
                f"{self._ext_node_id(ctx, tgt_call, mod)}"
            )

    def _render_call_edges(
        self,
        ctx: _GraphContext,
        caller_order: List[str],
        lines: List[str],
    ):
        """
        Emit solid call edges (internal → internal and internal → external).

        Parallel edges between the same pair of nodes are merged into a single
        edge with a combined label (e.g. "X,y" instead of two separate edges)
        to prevent label overlap clutter.
        """
        extra_call_edges = ctx.call_edges

        for caller in caller_order:
            if caller not in ctx.function_map:
                continue

            info = ctx.function_map[caller]
            current_module = info.get("module", "") or ""
            src = _nid(caller)
            call_args = info.get("call_arguments", {}) or {}

            # Compute which external roots are "sources" in a composition edge
            # so their composed children don't also get direct edges from here.
            caller_ext_roots = {
                self._external_root_name(ctx, c, current_module)
                for c in (info.get("calls") or [])
                if self._keep_external(ctx, c, current_module)
                and not self._resolve_internal(ctx, c, current_module)
            }
            suppressed_ext_roots = {
                self._external_root_name(ctx, e.get("target", ""), current_module)
                for e in extra_call_edges
                if (e.get("module") or "") in ("", current_module)
                and self._external_root_name(ctx, e.get("source", ""), current_module) in caller_ext_roots
            }

            # Collect all (src, dst, label) tuples first, then merge per (src,dst) pair
            # so parallel calls with different labels become one combined-label edge.
            edge_labels: Dict[tuple, Set[str]] = {}   # (src_id, dst_id) -> set of labels

            for callee in (info.get("calls") or []):
                if not callee:
                    continue

                if (
                    self._keep_external(ctx, callee, current_module)
                    and not self._resolve_internal(ctx, callee, current_module)
                    and self._external_root_name(ctx, callee, current_module) in suppressed_ext_roots
                ):
                    continue

                target_internal = self._resolve_internal(ctx, callee, current_module)
                vars_used = (
                    call_args.get(callee)
                    or (call_args.get(target_internal) if target_internal else [])
                    or []
                )
                label = _normalize_vars(vars_used)

                if target_internal:
                    dst_id = _nid(target_internal)
                elif self._keep_external(ctx, callee, current_module):
                    dst_id = self._ext_node_id(ctx, callee, current_module)
                else:
                    continue

                pair = (src, dst_id)
                edge_labels.setdefault(pair, set())
                if label:
                    edge_labels[pair].add(label)

            # Emit one edge per (src, dst) pair with merged label
            for (src_id, dst_id), labels in edge_labels.items():
                combined = ",".join(sorted(labels)) if labels else ""
                lines.append(
                    f"    {src_id} --> |{combined}| {dst_id}"
                    if combined else
                    f"    {src_id} --> {dst_id}"
                )

    def _render_dataflow_edges(
        self,
        ctx: _GraphContext,
        caller_order: List[str],
        lines: List[str],
    ):
        """
        Emit dashed data-flow edges derived from return_assignments.

        Deduplication: multiple variables flowing between the same pair of nodes
        are merged into one dashed edge with a combined label, mirroring the same
        approach used for solid call edges to avoid overlapping arrows.
        """
        for fn in caller_order:
            if fn not in ctx.function_map:
                continue

            info = ctx.function_map[fn]
            dst = _nid(fn)
            current_module = info.get("module", "") or ""

            # Collect all (src_id -> set[var]) mappings, then emit one edge per src
            src_vars: Dict[str, Set[str]] = {}

            for var_name, producers in (info.get("return_assignments", {}) or {}).items():
                for p in (producers or []):
                    internal_p = self._resolve_internal(ctx, p, current_module)
                    if internal_p:
                        src_id = _nid(internal_p)
                    elif self._keep_external(ctx, p, current_module):
                        src_id = self._ext_node_id(ctx, p, current_module)
                    else:
                        continue
                    src_vars.setdefault(src_id, set()).add(var_name)

            for src_id, var_names in src_vars.items():
                combined = ",".join(sorted(var_names))
                lines.append(f"    {src_id} -.->|{combined}| {dst}")

    def _render_pipeline_heuristic_edges(self, ctx: _GraphContext, lines: List[str]):
        """
        Heuristic: when a function calls two external tools and one receives
        a file-ish argument, draw a pipeline edge from the producer to the consumer.
        """
        for _, info in ctx.function_map.items():
            current_module = info.get("module", "") or ""
            calls = info.get("calls") or []
            call_args = info.get("call_arguments") or {}

            meaningful = [
                c for c in calls
                if c
                and self._keep_external(ctx, c, current_module)
                and not self._resolve_internal(ctx, c, current_module)
            ]
            # deduplicate while preserving order
            seen_m: Set[str] = set()
            meaningful = [c for c in meaningful if not (c in seen_m or seen_m.add(c))]

            if len(meaningful) < 2:
                continue

            fileish_callee = next(
                (
                    callee for callee, args in call_args.items()
                    if self._keep_external(ctx, callee, current_module)
                    and any(_is_fileish_arg(a) for a in (args or []) if isinstance(a, str))
                ),
                None,
            )
            if not fileish_callee:
                continue

            producer = next((x for x in meaningful if x != fileish_callee), None)
            if not producer:
                continue

            vars_passed = call_args.get(fileish_callee, []) or []
            label = _normalize_vars(vars_passed) or "value"
            lines.append(
                f"    {self._ext_node_id(ctx, producer, current_module)} "
                f"-->|{label}| {self._ext_node_id(ctx, fileish_callee, current_module)}"
            )

    def _render_done_edge(
        self,
        external_lib_nodes: Dict[str, Set[str]],
        lines: List[str],
    ):
        """Connect the last output-like external library node to Done."""
        tool_like = [
            lib for lib in external_lib_nodes
            if any(k in lib for k in ("Generator", "Exporter", "Renderer", "Writer"))
        ]
        if tool_like:
            lines.append(f"    {_nid('ext__' + sorted(tool_like)[-1])} -->|output| Done")

    # ------------------------------------------------------------------
    # Low-level metadata helpers
    # ------------------------------------------------------------------

    def _load_metadata(self, metadata_path: Path) -> Dict[str, Any]:
        with open(metadata_path, "r", encoding="utf-8") as f:
            return json.load(f)

    def _find_function_full_name(self, func_name: str, current_module: str) -> str:
        """Resolve func_name to its fully-qualified key in function_map."""
        function_map = self.metadata.get("function_map", {})

        if func_name in function_map:
            return func_name

        potential_key = f"{current_module}.{func_name}"
        if potential_key in function_map:
            return potential_key

        for full_name in function_map:
            if full_name.endswith(f".{func_name}"):
                return full_name

        return ""


# ---------------------------------------------------------------------------
# Module-level pure utility functions  (no class state needed)
# ---------------------------------------------------------------------------

def _nid(name: str) -> str:
    """Return a Mermaid-safe node id."""
    return (name or "").replace(".", "_").replace(":", "_").replace("-", "_")


def _short_label(name: str) -> str:
    return (name or "").split(".")[-1]


def _is_camel_case(s: str) -> bool:
    return bool(s) and s[0].isupper() and any(c.islower() for c in s[1:])


def _normalize_vars(vars_used) -> str:
    if not vars_used:
        return ""
    cleaned = [v for v in vars_used if isinstance(v, str) and v.isidentifier()]
    if not cleaned:
        return ""
    return ",".join(sorted(set(cleaned)))


def _is_outputish_call(name: str) -> bool:
    n = (name or "").lower()
    return n.startswith(("generate", "render", "export")) or ("graph" in n) or ("diagram" in n)


def _is_fileish_arg(arg: str) -> bool:
    a = (arg or "").lower()
    return any(
        k in a for k in (
            "meta", "json", "yaml", "yml", "config", "file",
            ".json", ".yaml", ".yml", ".cfg", ".ini", ".txt", ".csv",
        )
    )