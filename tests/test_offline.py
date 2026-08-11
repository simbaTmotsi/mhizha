"""Rule 1 enforcement: no runtime module may reach the network.

This is a static import scan rather than a runtime check on purpose. A runtime check only
catches a network call on a path the tests happen to exercise. The scan catches the
import that would make one possible at all, which is the property we actually want.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

SRC = Path(__file__).resolve().parents[1] / "src" / "mhizha"

# Packages that reach the network. A runtime module importing any of these is a rule 1
# violation regardless of whether the call is currently made.
FORBIDDEN_ROOTS = {
    "requests", "httpx", "urllib", "urllib3", "http", "socket", "ftplib", "telnetlib",
    "smtplib", "aiohttp", "websocket", "websockets", "boto3", "botocore", "openai",
    "anthropic", "google", "huggingface_hub", "datasets", "wandb", "posthog",
    "sentry_sdk", "segment", "mixpanel", "xmlrpc", "asyncio.streams",
}

# BUILD TIME packages. Network access is permitted here and nothing on the device
# imports them.
BUILD_TIME_PACKAGES = {"corpus"}

# Dev harness only. The Android app ships neither, so they are out of scope for the
# device-side rule. They are still checked against FORBIDDEN_ROOTS below.
DEV_HARNESS_MODULES = {"cli.py", "evaluate.py"}


def _runtime_modules() -> list[Path]:
    modules = []
    for path in sorted(SRC.rglob("*.py")):
        relative = path.relative_to(SRC)
        if relative.parts[0] in BUILD_TIME_PACKAGES:
            continue
        modules.append(path)
    return modules


def _imported_roots(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    roots: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                roots.add(alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom):
            if node.level == 0 and node.module:
                roots.add(node.module.split(".")[0])
    return roots


@pytest.mark.parametrize("module", _runtime_modules(), ids=lambda p: p.name)
def test_runtime_module_imports_no_network_library(module: Path) -> None:
    offending = _imported_roots(module) & FORBIDDEN_ROOTS
    assert not offending, (
        f"{module.relative_to(SRC)} imports {sorted(offending)}, which can reach the "
        "network. Runtime code must be fully offline (CLAUDE.md rule 1). If this is "
        "build-time code, move it under mhizha/corpus/."
    )


def test_runtime_modules_are_actually_scanned() -> None:
    """Guards the guard: an empty module list would make this file pass vacuously."""
    modules = {p.name for p in _runtime_modules()}
    for expected in ("retrieve.py", "store.py", "answer.py", "safety.py", "embedder.py"):
        assert expected in modules, f"{expected} was not scanned for network imports"


def test_build_time_packages_declare_themselves() -> None:
    """A build-time module must say so on the first line of its docstring."""
    for path in sorted((SRC / "corpus").glob("*.py")):
        if path.name == "__init__.py":
            continue
        first_line = ast.get_docstring(
            ast.parse(path.read_text(encoding="utf-8"))
        ) or ""
        assert first_line.startswith("BUILD TIME"), (
            f"{path.name} must open its docstring with 'BUILD TIME' so a reader knows "
            "network access is permitted there and it never runs on the device."
        )


def test_runtime_modules_declare_themselves() -> None:
    for path in _runtime_modules():
        if path.name in {"__init__.py", "__main__.py"} or path.name in DEV_HARNESS_MODULES:
            continue
        doc = ast.get_docstring(ast.parse(path.read_text(encoding="utf-8"))) or ""
        assert doc.startswith("RUNTIME"), (
            f"{path.name} must open its docstring with 'RUNTIME (offline)'."
        )
