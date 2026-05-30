from pathlib import Path

from generator.manifest import build_manifest, exports_stale_against_workspace
from paths import ProjectPaths


def test_exports_stale_when_manifest_missing(tmp_path):
    paths = ProjectPaths("stale_robot", tmp_path)
    paths.exports_dir.mkdir(parents=True)
    paths.sens_rl_urdf().write_text("<robot/>", encoding="utf-8")
    stale, changed = exports_stale_against_workspace(paths)
    assert stale
    assert "workspace not generated" in changed


def test_exports_stale_when_hash_differs(tmp_path):
    paths = ProjectPaths("stale_robot", tmp_path)
    paths.exports_dir.mkdir(parents=True)
    urdf = paths.sens_rl_urdf()
    urdf.write_text("<robot name='v1'/>", encoding="utf-8")
    paths.workspace_dir.mkdir(parents=True)
    manifest = build_manifest(paths)
    paths.manifest_path.write_text(
        '{"manifest":{"files":[{"path":"'
        + str(urdf)
        + '","sha256":"deadbeef"}]}}',
        encoding="utf-8",
    )
    stale, changed = exports_stale_against_workspace(paths)
    assert stale
    assert urdf.name in changed


def test_exports_fresh_when_hashes_match(tmp_path):
    paths = ProjectPaths("fresh_robot", tmp_path)
    paths.exports_dir.mkdir(parents=True)
    urdf = paths.sens_rl_urdf()
    urdf.write_text("<robot name='v1'/>", encoding="utf-8")
    entry = next(e for e in build_manifest(paths).entries if e.path == urdf)
    paths.workspace_dir.mkdir(parents=True)
    paths.manifest_path.write_text(
        '{"manifest":{"files":[{"path":"'
        + str(urdf)
        + '","sha256":"'
        + entry.sha256()
        + '"}]}}',
        encoding="utf-8",
    )
    stale, changed = exports_stale_against_workspace(paths)
    assert not stale
    assert changed == []


def test_manifest_valid_for_my_robot():
    paths = ProjectPaths("my_robot")
    if not paths.sens_rl_urdf().is_file():
        return
    result = build_manifest(paths)
    assert result.valid, result.errors


def test_manifest_missing_exports(tmp_path: Path):
    paths = ProjectPaths("missing_robot", tmp_path)
    paths.exports_dir.mkdir(parents=True)
    result = build_manifest(paths)
    assert not result.valid
    assert any("Missing" in e for e in result.errors)
