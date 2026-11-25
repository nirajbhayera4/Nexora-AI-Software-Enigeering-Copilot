"""Mermaid diagram generators (Task 5: UML class and sequence diagrams)."""
import posixpath
import re
from collections import OrderedDict

MAX_DEP_NODES = 40
MAX_DEP_EDGES = 120
MAX_CLASSES = 25
MAX_METHODS = 8
MAX_SEQ_LINES = 70


def _ident(value):
    cleaned = re.sub(r"\W", "_", value)
    if not cleaned or cleaned[0].isdigit():
        cleaned = "n_" + cleaned
    return cleaned


def _label(value):
    return re.sub(r"[\"\[\]{}()<>;#|]", "", value).strip() or "item"


def _short(path):
    parts = path.split("/")
    return "/".join(parts[-2:])


# --------------------------------------------------------------------------
# Dependency diagram (flowchart)
# --------------------------------------------------------------------------
def dependency_diagram(graph):
    if graph.number_of_nodes() == 0:
        return 'flowchart LR\n  empty["No source files found"]'

    connected = [n for n in graph if graph.degree(n) > 0]
    pool = connected if connected else list(graph.nodes)
    chosen = sorted(pool, key=lambda n: (-graph.degree(n), n))[:MAX_DEP_NODES]
    chosen_set = set(chosen)
    ids = {node: "n%d" % i for i, node in enumerate(sorted(chosen))}

    groups = OrderedDict()
    for node in sorted(chosen):
        top = node.split("/")[0] if "/" in node else ""
        groups.setdefault(top, []).append(node)

    lines = ["flowchart LR"]
    for gi, (top, nodes) in enumerate(groups.items()):
        indent = "  "
        if top:
            lines.append('  subgraph grp_%d["%s"]' % (gi, _label(top)))
            indent = "    "
        for node in nodes:
            lines.append('%s%s["%s"]' % (indent, ids[node], _label(node)))
        if top:
            lines.append("  end")

    edge_count = 0
    for source, target in sorted(graph.edges):
        if source in chosen_set and target in chosen_set:
            lines.append("  %s --> %s" % (ids[source], ids[target]))
            edge_count += 1
            if edge_count >= MAX_DEP_EDGES:
                break
    return "\n".join(lines)


# --------------------------------------------------------------------------
# Class diagram
# --------------------------------------------------------------------------
def _base_name(base):
    base = re.sub(r"\[.*\]", "", base)
    base = base.split("(")[0].split(".")[-1].strip()
    return base


def class_diagram(parsed):
    classes = []
    for path in sorted(parsed):
        for cls in parsed[path]["classes"]:
            classes.append((path, cls))

    lines = ["classDiagram"]
    if classes:
        used = {}
        names = {}
        for path, cls in classes[:MAX_CLASSES]:
            base = _ident(cls["name"])
            count = used.get(base, 0)
            used[base] = count + 1
            names[(path, cls["name"])] = base if count == 0 else "%s_%d" % (base, count + 1)

        local_names = set(names.values())
        for path, cls in classes[:MAX_CLASSES]:
            ident = names[(path, cls["name"])]
            lines.append("  class %s {" % ident)
            for method in cls["methods"][:MAX_METHODS]:
                lines.append("    +%s()" % _ident(method))
            lines.append("  }")
        for path, cls in classes[:MAX_CLASSES]:
            ident = names[(path, cls["name"])]
            for base in cls["bases"]:
                base_ident = _ident(_base_name(base))
                if base_ident and base_ident not in ("object", "n_") and base_ident != ident:
                    if base_ident not in local_names:
                        lines.append("  class %s" % base_ident)
                        local_names.add(base_ident)
                    lines.append("  %s <|-- %s" % (base_ident, ident))
        return "\n".join(lines)

    # No classes anywhere: show modules and their functions instead.
    shown = 0
    for path in sorted(parsed):
        funcs = parsed[path]["functions"]
        if not funcs:
            continue
        ident = _ident(path)
        lines.append("  class %s {" % ident)
        lines.append("    <<module>>")
        for func in funcs[:MAX_METHODS]:
            lines.append("    +%s()" % _ident(func["name"]))
        lines.append("  }")
        shown += 1
        if shown >= MAX_CLASSES:
            break
    if shown == 0:
        lines.append("  class NoClassesFound")
    return "\n".join(lines)


