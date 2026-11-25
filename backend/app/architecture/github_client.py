"""Small GitHub REST API client (public repositories, optional GITHUB_TOKEN)."""
import re
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import quote

import requests

from .config import (
    FETCH_WORKERS, GITHUB_API, GITHUB_TOKEN, MAX_FILE_BYTES, RAW_BASE,
    REQUEST_TIMEOUT,
)


class GitHubError(Exception):
    """Raised for any problem talking to GitHub. `status` is an HTTP-like code."""

    def __init__(self, message, status=502):
        super().__init__(message)
        self.message = message
        self.status = status


def _headers():
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "nexora-architecture-analyzer",
    }
    if GITHUB_TOKEN:
        headers["Authorization"] = "Bearer " + GITHUB_TOKEN
    return headers


def parse_repo_url(url):
    """Return (owner, repo) from a GitHub URL such as https://github.com/o/r."""
    match = re.match(
        r"^(?:https?://)?(?:www\.)?github\.com/([^/\s]+)/([^/\s#?]+)",
        (url or "").strip(),
    )
    if not match:
        raise GitHubError("Please provide a valid GitHub repository URL.", 400)
    owner, repo = match.group(1), match.group(2)
    if repo.endswith(".git"):
        repo = repo[:-4]
    return owner, repo


def _get_json(url, params=None):
    try:
        response = requests.get(
            url, headers=_headers(), params=params, timeout=REQUEST_TIMEOUT
        )
    except requests.RequestException as exc:
        raise GitHubError("Could not reach GitHub: %s" % exc, 502)
    if response.status_code == 404:
        raise GitHubError("Repository not found (or it is private).", 404)
    if response.status_code in (403, 429):
        raise GitHubError(
            "GitHub API rate limit reached. Set the GITHUB_TOKEN environment "
            "variable or try again later.",
            429,
        )
    if response.status_code >= 400:
        raise GitHubError("GitHub returned HTTP %s." % response.status_code, 502)
    try:
        return response.json()
    except ValueError:
        raise GitHubError("GitHub returned an invalid response.", 502)


def get_default_branch(owner, repo):
    data = _get_json("%s/repos/%s/%s" % (GITHUB_API, owner, repo))
    return data.get("default_branch") or "main"


def get_tree(owner, repo, branch):
    """Return ([{path, size}, ...], truncated) for every file in the branch."""
    data = _get_json(
        "%s/repos/%s/%s/git/trees/%s" % (GITHUB_API, owner, repo, quote(branch, safe="")),
        params={"recursive": "1"},
    )
    blobs = [
        {"path": item["path"], "size": item.get("size", 0) or 0}
        for item in data.get("tree", [])
        if item.get("type") == "blob" and "path" in item
    ]
    return blobs, bool(data.get("truncated"))


def _fetch_one(owner, repo, branch, path):
    url = "%s/%s/%s/%s/%s" % (
        RAW_BASE, owner, repo, quote(branch, safe=""), quote(path),
    )
    headers = {"User-Agent": "nexora-architecture-analyzer"}
    if GITHUB_TOKEN:
        headers["Authorization"] = "Bearer " + GITHUB_TOKEN
    try:
        response = requests.get(url, headers=headers, timeout=REQUEST_TIMEOUT)
    except requests.RequestException:
        return path, None
    if response.status_code != 200 or len(response.content) > MAX_FILE_BYTES:
        return path, None
    return path, response.content.decode("utf-8", errors="replace")


def fetch_files(owner, repo, branch, paths):
    """Download file contents concurrently. Failed files are simply omitted."""
    if not paths:
        return {}
    with ThreadPoolExecutor(max_workers=FETCH_WORKERS) as pool:
        results = pool.map(lambda p: _fetch_one(owner, repo, branch, p), paths)
        return {path: text for path, text in results if text is not None}
