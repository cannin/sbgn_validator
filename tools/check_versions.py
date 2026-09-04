"""Verify that every SBGN Validator package uses the root version."""

import json
import re
import tomllib
from pathlib import Path
from xml.etree import ElementTree

ROOT = Path(__file__).resolve().parents[1]


def description_version(path: Path) -> str:
    """Read the Version field from an R DESCRIPTION file.

    Args:
        path: DESCRIPTION file path.

    Returns:
        Declared R package version.
    """
    match = re.search(r"^Version:\s*(\S+)$", path.read_text(), re.MULTILINE)
    if match is None:
        raise ValueError(f"Version field missing from {path}")
    return match.group(1)


def source_version(path: Path, pattern: str) -> str:
    """Extract an implementation version from source code.

    Args:
        path: Source file containing backend metadata.
        pattern: Regular expression with one version capture group.

    Returns:
        Captured implementation version.
    """
    match = re.search(pattern, path.read_text())
    if match is None:
        raise ValueError(f"implementation version missing from {path}")
    return match.group(1)


def locked_package_version(path: Path, package_name: str) -> str:
    """Read one named package version from a TOML lockfile.

    Args:
        path: TOML lockfile path.
        package_name: Exact package name to locate.

    Returns:
        Version of the uniquely named package.
    """
    packages = tomllib.loads(path.read_text()).get("package", [])
    matches = [package["version"] for package in packages if package["name"] == package_name]
    if len(matches) != 1:
        raise ValueError(f"expected one {package_name} package in {path}, found {len(matches)}")
    return matches[0]


def main() -> None:
    """Fail when any project-owned package version differs."""
    expected = (ROOT / "VERSION").read_text().strip()
    pom = ElementTree.parse(ROOT / "java" / "pom.xml").getroot()
    namespace = {"m": "http://maven.apache.org/POM/4.0.0"}
    javascript_package = json.loads((ROOT / "javascript" / "package.json").read_text())
    javascript_lock = json.loads((ROOT / "javascript" / "package-lock.json").read_text())
    versions = {
        "java": pom.findtext("m:version", namespaces=namespace),
        "javascript": javascript_package["version"],
        "javascript lock": javascript_lock["version"],
        "javascript package lock": javascript_lock["packages"][""]["version"],
        "python": tomllib.loads((ROOT / "python" / "pyproject.toml").read_text())["project"][
            "version"
        ],
        "python lock": locked_package_version(
            ROOT / "python" / "uv.lock", "sbgn-validator"
        ),
        "r": description_version(ROOT / "r" / "DESCRIPTION"),
        "rust": tomllib.loads((ROOT / "rust" / "Cargo.toml").read_text())["package"][
            "version"
        ],
        "rust lock": locked_package_version(
            ROOT / "rust" / "Cargo.lock", "sbgn-validator"
        ),
        "tools": tomllib.loads((ROOT / "tools" / "pyproject.toml").read_text())["project"][
            "version"
        ],
        "tools lock": locked_package_version(
            ROOT / "tools" / "uv.lock", "sbgn-validator-tools"
        ),
        "java metadata": source_version(
            ROOT / "java/src/main/java/org/sbgn/schematron/BackendInfo.java",
            r'"sbgn-validator-java",\s*"([^"]+)"',
        ),
        "javascript metadata": source_version(
            ROOT / "javascript/src/validator.js",
            r'implementation_version:\s*"([^"]+)"',
        ),
        "python metadata": source_version(
            ROOT / "python/sbgn_validator/validator.py",
            r'"implementation_version":\s*"([^"]+)"',
        ),
        "python module": source_version(
            ROOT / "python/sbgn_validator/__init__.py",
            r'__version__\s*=\s*"([^"]+)"',
        ),
        "go metadata": source_version(
            ROOT / "go/internal/validator/validator.go",
            r'ImplementationVersion:\s*"([^"]+)"',
        ),
        "rust metadata": source_version(
            ROOT / "rust/src/lib.rs",
            r'implementation_version:\s*"([^"]+)"',
        ),
        "r metadata": source_version(
            ROOT / "r/src/schematron.cpp",
            r'implementation_version"\]\s*=\s*"([^"]+)"',
        ),
    }
    mismatches = {
        language: version for language, version in versions.items() if version != expected
    }
    if mismatches:
        raise SystemExit(f"version mismatch: expected {expected}, found {mismatches}")
    print(f"all project packages use version {expected}")


if __name__ == "__main__":
    main()
