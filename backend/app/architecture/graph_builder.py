"""Dependency graph (Task 3: detect relationships and dependencies) built with NetworkX."""
import posixpath
import sys
from collections import Counter, defaultdict

import networkx as nx

_FALLBACK_STDLIB = {
    "abc", "argparse", "asyncio", "base64", "collections", "contextlib", "copy",
    "csv", "dataclasses", "datetime", "enum", "functools", "glob", "hashlib",
    "http", "importlib", "inspect", "io", "itertools", "json", "logging", "math",
    "os", "pathlib", "pickle", "random", "re", "shutil", "socket", "sqlite3",
    "string", "subprocess", "sys", "tempfile", "threading", "time", "traceback",
    "types", "typing", "unittest", "urllib", "uuid", "warnings", "__future__",
}
STDLIB = set(getattr(sys, "stdlib_module_names", ())) or _FALLBACK_STDLIB

JS_EXTENSIONS = (".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs")


def _common_prefix_len(a, b):
    count = 0
    for x, y in zip(a.split("/"), b.split("/")):
        if x != y:
            break
        count += 1
    return count


class ResolveContext:
    """Resolves import statements to files inside the analysed repository."""

    def __init__(self, paths):
        self.paths = set(paths)
        self.py_index = defaultdict(list)
        for path in sorted(self.paths):
            if path.endswith(".py"):
                parts = path[:-3].split("/")
                if parts[-1] == "__init__":
                    parts = parts[:-1]
                for i in range(len(parts)):
                    self.py_index[".".join(parts[i:])].append(path)

    # ---- Python helpers -------------------------------------------------
    def _lookup_py(self, key, from_path):
        candidates = self.py_index.get(key)
        if not candidates:
            return None
        if len(candidates) == 1:
            return candidates[0]
        return max(candidates, key=lambda c: (_common_prefix_len(c, from_path), -len(c)))

    def _py_file(self, base):
        options = ["%s.py" % base, "%s/__init__.py" % base] if base else ["__init__.py"]
        for option in options:
            if option in self.paths:
                return option
        return None

    @staticmethod
    def _relative_base(path, module, level):
        base = posixpath.dirname(path)
        for _ in range(max(level - 1, 0)):
            base = posixpath.dirname(base)
        if module:
            base = posixpath.join(base, module.replace(".", "/"))
        base = posixpath.normpath(base) if base else ""
        return "" if base == "." else base

    def _bindings_py(self, path, imp):
        bindings, externals = [], []
        module, level = imp["module"], imp["level"]

        if imp["kind"] == "import":
            top = module.split(".")[0]
            if top in STDLIB:
                return bindings, externals
            target = self._lookup_py(module, path)
            if target:
                bindings.append({
                    "local": imp.get("asname") or module, "target": target, "symbol": None,
                })
            else:
                externals.append(top)
            return bindings, externals

        # "from X import a, b"
        if level > 0:
            base = self._relative_base(path, module, level)
            module_file = self._py_file(base)
            for item in imp["names"]:
                name = item["name"]
                local = item["asname"] or name
                sub = self._py_file(posixpath.join(base, name) if base else name)
                if sub:
                    bindings.append({"local": local, "target": sub, "symbol": None})
                elif module_file:
                    bindings.append({"local": local, "target": module_file, "symbol": name})
            return bindings, externals

        top = module.split(".")[0] if module else ""
        if not top or top in STDLIB:
            return bindings, externals
        module_file = self._lookup_py(module, path)
        resolved_any = False
        for item in imp["names"]:
            name = item["name"]
            local = item["asname"] or name
            sub = self._lookup_py("%s.%s" % (module, name), path)
            if sub:
                bindings.append({"local": local, "target": sub, "symbol": None})
                resolved_any = True
            elif module_file:
                bindings.append({"local": local, "target": module_file, "symbol": name})
                resolved_any = True
        if not resolved_any and module_file:
            bindings.append({"local": module.split(".")[-1], "target": module_file, "symbol": None})
            resolved_any = True
        if not resolved_any:
            externals.append(top)
        return bindings, externals

    # ---- JavaScript helpers ----------------------------------------------
    def _js_file(self, base):
        if base in self.paths:
            return base
        for ext in JS_EXTENSIONS:
            if base + ext in self.paths:
                return base + ext
        for ext in JS_EXTENSIONS:
            candidate = "%s/index%s" % (base, ext)
            if candidate in self.paths:
                return candidate
        return None

    def _bindings_js(self, path, spec):
        bindings, externals = [], []
        if spec.startswith("."):
            base = posixpath.normpath(posixpath.join(posixpath.dirname(path), spec))
            target = self._js_file(base)
            if target:
                bindings.append({"local": None, "target": target, "symbol": None})
        elif spec.startswith("@/") or spec.startswith("~/"):
            rest = spec[2:]
            matches = []
            for candidate in sorted(self.paths):
                for ext in ("",) + JS_EXTENSIONS:
                    full = rest + ext
                    if candidate == full or candidate.endswith("/" + full):
                        matches.append(candidate)
            if matches:
                bindings.append({"local": None, "target": min(matches, key=len), "symbol": None})
        elif spec.startswith(("node:", "http:", "https:", "/")):
            pass
        else:
            parts = spec.split("/")
            package = "/".join(parts[:2]) if spec.startswith("@") and len(parts) > 1 else parts[0]
            externals.append(package)
        return bindings, externals

    def resolve(self, path, imp):
        if imp["kind"] == "js":
            return self._bindings_js(path, imp["module"])
        return self._bindings_py(path, imp)


