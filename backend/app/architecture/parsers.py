"""Source parsers (Task 2: identify modules and components).

Python  -> built-in `ast` module
JS / TS -> Tree-sitter (with a regex fallback when Tree-sitter is unavailable)

Every parser returns the same dictionary shape:
    {
      "path", "language", "lines", "error",
      "imports":   [{"kind", "module", "level", "names": [{"name","asname"}], "asname"}],
      "classes":   [{"name", "bases": [], "methods": [], "line"}],
      "functions": [{"name", "line", "calls": [{"name","obj"}], "route": {...}|None}],
    }
"""
import ast
import posixpath
import re
from functools import lru_cache

HTTP_METHODS = {"get", "post", "put", "delete", "patch", "options", "head"}


def _empty(path, language, source):
    return {
        "path": path,
        "language": language,
        "lines": source.count("\n") + 1 if source else 0,
        "imports": [],
        "classes": [],
        "functions": [],
        "error": None,
    }


# --------------------------------------------------------------------------
# Python (ast)
# --------------------------------------------------------------------------
def _calls_in(node):
    found = []
    for sub in ast.walk(node):
        if not isinstance(sub, ast.Call):
            continue
        func = sub.func
        if isinstance(func, ast.Name):
            key = (func.id, None)
        elif isinstance(func, ast.Attribute):
            obj = func.value.id if isinstance(func.value, ast.Name) else None
            key = (func.attr, obj)
        else:
            continue
        found.append((getattr(sub, "lineno", 0), getattr(sub, "col_offset", 0), key))
    found.sort(key=lambda item: (item[0], item[1]))
    seen, calls = set(), []
    for _, _, key in found:
        if key not in seen:
            seen.add(key)
            calls.append({"name": key[0], "obj": key[1]})
    return calls


def _route_of(func_node):
    for dec in func_node.decorator_list:
        if isinstance(dec, ast.Call) and isinstance(dec.func, ast.Attribute):
            attr = dec.func.attr.lower()
            if attr in HTTP_METHODS or attr == "route":
                path = "/"
                if dec.args and isinstance(dec.args[0], ast.Constant) \
                        and isinstance(dec.args[0].value, str):
                    path = dec.args[0].value
                return {"method": "GET" if attr == "route" else attr.upper(), "path": path}
    return None


def parse_python(path, source):
    info = _empty(path, "Python", source)
    try:
        tree = ast.parse(source)
    except Exception as exc:  # SyntaxError, ValueError (null bytes), RecursionError
        info["error"] = "%s: %s" % (type(exc).__name__, exc)
        return info

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                info["imports"].append({
                    "kind": "import", "module": alias.name, "level": 0,
                    "names": [], "asname": alias.asname,
                })
        elif isinstance(node, ast.ImportFrom):
            info["imports"].append({
                "kind": "from", "module": node.module or "", "level": node.level or 0,
                "names": [{"name": a.name, "asname": a.asname} for a in node.names],
                "asname": None,
            })

    for node in tree.body:
        if isinstance(node, ast.ClassDef):
            bases = []
            for base in node.bases:
                try:
                    bases.append(ast.unparse(base))
                except Exception:
                    continue
            methods = [
                n.name for n in node.body
                if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
            ]
            info["classes"].append({
                "name": node.name, "bases": bases, "methods": methods,
                "line": node.lineno,
            })
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            info["functions"].append({
                "name": node.name, "line": node.lineno,
                "calls": _calls_in(node), "route": _route_of(node),
            })
    return info


# --------------------------------------------------------------------------
# JavaScript / TypeScript (Tree-sitter, regex fallback)
# --------------------------------------------------------------------------
@lru_cache(maxsize=None)
def _get_ts_parser(kind):
    try:
        from tree_sitter import Language, Parser

        if kind == "js":
            import tree_sitter_javascript as mod
            language = Language(mod.language())
        elif kind == "ts":
            import tree_sitter_typescript as mod
            language = Language(mod.language_typescript())
        else:
            import tree_sitter_typescript as mod
            language = Language(mod.language_tsx())
        return Parser(language)
    except Exception:
        return None


def _walk(root):
    stack = [root]
    while stack:
        node = stack.pop()
        yield node
        stack.extend(reversed(node.children))


def _text(node):
    if node is None:
        return ""
    return node.text.decode("utf-8", errors="ignore")


def _unquote(value):
    return value.strip().strip("'\"`")


def _first_string(node):
    if node is None:
        return None
    for child in node.children:
        if child.type in ("string", "template_string"):
            return _unquote(_text(child))
    return None


