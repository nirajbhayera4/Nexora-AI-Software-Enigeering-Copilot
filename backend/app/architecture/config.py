"""Configuration for the Repository Architecture Analysis module."""
import os


def _int_env(name, default):
    try:
        return int(os.getenv(name, str(default)))
    except ValueError:
        return default


GITHUB_API = "https://api.github.com"
RAW_BASE = "https://raw.githubusercontent.com"
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "").strip()

OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434").rstrip("/")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5-coder:3b")
OLLAMA_TIMEOUT = _int_env("ARCH_OLLAMA_TIMEOUT", 90)

REQUEST_TIMEOUT = 20
MAX_FILES = _int_env("ARCH_MAX_FILES", 80)
MAX_FILE_BYTES = 200_000
FETCH_WORKERS = 8

IGNORED_DIRS = {
    ".git", "node_modules", "dist", "build", "__pycache__", ".venv", "venv",
    "env", ".idea", ".vscode", ".next", "coverage", ".pytest_cache",
    ".mypy_cache", "site-packages", "vendor", "target", ".gradle",
}
IGNORED_FILES = {"package-lock.json", "yarn.lock", "pnpm-lock.yaml", "poetry.lock"}
IGNORED_SUFFIXES = (".min.js", ".lock", ".map", ".d.ts")

LANGUAGES = {
    ".py": "Python", ".js": "JavaScript", ".jsx": "JavaScript",
    ".mjs": "JavaScript", ".cjs": "JavaScript", ".ts": "TypeScript",
    ".tsx": "TypeScript", ".java": "Java", ".go": "Go", ".rs": "Rust",
    ".c": "C", ".h": "C", ".cpp": "C++", ".cs": "C#", ".rb": "Ruby",
    ".php": "PHP", ".kt": "Kotlin", ".swift": "Swift", ".html": "HTML",
    ".css": "CSS", ".scss": "CSS", ".sh": "Shell", ".sql": "SQL",
}
PARSEABLE_EXTENSIONS = {".py", ".js", ".jsx", ".mjs", ".cjs", ".ts", ".tsx"}

ENTRY_POINT_NAMES = {
    "main.py", "app.py", "server.py", "manage.py", "wsgi.py", "asgi.py",
    "index.js", "index.jsx", "index.ts", "index.tsx", "main.js", "main.jsx",
    "main.ts", "main.tsx", "app.js", "app.jsx", "app.tsx", "server.js",
}
MANIFEST_NAMES = {"requirements.txt", "package.json", "pyproject.toml"}

TECH_KEYWORDS = {
    "fastapi": "FastAPI", "flask": "Flask", "django": "Django",
    "uvicorn": "Uvicorn", "sqlalchemy": "SQLAlchemy", "pydantic": "Pydantic",
    "langchain": "LangChain", "ollama": "Ollama", "networkx": "NetworkX",
    "tree-sitter": "Tree-sitter", "semgrep": "Semgrep", "pylint": "Pylint",
    "bandit": "Bandit", "ruff": "Ruff", "react": "React", "vue": "Vue",
    "vite": "Vite", "next": "Next.js", "express": "Express",
    "tailwindcss": "Tailwind CSS", "mermaid": "Mermaid.js",
    "typescript": "TypeScript", "axios": "Axios",
}
