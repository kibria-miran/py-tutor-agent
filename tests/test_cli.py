import logging
from types import SimpleNamespace

import config
import progress
import tutor


class Inputs:
    def __init__(self, items):
        self.items = list(items)

    def __call__(self, prompt=""):
        if not self.items:
            raise EOFError
        return self.items.pop(0)


class FakeAgent:
    def __init__(self, answer="lesson answer", tool_calls=1):
        self.answer = answer
        self.tasks = []
        self.reset_values = []
        self.memory = SimpleNamespace(
            steps=[SimpleNamespace(tool_calls=[object()] * tool_calls)]
        )

    def run(self, task, reset=True):
        self.tasks.append(task)
        self.reset_values.append(reset)
        return self.answer


def make_app(inputs=()):
    output = []
    app = tutor.TutorApp(input_fn=Inputs(inputs), output_fn=output.append)
    return app, output


def patch_agent(monkeypatch, agent):
    monkeypatch.setattr(tutor.agent_setup, "build_agent", lambda: agent)


def test_lesson_by_slug_builds_new_agent(monkeypatch) -> None:
    fake = FakeAgent()
    patch_agent(monkeypatch, fake)
    app, output = make_app()
    app.handle("/lesson 01_project_structure")
    assert fake.tasks and "01_project_structure" in fake.tasks[0]
    assert fake.reset_values == [True]
    assert progress.load()["current_topic"] == "01_project_structure"
    assert any("Run /quiz" in line for line in output)


def test_lesson_without_arg_uses_completion_order(monkeypatch) -> None:
    fake = FakeAgent()
    patch_agent(monkeypatch, fake)
    app, _ = make_app()
    slugs = progress.slugs()
    app.handle("/lesson")
    assert progress.load()["current_topic"] == slugs[0]
    progress.record_quiz(slugs[0], 5, 5)
    app.handle("/lesson")
    assert progress.load()["current_topic"] == slugs[1]


def test_lesson_when_all_complete(monkeypatch) -> None:
    for slug in progress.slugs():
        progress.record_quiz(slug, 5, 5)
    app, output = make_app()
    app.handle("/lesson")
    assert "All lessons complete" in output


def test_lesson_unknown_slug(monkeypatch) -> None:
    app, output = make_app()
    app.handle("/lesson nope")
    assert any("No lesson found for nope" in line for line in output)


def test_no_tool_call_does_not_loop(monkeypatch, caplog) -> None:
    fake = FakeAgent(answer="prose only", tool_calls=0)
    patch_agent(monkeypatch, fake)
    app, output = make_app()
    with caplog.at_level(logging.WARNING, logger="tutor"):
        app.handle("/lesson 01_project_structure")
    assert "prose only" in output
    assert len(fake.tasks) == 1
    assert "without a tool call" in caplog.text


def test_progress_command() -> None:
    progress.set_current("01_project_structure")
    app, output = make_app()
    app.handle("/progress")
    assert any("Completed" in line for line in output)


def test_scaffold_command() -> None:
    app, output = make_app()
    app.handle("/scaffold demo_app")
    assert (config.SANDBOX_DIR / "demo_app" / "src" / "demo_app" / "__init__.py").is_file()
    assert any("Created:" in line for line in output)


def test_scaffold_usage() -> None:
    app, output = make_app()
    app.handle("/scaffold")
    assert any("Usage: /scaffold" in line for line in output)


def test_run_command_reads_until_end(monkeypatch) -> None:
    seen = {}

    def fake_run(code):
        seen["code"] = code
        return "ran it"

    monkeypatch.setattr(tutor, "run_python", fake_run)
    app, output = make_app(["print(1)", "print(2)", "END"])
    app.handle("/run")
    assert seen["code"] == "print(1)\nprint(2)"
    assert "ran it" in output


def test_quiz_all_correct_skips_agent(monkeypatch) -> None:
    progress.set_current("01_project_structure")
    fake = FakeAgent()
    patch_agent(monkeypatch, fake)
    app, _ = make_app(["A", "B", "C", "B", "A"])
    app.handle("/quiz")
    data = progress.load()
    assert data["quizzes"][-1]["score"] == 5
    assert "01_project_structure" in data["completed"]
    assert fake.tasks == []


def test_quiz_wrong_answer_gets_explanation(monkeypatch) -> None:
    progress.set_current("01_project_structure")
    fake = FakeAgent()
    patch_agent(monkeypatch, fake)
    app, _ = make_app(["A", "A", "C", "B", "A"])
    app.handle("/quiz")
    data = progress.load()
    assert data["quizzes"][-1]["score"] == 4
    assert len(fake.tasks) == 1
    task = fake.tasks[0]
    assert "Lesson 01_project_structure" in task
    assert "Q2:" in task
    assert "you said A; correct B" in task


def test_quiz_invalid_input_reprompts_once_then_counts_wrong(monkeypatch) -> None:
    progress.set_current("01_project_structure")
    fake = FakeAgent()
    patch_agent(monkeypatch, fake)
    app, output = make_app(["Z", "Y", "B", "C", "B", "A"])
    app.handle("/quiz")
    data = progress.load()
    assert data["quizzes"][-1]["score"] == 4
    assert any("Please enter one of" in line for line in output)
    assert "you said invalid" in fake.tasks[0]


def test_quiz_without_current_topic() -> None:
    app, output = make_app()
    app.handle("/quiz")
    assert any("No current lesson" in line for line in output)


def test_quit_returns_false() -> None:
    app, output = make_app()
    assert app.handle("/quit") is False
    assert any("Bye" in line for line in output)


def test_free_text_goes_to_agent(monkeypatch) -> None:
    fake = FakeAgent(answer="hello there")
    patch_agent(monkeypatch, fake)
    app, output = make_app()
    app.handle("what is a tool?")
    assert fake.tasks == ["what is a tool?"]
    assert fake.reset_values == [False]
    assert "hello there" in output


def test_unknown_command_does_not_call_agent(monkeypatch) -> None:
    fake = FakeAgent()
    patch_agent(monkeypatch, fake)
    app, output = make_app()
    app.handle("/nope")
    assert fake.tasks == []
    assert any("Unknown command" in line for line in output)


def test_banner_hides_api_key(monkeypatch, capsys) -> None:
    monkeypatch.setattr(config, "NVIDIA_API_KEY", "super-secret-key")
    monkeypatch.setattr(config, "MODEL_ID", "test/model")
    tutor.print_banner()
    out = capsys.readouterr().out
    assert "test/model" in out
    assert "super-secret-key" not in out
