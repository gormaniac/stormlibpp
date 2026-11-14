"""Checks every Storm service's tests should run.

These don't need the pytest plugin, so a repo-level script can use them too::

    from stormlibpp.testing.checks import assertVersionsMatch

    def test_versions_match():
        assertVersionsMatch(pathlib.Path(__file__).parents[1])
"""

import json
import pathlib
import re
import subprocess
import sys
import tomllib

import yaml

_VERSION_RE = re.compile(r"""^__version__\s*=\s*["']([^"']+)["']""", re.MULTILINE)


def _norm(name: str) -> str:
    """A Python package name, normalized as in PEP 503."""
    return re.sub(r"[-_.]+", "-", name).lower()


def findVersions(root: str | pathlib.Path) -> dict[str, str | None]:
    """Find a Storm service's version everywhere it's written down.

    ``root`` is the service's project directory (the one with ``pyproject.toml``). Returns a
    dict of location to version, ``None`` when a location has no version:

    - ``pyproject.toml``: ``project.version``.
    - ``src/<pkg>/__init__.py``: ``__version__``, for each package under ``src/`` that sets it.
    - ``src/<pkg>/pkgproto/<name>.yaml``: ``version``, for each Storm package prototype.
    - ``uv.lock``: the project's own ``[[package]]`` entry, when the project has a lock.
    """

    root = pathlib.Path(root)
    found: dict[str, str | None] = {}

    pyproj = tomllib.loads((root / "pyproject.toml").read_text())
    project = pyproj.get("project", {})
    found["pyproject.toml"] = project.get("version")

    for init in sorted(root.glob("src/*/__init__.py")):
        if match := _VERSION_RE.search(init.read_text()):
            found[init.relative_to(root).as_posix()] = match.group(1)

    for proto in sorted(root.glob("src/*/pkgproto/*.yaml")):
        data = yaml.safe_load(proto.read_text()) or {}
        if isinstance(data, dict) and "name" in data:
            valu = data.get("version")
            found[proto.relative_to(root).as_posix()] = (
                None if valu is None else str(valu)
            )

    lock = root / "uv.lock"
    if lock.exists() and project.get("name"):
        name = _norm(project["name"])
        pkgs = tomllib.loads(lock.read_text()).get("package", [])
        found["uv.lock"] = next(
            (p.get("version") for p in pkgs if _norm(p.get("name", "")) == name), None
        )

    return found


def assertVersionsMatch(root: str | pathlib.Path) -> str:
    """Assert a Storm service's version is the same everywhere ``findVersions()`` looks.

    Also asserts there's at least a ``pyproject.toml`` version, an ``__init__.py`` version,
    and a Storm package prototype version. Returns the version.
    """

    found = findVersions(root)
    shown = "\n".join(f"  {loc}: {ver}" for loc, ver in found.items())

    assert found.get(
        "pyproject.toml"
    ), f"No project.version in pyproject.toml:\n{shown}"
    assert any(
        loc.endswith("__init__.py") for loc in found
    ), f"No __version__ in any src/<pkg>/__init__.py:\n{shown}"
    assert any(
        loc.endswith(".yaml") for loc in found
    ), f"No Storm package prototype in src/<pkg>/pkgproto/:\n{shown}"
    assert len(set(found.values())) == 1, f"The versions don't match:\n{shown}"
    return found["pyproject.toml"]


def stormLint(
    *paths: str | pathlib.Path,
    select: str | None = None,
    ignore: str | None = None,
    v3: bool = False,
    cwd: str | pathlib.Path | None = None,
) -> list[dict]:
    """Run Synapse's Storm linter and return its findings (empty when clean).

    Runs ``python -m synapse.tools.storm.lint --format json`` in a subprocess, so the
    linter's settings are read from the nearest ``[tool.stormlint]`` table as usual,
    searching up from ``cwd``. ``select``, ``ignore`` and ``v3`` map to its
    ``--select``, ``--ignore`` and ``--v3-ready`` options. Needs Synapse 2.256.0 or later.

    Raises ``RuntimeError`` on a usage, config or file error (exit code 2).
    """

    cmd = [sys.executable, "-m", "synapse.tools.storm.lint", "--format", "json"]
    if select:
        cmd += ["--select", select]
    if ignore:
        cmd += ["--ignore", ignore]
    if v3:
        cmd.append("--v3-ready")
    cmd += [str(p) for p in paths]

    proc = subprocess.run(cmd, capture_output=True, text=True, cwd=cwd, check=False)
    if proc.returncode not in (0, 1):
        raise RuntimeError(
            f"The Storm linter failed ({proc.returncode}):\n{proc.stderr}"
        )
    return [json.loads(line) for line in proc.stdout.splitlines() if line.strip()]


def assertMainHelp(module: str, *, timeout: float = 120) -> str:
    """Assert ``python -m <module> --help`` exits 0, and return what it printed.

    A cheap check that a service's entry point imports and builds its argument parser.
    """

    proc = subprocess.run(
        [sys.executable, "-m", module, "--help"],
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
    )
    assert (
        proc.returncode == 0
    ), f"python -m {module} --help exited {proc.returncode}:\n{proc.stdout}\n{proc.stderr}"
    return proc.stdout + proc.stderr
