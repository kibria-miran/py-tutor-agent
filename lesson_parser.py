import re
from pathlib import Path

QUIZ_LINE_RE = re.compile(
    r"^Q(\d+): (.+?) \| (A\).+?)(?: (B\).+?))(?: (C\).+?))? \| answer: ([A-C])$"
)
REQUIRED = ("Concept", "Example", "Exercise", "Quiz")
FRONT_MATTER_RE = re.compile(r"^---\n(.*?)\n---\n(.*)$", re.S)
PYTHON_FENCE_RE = re.compile(r"^```python\s*$", re.M)


class LessonParseError(ValueError):
    pass


def parse_lesson(text: str) -> dict:
    """Parse a lesson's front-matter and required sections.

    Raises:
        LessonParseError: if the lesson does not follow the contract.
    """
    if not isinstance(text, str):
        raise LessonParseError("lesson must be text")
    text = text.replace("\r\n", "\n")
    match = FRONT_MATTER_RE.match(text)
    if not match:
        raise LessonParseError("missing front-matter")

    meta = {}
    for line in match.group(1).splitlines():
        if ":" in line:
            key, value = line.split(":", 1)
            meta[key.strip()] = value.strip()
    for key in ("id", "title"):
        if not meta.get(key):
            raise LessonParseError(f"front-matter missing '{key}'")

    sections = {}
    current = None
    for line in match.group(2).splitlines():
        if line.startswith("## "):
            current = line[3:].strip().split(" ")[0]
            sections[current] = []
        elif current:
            sections[current].append(line)
    for name in REQUIRED:
        if name not in sections:
            raise LessonParseError(f"missing section '{name}'")
    sections = {key: "\n".join(value).strip() for key, value in sections.items()}

    if len(PYTHON_FENCE_RE.findall(sections["Example"])) != 1:
        raise LessonParseError("Example must contain exactly one python code block")
    return {"meta": meta, "sections": sections}


def parse_quiz(text: str) -> list:
    """Parse the Quiz block into five question dictionaries."""
    quiz = parse_lesson(text)["sections"]["Quiz"]
    questions = []
    for line in quiz.splitlines():
        line = line.strip()
        if not line:
            continue
        match = QUIZ_LINE_RE.match(line)
        if not match:
            raise LessonParseError(f"bad quiz line: {line[:60]}")
        options = {option[0]: option[3:].strip() for option in match.groups()[2:5] if option}
        answer = match.group(6)
        if answer not in options:
            raise LessonParseError(f"Q{match.group(1)}: answer {answer} has no matching option")
        questions.append(
            {
                "n": int(match.group(1)),
                "question": match.group(2),
                "options": options,
                "answer": answer,
            }
        )
    if len(questions) != 5:
        raise LessonParseError(f"quiz must have exactly 5 questions, found {len(questions)}")
    return questions


def load_lesson_file(path: Path) -> str:
    """Read and validate a lesson file, returning its full markdown."""
    text = Path(path).read_text(encoding="utf-8")
    parse_lesson(text)
    return text
