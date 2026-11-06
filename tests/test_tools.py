import logging
import os

import config
import progress
import tools
from tools import (
    get_progress,
    read_lesson,
    run_python,
    save_progress,
    scaffold_project,
    web_search,
)


def test_read_lesson_returns_full_markdown() -> None:
    text = read_lesson("01_project_structure")
    assert text.startswith("---")
    assert "## Exercise" in text
    assert "## Quiz" in text


def test_read_lesson_unknown_lists_available() -> None:
    text = read_lesson("does_not_exist")
    assert text.startswith("No lesson found for does_not_exist. Available:")
    assert "01_project_structure" in text


def test_read_lesson_malformed(monkeypatch, tmp_path, caplog) -> None:
    monkeypatch.setattr(tools, "LESSONS_DIR", tmp_path)
    (tmp_path / "bad.md").write_text("not a lesson", encoding="utf-8")
    with caplog.at_level(logging.WARNING, logger="tutor"):
        text = read_lesson("bad")
    assert text.startswith("Error: lesson bad is malformed")
    assert "malformed lesson bad" in caplog.text


def test_read_lesson_rejects_empty() -> None:
    assert read_lesson("").startswith("Error:")


def test_run_python_success() -> None:
    out = run_python("print('hello from sandbox')")
    assert "hello from sandbox" in out
    assert "exit code: 0" in out


def test_run_python_reports_stderr_and_exit() -> None:
    out = run_python("import sys\nprint('oops', file=sys.stderr)\nsys.exit(3)")
    assert "oops" in out
    assert "exit code: 3" in out


def test_run_python_timeout(monkeypatch) -> None:
    monkeypatch.setattr(config, "RUN_TIMEOUT", 1)
    assert run_python("while True:\n    pass") == "Timed out after 1s"


def test_run_python_rejects_too_much_code() -> None:
    assert run_python("\n".join(["x = 1"] * 201)) == "Code too long"


def test_run_python_rejects_empty() -> None:
    assert run_python("   ").startswith("Error:")


def test_run_python_scrubs_api_keys(monkeypatch) -> None:
    monkeypatch.setenv("NVIDIA_API_KEY", "topsecret-value")
    out = run_python("import os\nprint(os.environ.get('NVIDIA_API_KEY'))")
    assert "None" in out
    assert "topsecret-value" not in out


def test_run_python_keeps_sandbox_files() -> None:
    run_python("from pathlib import Path\nPath('persist.txt').write_text('kept')")
    out = run_python("from pathlib import Path\nprint(Path('persist.txt').read_text())")
    assert "kept" in out


def test_run_python_truncates_output() -> None:
    out = run_python("print('x' * 10000)")
    assert len(out) <= 4000


def test_run_python_removes_temp_script() -> None:
    run_python("print(1)")
    assert list(config.SANDBOX_DIR.glob("*.py")) == []


def test_scaffold_creates_fixed_tree() -> None:
    result = scaffold_project("demo_app")
    target = config.SANDBOX_DIR / "demo_app"
    assert result.startswith("Created:")
    assert (target / "src" / "demo_app" / "__init__.py").is_file()
    assert (target / "tests" / "test_smoke.py").is_file()
    assert (target / "pyproject.toml").is_file()
    assert (target / "README.md").is_file()
    assert (target / ".gitignore").is_file()
    assert 'name = "demo_app"' in (target / "pyproject.toml").read_text(encoding="utf-8")
    assert "__PACKAGE__" not in (target / "README.md").read_text(encoding="utf-8")


def test_scaffold_rejects_bad_names(tmp_path) -> None:
    for name in ("", "Demo", "bad-name", "../evil", "a" * 41):
        assert scaffold_project(name).startswith("Error:")
    assert not (tmp_path / "evil").exists()


def test_scaffold_refuses_to_overwrite() -> None:
    assert scaffold_project("demo_app").startswith("Created:")
    assert "already exists" in scaffold_project("demo_app")


def test_save_progress_and_get_progress() -> None:
    assert "passed" in save_progress("01_project_structure", 5, 5)
    assert progress.load()["completed"] == ["01_project_structure"]
    assert "Completed 1/" in get_progress()


def test_save_progress_validates() -> None:
    assert save_progress("nope", 1, 1).startswith("Error:")
    assert save_progress("01_project_structure", 9, 5).startswith("Error:")


def test_web_search_validates_query() -> None:
    assert web_search("").startswith("Error:")
