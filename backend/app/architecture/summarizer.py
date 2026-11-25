"""Architecture summaries (Task 4) generated with Ollama + Qwen 2.5 Coder.

If Ollama is not running, a deterministic summary is returned instead so the
endpoint never fails because of the LLM.
"""
import requests

from .config import OLLAMA_HOST, OLLAMA_MODEL, OLLAMA_TIMEOUT


def _facts(analysis):
    structure = analysis["structure"]
    langs = ", ".join(
        "%s %s%%" % (l["language"], l["percent"]) for l in structure["languages"][:5]
    ) or "unknown"
    folders = ", ".join(
        "%s (%d files)" % (f["name"], f["files"]) for f in structure["top_level_folders"][:8]
    ) or "none"
    comps = "; ".join(
        "%s [%s] %d files" % (c["name"], c["role"], c["files"])
        for c in analysis["components"][:10]
    ) or "none"
    deps = analysis["dependencies"]
    core = ", ".join(
        "%s (used by %d)" % (m["file"], m["imported_by"]) for m in deps["most_imported"][:5]
    ) or "none"
    external = ", ".join(
        "%s" % e["name"] for e in deps["external_packages"][:10]
    ) or "none"
    cycles = len(deps["circular_groups"])
    return {
        "languages": langs,
        "folders": folders,
        "components": comps,
        "core": core,
        "external": external,
        "cycles": cycles,
        "tech": ", ".join(analysis["technologies"]) or "not detected",
        "entries": ", ".join(structure["entry_points"][:5]) or "not detected",
    }


def static_summary(analysis):
    f = _facts(analysis)
    repo = analysis["repository"]["name"]
    stats = analysis["stats"]
    parts = [
        "%s is a repository with %d files; %d source files were analysed. "
        "Main languages: %s." % (
            repo, stats["total_files"], stats["analyzed_files"], f["languages"]
        ),
        "Detected technologies: %s. Entry points: %s." % (f["tech"], f["entries"]),
        "Top-level folders: %s." % f["folders"],
        "Main components: %s." % f["components"],
        "Most depended-on files: %s." % f["core"],
        "External packages used: %s." % f["external"],
    ]
    if f["cycles"]:
        parts.append(
            "Warning: %d group(s) of files import each other in a cycle." % f["cycles"]
        )
    else:
        parts.append("No circular dependencies were detected between analysed files.")
    return "\n\n".join(parts)


def _prompt(analysis):
    f = _facts(analysis)
    return (
        "You are a senior software architect. Using ONLY the facts below, write a "
        "clear architecture summary in under 200 words with these headings: "
        "Overview, Main Components, How Data Flows, Risks. Do not invent files.\n\n"
        "Repository: %s\nLanguages: %s\nTechnologies: %s\nEntry points: %s\n"
        "Top-level folders: %s\nComponents: %s\nMost depended-on files: %s\n"
        "External packages: %s\nCircular dependency groups: %d\n"
        % (
            analysis["repository"]["name"], f["languages"], f["tech"], f["entries"],
            f["folders"], f["components"], f["core"], f["external"], f["cycles"],
        )
    )


def generate_summary(analysis):
    """Return (text, source) where source is 'ollama' or 'static'."""
    try:
        response = requests.post(
            OLLAMA_HOST + "/api/generate",
            json={
                "model": OLLAMA_MODEL,
                "prompt": _prompt(analysis),
                "stream": False,
                "options": {"temperature": 0.2, "num_predict": 500},
            },
            timeout=OLLAMA_TIMEOUT,
        )
        if response.status_code == 200:
            text = (response.json().get("response") or "").strip()
            if text:
                return text, "ollama"
    except (requests.RequestException, ValueError):
        pass
    return static_summary(analysis), "static"