def _parse_js_tree_sitter(info, source, kind):
    parser = _get_ts_parser(kind)
    if parser is None:
        return False
    try:
        tree = parser.parse(source.encode("utf-8"))
    except Exception:
        return False

    seen_imports = set()

    def add_import(spec):
        if spec and spec not in seen_imports:
            seen_imports.add(spec)
            info["imports"].append({
                "kind": "js", "module": spec, "level": 0, "names": [], "asname": None,
            })

    for node in _walk(tree.root_node):
        ntype = node.type
        if ntype in ("import_statement", "export_statement"):
            src = node.child_by_field_name("source")
            if src is not None:
                add_import(_unquote(_text(src)))
        elif ntype == "call_expression":
            fn = node.child_by_field_name("function")
            if fn is not None and (
                (fn.type == "identifier" and _text(fn) == "require") or fn.type == "import"
            ):
                add_import(_first_string(node.child_by_field_name("arguments")))
        elif ntype in ("class_declaration", "abstract_class_declaration"):
            name = _text(node.child_by_field_name("name"))
            if not name:
                continue
            bases = []
            for child in node.children:
                if child.type == "class_heritage":
                    heritage = _text(child).replace("extends", "", 1).strip()
                    if heritage:
                        bases.append(heritage.split("implements")[0].strip())
            methods = []
            body = node.child_by_field_name("body")
            if body is not None:
                for member in body.children:
                    if member.type in ("method_definition", "method_signature"):
                        mname = _text(member.child_by_field_name("name"))
                        if mname:
                            methods.append(mname)
            info["classes"].append({
                "name": name, "bases": bases, "methods": methods,
                "line": node.start_point[0] + 1,
            })
        elif ntype == "function_declaration":
            name = _text(node.child_by_field_name("name"))
            if name:
                info["functions"].append({
                    "name": name, "line": node.start_point[0] + 1,
                    "calls": [], "route": None,
                })
        elif ntype == "variable_declarator":
            value = node.child_by_field_name("value")
            name_node = node.child_by_field_name("name")
            if value is not None and name_node is not None and name_node.type == "identifier" \
                    and value.type in ("arrow_function", "function_expression", "function"):
                info["functions"].append({
                    "name": _text(name_node), "line": node.start_point[0] + 1,
                    "calls": [], "route": None,
                })
    return True


_JS_IMPORT_PATTERNS = [
    re.compile(r"""\bimport\s+[^'";]*?\bfrom\s*['"]([^'"]+)['"]"""),
    re.compile(r"""\bimport\s*['"]([^'"]+)['"]"""),
    re.compile(r"""\bexport\s+[^'";]*?\bfrom\s*['"]([^'"]+)['"]"""),
    re.compile(r"""\brequire\(\s*['"]([^'"]+)['"]\s*\)"""),
    re.compile(r"""\bimport\(\s*['"]([^'"]+)['"]\s*\)"""),
]
_JS_CLASS = re.compile(
    r"^\s*(?:export\s+)?(?:default\s+)?(?:abstract\s+)?class\s+([A-Za-z_$][\w$]*)"
    r"(?:\s+extends\s+([A-Za-z_$][\w$.]*))?",
    re.MULTILINE,
)
_JS_FUNC = re.compile(
    r"^\s*(?:export\s+)?(?:default\s+)?(?:async\s+)?function\s*\*?\s*([A-Za-z_$][\w$]*)",
    re.MULTILINE,
)
_JS_ARROW = re.compile(
    r"^\s*(?:export\s+)?(?:const|let|var)\s+([A-Za-z_$][\w$]*)\s*=\s*(?:async\s*)?"
    r"(?:\([^)]*\)|[A-Za-z_$][\w$]*)\s*=>",
    re.MULTILINE,
)


def _parse_js_regex(info, source):
    seen = set()
    for pattern in _JS_IMPORT_PATTERNS:
        for match in pattern.finditer(source):
            spec = match.group(1)
            if spec not in seen:
                seen.add(spec)
                info["imports"].append({
                    "kind": "js", "module": spec, "level": 0, "names": [], "asname": None,
                })
    for match in _JS_CLASS.finditer(source):
        info["classes"].append({
            "name": match.group(1),
            "bases": [match.group(2)] if match.group(2) else [],
            "methods": [],
            "line": source.count("\n", 0, match.start()) + 1,
        })
    for pattern in (_JS_FUNC, _JS_ARROW):
        for match in pattern.finditer(source):
            info["functions"].append({
                "name": match.group(1),
                "line": source.count("\n", 0, match.start()) + 1,
                "calls": [], "route": None,
            })


def parse_javascript(path, source):
    ext = posixpath.splitext(path)[1].lower()
    language = "TypeScript" if ext in (".ts", ".tsx") else "JavaScript"
    info = _empty(path, language, source)
    kind = {".ts": "ts", ".tsx": "tsx"}.get(ext, "js")
    try:
        if not _parse_js_tree_sitter(info, source, kind):
            info["imports"], info["classes"], info["functions"] = [], [], []
            _parse_js_regex(info, source)
    except Exception as exc:
        info["error"] = "%s: %s" % (type(exc).__name__, exc)
    return info


def parse_file(path, source):
    ext = posixpath.splitext(path)[1].lower()
    if ext == ".py":
        return parse_python(path, source)
    return parse_javascript(path, source)
