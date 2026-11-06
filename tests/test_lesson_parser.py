from pathlib import Path

import pytest

import config
from lesson_parser import LessonParseError, parse_lesson, parse_quiz

LESSON_FILES = sorted((config.BASE_DIR / "lessons").glob("*.md"))

GOOD_QUIZ = "\n".join(
    [
        "Q1: first? | A) one B) two C) three | answer: A",
        "Q2: second? | A) one B) two C) three | answer: B",
        "Q3: third? | A) one B) two C) three | answer: C",
        "Q4: fourth? | A) one B) two C) three | answer: A",
        "Q5: fifth? | A) one B) two C) three | answer: B",
    ]
)


def make_lesson(example: str = "```python\nprint(1)\n```", quiz: str = GOOD_QUIZ) -> str:
    return (
        "---\n"
        "id: 99\n"
        "title: Test Lesson\n"
        "---\n"
        "## Concept\n"
        "Some concept.\n"
        "## Example (runnable)\n"
        f"{example}\n"
        "## Exercise\n"
        "Do something.\n"
        "## Quiz\n"
        f"{quiz}\n"
    )


@pytest.mark.parametrize("path", LESSON_FILES, ids=lambda p: p.stem)
def test_every_lesson_parses(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    parsed = parse_lesson(text)
    assert parsed["meta"]["id"]
    assert parsed["meta"]["title"]
    assert len(parse_quiz(text)) == 5


def test_parse_lesson_sections() -> None:
    parsed = parse_lesson(make_lesson())
    assert set(parsed["sections"]) >= {"Concept", "Example", "Exercise", "Quiz"}


def test_parse_lesson_missing_section() -> None:
    text = make_lesson().replace("## Exercise\nDo something.\n", "")
    with pytest.raises(LessonParseError, match="missing section 'Exercise'"):
        parse_lesson(text)


def test_parse_lesson_requires_front_matter() -> None:
    with pytest.raises(LessonParseError, match="front-matter"):
        parse_lesson("## Concept\nnope\n")


def test_parse_lesson_requires_one_code_block() -> None:
    two_blocks = "```python\nprint(1)\n```\n\n```python\nprint(2)\n```"
    with pytest.raises(LessonParseError, match="exactly one python code block"):
        parse_lesson(make_lesson(example=two_blocks))


def test_parse_quiz_options_and_answer() -> None:
    questions = parse_quiz(make_lesson())
    assert questions[0]["options"] == {"A": "one", "B": "two", "C": "three"}
    assert questions[0]["answer"] == "A"
    assert [q["n"] for q in questions] == [1, 2, 3, 4, 5]


def test_quiz_answer_without_matching_option() -> None:
    bad = GOOD_QUIZ.replace(
        "Q1: first? | A) one B) two C) three | answer: A",
        "Q1: first? | A) one B) two | answer: C",
    )
    with pytest.raises(LessonParseError, match="no matching option"):
        parse_quiz(make_lesson(quiz=bad))


def test_quiz_must_have_five_questions() -> None:
    four = "\n".join(GOOD_QUIZ.splitlines()[:4])
    with pytest.raises(LessonParseError, match="exactly 5"):
        parse_quiz(make_lesson(quiz=four))


def test_quiz_rejects_extra_prose() -> None:
    bad = GOOD_QUIZ + "\nThis line is not a question."
    with pytest.raises(LessonParseError, match="bad quiz line"):
        parse_quiz(make_lesson(quiz=bad))
