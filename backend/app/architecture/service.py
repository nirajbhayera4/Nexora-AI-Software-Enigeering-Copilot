"""Orchestrates the whole architecture analysis pipeline."""
import json
import posixpath
import re

from .config import MANIFEST_NAMES, MAX_FILE_BYTES, MAX_FILES, PARSEABLE_EXTENSIONS, TECH_KEYWORDS
from .diagrams import class_diagram, dependency_diagram, sequence_diagram
from .github_client import (
    fetch_files, get_default_branch, get_tree, parse_repo_url,
)
from .graph_builder import (
    build_components, build_graph, build_modules, compute_metrics,
)
from .parsers import parse_file
from .structure import build_structure, extension, is_ignored
from .summarizer import generate_summary

_TEST_RE = re.compile(r"(^|/)(tests?|__tests__|spec)(/|$)|(^|/)test_[^/]*$|\.(test|spec)\.[jt]sx?$")


def _is_test(path):
    return bool(_TEST_RE.search(path.lower()))


def select_source_files(blobs):
    candidates = [
        b for b in blobs
        if extension(b["path"]) in PARSEABLE_EXTENSIONS and b["size"] <= MAX_FILE_BYTES
    ]
    candidates.sort(key=lambda b: (_is_test(b["path"]), b["path"].count("/"), b["size"], b["path"]))
    return [b["path"] for b in candidates[:MAX_FILES]]


def select_manifests(blobs):
    found = [
        b["path"] for b in blobs
        if posixpath.basename(b["path"]).lower() in MANIFEST_NAMES and b["path"].count("/") <= 2
    ]
    return sorted(found, key=lambda p: (p.count("/"), p))[:6]


def detect_technologies(manifest_texts, parsed, external):
    blob = "\n".join(manifest_texts).lower()
    blob += "\n" + "\n".join(external.keys()).lower()
    found = []
    for keyword, label in TECH_KEYWORDS.items():
        if keyword in blob and label not in found:
            found.append(label)
    languages = sorted({info["language"] for info in parsed.values()})
    for language in languages:
        if language not in found:
            found.append(language)
    return found


def analyze_repository(url):
    owner, repo = parse_repo_url(url)
    branch = get_default_branch(owner, repo)
    blobs, truncated = get_tree(owner, repo, branch)
    blobs = [b for b in blobs if not is_ignored(b["path"])]

    structure = build_structure(blobs, repo)
    selected = select_source_files(blobs)
    manifests = select_manifests(blobs)
    contents = fetch_files(owner, repo, branch, selected + manifests)

    warnings = []
    if truncated:
        warnings.append("GitHub truncated the file tree; very large repositories are only partly analysed.")
    all_source = [b for b in blobs if extension(b["path"]) in PARSEABLE_EXTENSIONS]
    if len(all_source) > len(selected):
        warnings.append(
            "Analysed %d of %d source files (limit ARCH_MAX_FILES)." % (len(selected), len(all_source))
        )

    parsed = {}
    for path in selected:
        source = contents.get(path)
        if source is None:
            warnings.append("Could not download %s." % path)
            continue
        info = parse_file(path, source)
        if info["error"]:
            warnings.append("Could not fully parse %s (%s)." % (path, info["error"]))
        parsed[path] = info

    graph, bindings, external = build_graph(parsed)
    importance, metrics = compute_metrics(graph)

    manifest_texts = [contents[p] for p in manifests if p in contents]
    technologies = detect_technologies(manifest_texts, parsed, external)

    seq_text, seq_source = sequence_diagram(parsed, graph, bindings)

    edges = [
        {"from": u, "to": v, "weight": data.get("weight", 1)}
        for u, v, data in sorted(graph.edges(data=True))
    ][:300]

    result = {
        "repository": {
            "owner": owner, "name": repo, "branch": branch,
            "url": "https://github.com/%s/%s" % (owner, repo),
        },
        "stats": {
            "total_files": structure["total_files"],
            "analyzed_files": len(parsed),
            "tree_truncated": truncated,
            "warnings": warnings,
        },
        "structure": structure,
        "technologies": technologies,
        "modules": build_modules(parsed, graph, importance),
        "components": build_components(parsed, graph),
        "dependencies": {
            "edges": edges,
            "external_packages": [
                {"name": name, "count": count} for name, count in external.most_common(15)
            ],
            **metrics,
        },
        "diagrams": {
            "dependency": dependency_diagram(graph),
            "class": class_diagram(parsed),
            "sequence": seq_text,
            "sequence_source": seq_source,
        },
    }
    text, source = generate_summary(result)
    result["summary"] = {"text": text, "source": source}
    return result