# --------------------------------------------------------------------------
# Sequence diagram
# --------------------------------------------------------------------------
class _Sequence:
    def __init__(self):
        self.participants = OrderedDict()  # path -> id
        self.body = []

    def pid(self, path):
        if path not in self.participants:
            self.participants[path] = "P%d" % (len(self.participants) + 1)
        return self.participants[path]

    def full(self):
        return len(self.body) >= MAX_SEQ_LINES

    def render(self):
        lines = ["sequenceDiagram", "  actor Client"]
        for path, pid in self.participants.items():
            lines.append("  participant %s as %s" % (pid, _label(_short(path))))
        lines.extend(self.body)
        return "\n".join(lines)


def _resolve_call(call, path, funcs, bindings):
    """Return (target_path, target_function_dict_or_None) or None if unresolved."""
    name, obj = call["name"], call["obj"]
    if obj is None:
        if name in funcs.get(path, {}):
            return path, funcs[path][name]
        for binding in bindings.get(path, []):
            if binding["local"] == name and binding["symbol"]:
                target = binding["target"]
                return target, funcs.get(target, {}).get(binding["symbol"])
        return None
    for binding in bindings.get(path, []):
        if binding["local"] == obj:
            target = binding["target"]
            return target, funcs.get(target, {}).get(name)
    return None


def _emit_calls(seq, path, func, depth, stack, funcs, bindings):
    resolved_calls = []
    for call in func["calls"]:
        resolved = _resolve_call(call, path, funcs, bindings)
        if resolved:
            resolved_calls.append((call, resolved))
    for call, resolved in resolved_calls[:6]:
        if seq.full():
            return
        target, target_func = resolved
        src, dst = seq.pid(path), seq.pid(target)
        label = _label(call["name"]) + "()"
        seq.body.append("  %s->>%s: %s" % (src, dst, label))
        key = (target, call["name"])
        if target_func is not None and depth > 1 and key not in stack:
            _emit_calls(seq, target, target_func, depth - 1, stack | {key}, funcs, bindings)
        if not seq.full():
            seq.body.append("  %s-->>%s: result" % (dst, src))


def _import_sequence(graph):
    seq = _Sequence()
    if graph.number_of_nodes() == 0:
        return "sequenceDiagram\n  actor Client\n  Note over Client: No source files found", "none"
    roots = [n for n in graph if graph.in_degree(n) == 0 and graph.out_degree(n) > 0]
    pool = roots or [n for n in graph if graph.out_degree(n) > 0]
    if not pool:
        return "sequenceDiagram\n  actor Client\n  Note over Client: No dependencies detected", "none"
    entry = sorted(pool, key=lambda n: (-graph.out_degree(n), n))[0]
    seq.body.append("  Client->>%s: start" % seq.pid(entry))
    visited = {entry}
    queue = [entry]
    while queue and not seq.full():
        current = queue.pop(0)
        for target in sorted(graph.successors(current)):
            if seq.full():
                break
            seq.body.append("  %s->>%s: imports" % (seq.pid(current), seq.pid(target)))
            if target not in visited and len(visited) < 12:
                visited.add(target)
                queue.append(target)
    return seq.render(), "imports"


def sequence_diagram(parsed, graph, bindings, max_routes=3, depth=3):
    """Return (mermaid_text, source) where source is 'routes', 'imports' or 'none'."""
    funcs = {
        path: OrderedDict((f["name"], f) for f in info["functions"])
        for path, info in parsed.items()
    }
    routes = [
        (path, func)
        for path in sorted(parsed)
        for func in parsed[path]["functions"]
        if func.get("route")
    ]
    if not routes:
        return _import_sequence(graph)

    def resolved_count(item):
        route_path, route_func = item
        return sum(
            1 for call in route_func["calls"]
            if _resolve_call(call, route_path, funcs, bindings)
        )

    # Prefer routes that actually call into other modules, keep file order.
    ranked = sorted(routes, key=lambda item: -resolved_count(item))[:max_routes]
    chosen = [item for item in routes if item in ranked]

    seq = _Sequence()
    for path, func in chosen:
        if seq.full():
            break
        route = func["route"]
        entry = seq.pid(path)
        seq.body.append(
            "  Client->>%s: %s %s" % (entry, route["method"], _label(route["path"]))
        )
        _emit_calls(seq, path, func, depth, {(path, func["name"])}, funcs, bindings)
        seq.body.append("  %s-->>Client: response" % entry)
    return seq.render(), "routes"