def build_graph(parsed):
    """Return (DiGraph, bindings_by_file, Counter of external packages)."""
    context = ResolveContext(parsed.keys())
    graph = nx.DiGraph()
    bindings_by_file = {}
    external = Counter()

    for path in sorted(parsed):
        graph.add_node(path, language=parsed[path]["language"])

    for path in sorted(parsed):
        file_bindings, file_external = [], set()
        for imp in parsed[path]["imports"]:
            bindings, externals = context.resolve(path, imp)
            file_bindings.extend(bindings)
            file_external.update(externals)
        bindings_by_file[path] = file_bindings
        for package in file_external:
            external[package] += 1
        for binding in file_bindings:
            target = binding["target"]
            if target == path:
                continue
            if graph.has_edge(path, target):
                graph[path][target]["weight"] += 1
            else:
                graph.add_edge(path, target, weight=1)
    return graph, bindings_by_file, external


def pagerank(graph, damping=0.85, iterations=50):
    """Tiny power-iteration PageRank (avoids the SciPy dependency)."""
    count = graph.number_of_nodes()
    if count == 0:
        return {}
    rank = {node: 1.0 / count for node in graph}
    for _ in range(iterations):
        dangling = sum(rank[n] for n in graph if graph.out_degree(n) == 0)
        updated = {}
        for node in graph:
            incoming = sum(rank[u] / graph.out_degree(u) for u in graph.predecessors(node))
            updated[node] = (1 - damping) / count + damping * (incoming + dangling / count)
        rank = updated
    return rank


def compute_metrics(graph):
    importance = pagerank(graph)
    most_imported = sorted(
        ((n, graph.in_degree(n)) for n in graph if graph.in_degree(n) > 0),
        key=lambda item: (-item[1], item[0]),
    )[:8]
    most_dependent = sorted(
        ((n, graph.out_degree(n)) for n in graph if graph.out_degree(n) > 0),
        key=lambda item: (-item[1], item[0]),
    )[:8]
    circular = [
        sorted(group)
        for group in nx.strongly_connected_components(graph)
        if len(group) > 1
    ][:10]
    return importance, {
        "most_imported": [{"file": n, "imported_by": d} for n, d in most_imported],
        "most_dependent": [{"file": n, "imports": d} for n, d in most_dependent],
        "circular_groups": circular,
    }


_ROLE_KEYWORDS = [
    ("test", "Tests"),
    ("route", "API layer"), ("router", "API layer"), ("api", "API layer"),
    ("controller", "API layer"), ("endpoint", "API layer"),
    ("agent", "AI agents"), ("llm", "AI / LLM"), ("model", "Models / data"),
    ("schema", "Models / data"), ("entity", "Models / data"), ("db", "Data access"),
    ("database", "Data access"), ("repositor", "Data access"),
    ("service", "Business logic"), ("core", "Business logic"), ("logic", "Business logic"),
    ("util", "Utilities"), ("helper", "Utilities"), ("common", "Utilities"),
    ("lib", "Utilities"), ("config", "Configuration"), ("setting", "Configuration"),
    ("component", "UI components"), ("page", "UI pages"), ("view", "UI views"),
    ("hook", "UI hooks"), ("frontend", "Frontend"), ("backend", "Backend"),
]


def guess_role(directory):
    lowered = directory.lower()
    for keyword, role in _ROLE_KEYWORDS:
        if keyword in lowered:
            return role
    return "Module"


def build_components(parsed, graph):
    groups = defaultdict(list)
    component_of = {}
    for path in parsed:
        name = posixpath.dirname(path) or "(root)"
        groups[name].append(path)
        component_of[path] = name

    deps = defaultdict(Counter)
    for source, target in graph.edges:
        a, b = component_of.get(source), component_of.get(target)
        if a and b and a != b:
            deps[a][b] += 1

    components = []
    for name, files in groups.items():
        components.append({
            "name": name,
            "role": guess_role(name),
            "files": len(files),
            "classes": sum(len(parsed[f]["classes"]) for f in files),
            "functions": sum(len(parsed[f]["functions"]) for f in files),
            "depends_on": [k for k, _ in deps[name].most_common(5)],
        })
    components.sort(key=lambda c: (-c["files"], c["name"]))
    return components[:30]


def build_modules(parsed, graph, importance):
    modules = []
    for path, info in parsed.items():
        modules.append({
            "path": path,
            "language": info["language"],
            "lines": info["lines"],
            "classes": [c["name"] for c in info["classes"]][:10],
            "functions": [f["name"] for f in info["functions"]][:10],
            "class_count": len(info["classes"]),
            "function_count": len(info["functions"]),
            "imports_internal": graph.out_degree(path),
            "imported_by": graph.in_degree(path),
            "importance": round(importance.get(path, 0.0), 4),
            "parse_error": info["error"],
        })
    modules.sort(key=lambda m: (-m["importance"], m["path"]))
    return modules[:100]
