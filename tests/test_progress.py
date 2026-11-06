import json

import config
import progress


def test_load_missing_returns_default() -> None:
    data = progress.load()
    assert data == {
        "version": 1,
        "current_topic": None,
        "completed": [],
        "quizzes": [],
    }


def test_save_is_atomic() -> None:
    data = progress.load()
    data["current_topic"] = "01_project_structure"
    progress.save(data)
    assert json.loads(config.PROGRESS_PATH.read_text(encoding="utf-8"))[
        "current_topic"
    ] == "01_project_structure"
    assert list(config.PROGRESS_PATH.parent.glob("*.tmp")) == []


def test_corrupt_file_backed_up_and_reset(capsys) -> None:
    config.PROGRESS_PATH.write_text("{not valid json", encoding="utf-8")
    data = progress.load()
    assert data["completed"] == []
    backup = config.PROGRESS_PATH.with_name("progress.json.bak")
    assert backup.exists()
    assert backup.read_text(encoding="utf-8") == "{not valid json"
    assert "corrupt" in capsys.readouterr().err


def test_completion_requires_pass_ratio() -> None:
    assert "not passed" in progress.record_quiz("01_project_structure", 2, 5)
    assert progress.load()["completed"] == []
    assert "passed" in progress.record_quiz("01_project_structure", 3, 5)
    assert progress.load()["completed"] == ["01_project_structure"]


def test_current_topic_stays_after_quiz() -> None:
    progress.set_current("02_env_and_config")
    progress.record_quiz("02_env_and_config", 5, 5)
    assert progress.load()["current_topic"] == "02_env_and_config"


def test_record_quiz_coerces_numeric_strings() -> None:
    assert "passed" in progress.record_quiz("01_project_structure", "4", "5")
    assert progress.load()["quizzes"][-1]["score"] == 4


def test_record_quiz_rejects_bad_values() -> None:
    assert progress.record_quiz("nope", 1, 1).startswith("Error:")
    assert progress.record_quiz("01_project_structure", 6, 5).startswith("Error:")
    assert progress.record_quiz("01_project_structure", 1, 0).startswith("Error:")
    assert progress.record_quiz("01_project_structure", "x", 5).startswith("Error:")


def test_next_topic_skips_completed() -> None:
    assert progress.next_topic() == progress.slugs()[0]
    progress.record_quiz(progress.slugs()[0], 5, 5)
    assert progress.next_topic() == progress.slugs()[1]


def test_summary_is_human_readable() -> None:
    progress.set_current("01_project_structure")
    text = progress.summary()
    assert "Completed" in text
    assert "Current: 01_project_structure" in text
    assert "Next:" in text
