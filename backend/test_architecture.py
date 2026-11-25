
import os
import sys

import pytest
import requests
from fastapi import FastAPI
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.architecture import router  # noqa: E402
from app.architecture import service, summarizer  # noqa: E402
from app.architecture.diagrams import class_diagram, dependency_diagram, sequence_diagram  # noqa: E402
from app.architecture.github_client import GitHubError, parse_repo_url  # noqa: E402
from app.architecture.graph_builder import build_graph, compute_metrics  # noqa: E402
from app.architecture.parsers import parse_file  # noqa: E402
from app.architecture.structure import is_ignored  # noqa: E402

FAKE_REPO = {
    "backend/app/__init__.py": "",
    "backend/app/main.py": (
        "from fastapi import FastAPI\n"
        "from app.routes.items import router\n"
        "app = FastAPI()\n"
        "app.include_router(router)\n"
    ),
    "backend/app/routes/__init__.py": "",
    "backend/app/routes/items.py": (
        "from fastapi import APIRouter\n"
        "from app.services.item_service import list_items\n"
        "router = APIRouter()\n"
        "@router.get('/items')\n"
        "def get_items():\n"
        "    return list_items()\n"
    ),
    "backend/app/services/__init__.py": "",
    "backend/app/services/item_service.py": (
        "from . import helpers\n"
        "class ItemBase:\n"
        "    def save(self): pass\n"
        "class Item(ItemBase):\n"
        "    def load(self): pass\n"
        "def list_items():\n"
        "    return helpers.clean([])\n"
    ),
    "backend/app/services/helpers.py": "def clean(x):\n    return x\n",
    "backend/broken.py": "def oops(:\n",
    "frontend/src/App.jsx": (
        "import Home from './pages/Home';\n"
        "export default function App() { return null; }\n"
    ),
    "frontend/src/pages/Home.jsx": (
        "import axios from 'axios';\n"
        "export default function Home() { return null; }\n"
    ),
    "frontend/package.json": '{"dependencies": {"react": "1", "axios": "1"}}',
    "README.md": "# demo",
}


@pytest.fixture
def client(monkeypatch):
    """A test client whose GitHub and Ollama calls are replaced by fake data."""
    monkeypatch.setattr(service, "get_default_branch", lambda owner, repo: "main")
    monkeypatch.setattr(
        service, "get_tree",
        lambda owner, repo, branch: (
            [{"path": p, "size": len(t)} for p, t in FAKE_REPO.items()], False
        ),
    )
    monkeypatch.setattr(
        service, "fetch_files",
        lambda owner, repo, branch, paths: {p: FAKE_REPO[p] for p in paths if p in FAKE_REPO},
    )

    def no_ollama(*args, **kwargs):
        raise requests.ConnectionError("Ollama is off in tests")

    monkeypatch.setattr(summarizer.requests, "post", no_ollama)
    app = FastAPI()
    app.include_router(router)
    return TestClient(app)


# ---------------- Task: directory structure ----------------
def test_ignored_paths():
    assert is_ignored("node_modules/react/index.js")
    assert is_ignored("frontend/package-lock.json")
    assert is_ignored("a/b/__pycache__/x.pyc")
    assert not is_ignored("backend/app/main.py")


def test_parse_repo_url():
    assert parse_repo_url("https://github.com/owner/repo") == ("owner", "repo")
    assert parse_repo_url("https://github.com/owner/repo.git") == ("owner", "repo")
    assert parse_repo_url("github.com/owner/repo/tree/main") == ("owner", "repo")
    with pytest.raises(GitHubError):
        parse_repo_url("not a url")


# ---------------- Task: modules and components ----------------
def test_python_parser_finds_classes_functions_imports_routes():
    info = parse_file("backend/app/services/item_service.py", FAKE_REPO["backend/app/services/item_service.py"])
    names = [c["name"] for c in info["classes"]]
    assert names == ["ItemBase", "Item"]
    assert info["classes"][1]["bases"] == ["ItemBase"]
    assert "list_items" in [f["name"] for f in info["functions"]]

    route_info = parse_file("backend/app/routes/items.py", FAKE_REPO["backend/app/routes/items.py"])
    route = [f for f in route_info["functions"] if f["route"]][0]
    assert route["route"] == {"method": "GET", "path": "/items"}


def test_broken_python_does_not_crash():
    info = parse_file("broken.py", "def oops(:\n")
    assert info["error"]
    assert info["classes"] == [] and info["functions"] == []


def test_javascript_parser():
    src = "import a from './a';\nconst b = require('lodash');\nexport class Foo extends Bar { run() {} }\nexport const go = () => 1;\n"
    info = parse_file("x.js", src)
    assert {i["module"] for i in info["imports"]} == {"./a", "lodash"}
    assert info["classes"][0]["name"] == "Foo"
    assert "go" in [f["name"] for f in info["functions"]]


# ---------------- Task: relationships and dependencies ----------------
def _parsed():
    return {p: parse_file(p, t) for p, t in FAKE_REPO.items() if p.endswith((".py", ".jsx"))}


def test_dependency_graph_edges():
    graph, _, external = build_graph(_parsed())
    assert graph.has_edge("backend/app/main.py", "backend/app/routes/items.py")
    assert graph.has_edge("backend/app/routes/items.py", "backend/app/services/item_service.py")
    assert graph.has_edge("backend/app/services/item_service.py", "backend/app/services/helpers.py")  # relative import
    assert graph.has_edge("frontend/src/App.jsx", "frontend/src/pages/Home.jsx")  # JS import
    assert external["fastapi"] >= 1 and external["axios"] == 1


def test_circular_dependency_detected():
    parsed = {
        "a.py": parse_file("a.py", "import b\n"),
        "b.py": parse_file("b.py", "import a\n"),
    }
    graph, _, _ = build_graph(parsed)
    _, metrics = compute_metrics(graph)
    assert metrics["circular_groups"] == [["a.py", "b.py"]]


# ---------------- Task: UML diagrams ----------------
def test_diagrams_have_valid_headers_and_content():
    parsed = _parsed()
    graph, bindings, _ = build_graph(parsed)
    assert dependency_diagram(graph).startswith("flowchart LR")
    cls = class_diagram(parsed)
    assert cls.startswith("classDiagram") and "ItemBase <|-- Item" in cls
    seq, source = sequence_diagram(parsed, graph, bindings)
    assert seq.startswith("sequenceDiagram") and source == "routes"
    assert "GET /items" in seq and "list_items()" in seq


# ---------------- Whole API ----------------
def test_endpoint_returns_everything(client):
    response = client.post("/github/architecture", json={"url": "https://github.com/demo/repo"})
    assert response.status_code == 200
    data = response.json()
    for key in ("repository", "stats", "structure", "technologies", "modules",
                "components", "dependencies", "diagrams", "summary"):
        assert key in data
    assert data["repository"]["name"] == "repo"
    assert data["stats"]["analyzed_files"] >= 6
    assert any("broken.py" in w for w in data["stats"]["warnings"])  # broken file reported, not fatal
    assert data["summary"]["source"] == "static"  # Ollama off -> fallback summary
    assert "React" in data["technologies"]
    assert data["diagrams"]["class"].startswith("classDiagram")


def test_endpoint_rejects_bad_url(client):
    response = client.post("/github/architecture", json={"url": "hello"})
    assert response.status_code == 400
    assert client.post("/github/architecture", json={}).status_code == 422
