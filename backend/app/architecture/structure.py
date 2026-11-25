"""Directory-structure analysis (Task 1: analyze project directory structure)."""
import posixpath
from collections import Counter

from .config import (
    ENTRY_POINT_NAMES, IGNORED_DIRS, IGNORED_FILES, IGNORED_SUFFIXES, LANGUAGES,
)

MAX_TREE_DEPTH = 4
MAX_CHILDREN = 30
MAX_TEXT_LINES = 90


def is_ignored(path):
    parts = path.split("/")
    if any(part in IGNORED_DIRS for part in parts[:-1]):
        return True
    name = parts[-1]
    return name in IGNORED_FILES or name.endswith(IGNORED_SUFFIXES)


def extension(path):
    return posixpath.splitext(path)[1].lower()


def _nest(paths):
    root = {}
    for path in paths:
        node = root
        parts = path.split("/")
        for part in parts[:-1]:
            child = node.setdefault(part, {})
            if child is None:  # file/dir name clash, should not happen in git
                child = node[part] = {}
            node = child
        node.setdefault(parts[-1], None)
    return root


def _count(node):
    if node is None:
        return 1
    return sum(_count(child) for child in node.values())


def _to_tree(name, node, depth):
    if node is None:
        return {"name": name, "type": "file"}
    if depth >= MAX_TREE_DEPTH:
        return {"name": name, "type": "dir", "children": [], "hidden": _count(node)}
    items = sorted(node.items(), key=lambda kv: (kv[1] is None, kv[0].lower()))
    children = [_to_tree(k, v, depth + 1) for k, v in items[:MAX_CHILDREN]]
    return {
        "name": name,
        "type": "dir",
        "children": children,
        "hidden": max(0, len(items) - MAX_CHILDREN),
    }


def _render(tree, prefix, lines):
    kids = tree.get("children", [])
    hidden = tree.get("hidden", 0)
    for index, kid in enumerate(kids):
        if len(lines) >= MAX_TEXT_LINES:
            return
        last = index == len(kids) - 1 and not hidden
        branch = "└── " if last else "├── "
        suffix = "/" if kid["type"] == "dir" else ""
        lines.append(prefix + branch + kid["name"] + suffix)
        if kid["type"] == "dir":
            _render(kid, prefix + ("    " if last else "│   "), lines)
    if hidden and len(lines) < MAX_TEXT_LINES:
        lines.append(prefix + "└── … %d more" % hidden)


def build_structure(blobs, repo_name):
    paths = [b["path"] for b in blobs]
    root = _to_tree(repo_name, _nest(paths), 0)

    lines = [repo_name + "/"]
    _render(root, "", lines)
    if len(lines) >= MAX_TEXT_LINES:
        lines.append("… (tree truncated)")

    counts = Counter()
    for path in paths:
        language = LANGUAGES.get(extension(path))
        if language:
            counts[language] += 1
    total_known = sum(counts.values()) or 1
    languages = [
        {"language": lang, "files": n, "percent": round(100.0 * n / total_known, 1)}
        for lang, n in counts.most_common()
    ]

    top_level = Counter(p.split("/")[0] for p in paths if "/" in p)
    entry_points = [
        p for p in paths if posixpath.basename(p).lower() in ENTRY_POINT_NAMES
    ][:8]

    return {
        "total_files": len(paths),
        "languages": languages,
        "top_level_folders": [
            {"name": name, "files": n} for name, n in top_level.most_common(12)
        ],
        "entry_points": entry_points,
        "tree": root,
        "tree_text": "\n".join(lines),
    }
