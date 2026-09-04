"""Regression tests for rule synchronization drift detection."""

import shutil
import zipfile
from pathlib import Path

from sync_rules import synchronize
from verify_rule_archive import verify_archive
from verify_rules import verify

ROOT = Path(__file__).resolve().parents[1]


def _workspace(tmp_path: Path) -> Path:
    for relative in (Path("validation/rules"),):
        shutil.copytree(ROOT / relative, tmp_path / relative)
    return tmp_path


def test_modified_generated_copy_fails(tmp_path: Path) -> None:
    workspace = _workspace(tmp_path)
    synchronize(workspace)
    target = workspace / "go/internal/rules/data/sbgn_pd.sch"
    target.write_bytes(target.read_bytes() + b"\n")
    assert verify(workspace)
    synchronize(workspace)
    assert verify(workspace) == []


def test_unsynchronized_canonical_change_fails(tmp_path: Path) -> None:
    workspace = _workspace(tmp_path)
    synchronize(workspace)
    target = workspace / "validation/rules/sbgn_pd.sch"
    target.write_bytes(target.read_bytes() + b"\n")
    assert verify(workspace)


def test_unexpected_canonical_file_is_rejected(tmp_path: Path) -> None:
    workspace = _workspace(tmp_path)
    (workspace / "validation/rules/extra.xml").write_text("<unexpected/>\n")
    try:
        synchronize(workspace)
    except ValueError as exception:
        assert "extra.xml" in str(exception)
    else:
        raise AssertionError("unexpected canonical file was accepted")


def test_modified_generated_metadata_fails(tmp_path: Path) -> None:
    workspace = _workspace(tmp_path)
    synchronize(workspace)
    target = workspace / "python/sbgn_validator/_resources/schematron/README.generated.md"
    target.write_text("stale\n")
    assert verify(workspace)


def test_release_archive_bytes_are_verified(tmp_path: Path) -> None:
    workspace = _workspace(tmp_path)
    synchronize(workspace)
    archive = tmp_path / "package.whl"
    snapshot = workspace / "python/sbgn_validator/_resources/schematron"
    with zipfile.ZipFile(archive, "w") as package:
        for path in snapshot.iterdir():
            package.write(path, f"package/schematron/{path.name}")
    assert verify_archive(archive, "package/schematron", workspace / "validation/rules") == []

    with zipfile.ZipFile(archive, "a") as package:
        package.writestr("package/schematron/unexpected.sch", "<schema/>\n")
    assert verify_archive(archive, "package/schematron", workspace / "validation/rules")
