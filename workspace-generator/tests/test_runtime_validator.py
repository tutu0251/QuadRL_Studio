from unittest.mock import patch

from paths import ProjectPaths
from validator.runtime_validator import validate_runtime


def test_runtime_skipped_when_stack_missing(tmp_path):
    paths = ProjectPaths("bot", tmp_path)
    paths.workspace_dir.mkdir(parents=True)
    (paths.workspace_dir / "install").mkdir()
    (paths.workspace_dir / "install" / "setup.bash").write_text("# mock")
    with patch("validator.runtime_validator.check_runtime_stack", return_value={"available": False, "missing": ["colcon"]}):
        result = validate_runtime(paths)
    assert result["status"] == "skipped"


def test_runtime_fails_without_build(tmp_path):
    paths = ProjectPaths("bot", tmp_path)
    with patch("validator.runtime_validator.check_runtime_stack", return_value={"available": True, "missing": []}):
        result = validate_runtime(paths)
    assert result["status"] == "failed"
    assert any("not built" in e for e in result["errors"])
