import re
from pathlib import Path

QUIZ_LINE_RE = re.compile(
    r"^Q(\d+): (.+?) \| (A\).+?)(?: (B\).+?))(?: (C\).+?))? \| answer: ([A-C])$"
)
REQUIRED = ("Concept", "Example", "Exercise", "Quiz")


class LessonParseError(ValueError):
    pass


def parse_lesson(text: str) -> dict:
    m = re.match(r"^---\n(.*?)\n---\n(.*)$", text, re.S)
    if not m:
        raise LessonParseError("missing front-matter")
    meta = {}
    for line in m.group(1).splitlines():
        if ":" in line:
            k, v = line.split(":", 1)
            meta[k.strip()] = v.strip()
    for key in ("id", "title"):
        if key not in meta:
            raise LessonParseError(f"front-matter missing '{key}'")
    sections, current = {}, None
    for line in m.group(2).splitlines():
        if line.startswith("## "):
            current = line[3:].strip().split(" ")[0]
            sections[current] = []
        elif current:
            sections[current].append(line)
    for name in REQUIRED:
        if name not in sections:
            raise LessonParseError(f"missing section '{name}'")
    sections = {k: "\n".join(v).strip() for k, v in sections.items()}
    if len(re.findall(r"```python\n", sections["Example"])) != 1:
        raise LessonParseError("Example must contain exactly one python code block")
    return {"meta": meta, "sections": sections}


def parse_quiz(text: str) -> list:
    quiz = parse_lesson(text)["sections"]["Quiz"]
    questions = []
    for line in quiz.splitlines():
        line = line.strip()
        if not line:
            continue
        m = QUIZ_LINE_RE.match(line)
        if not m:
            raise LessonParseError(f"bad quiz line: {line[:60]}")
        options = {o[0]: o[3:].strip() for o in m.groups()[2:5] if o}
        answer = m.group(6)
        if answer not in options:
            raise LessonParseError(f"Q{m.group(1)}: answer {answer} has no matching option")
        questions.append({"n": int(m.group(1)), "question": m.group(2), "options": options, "answer": answer})
    if len(questions) != 5:
        raise LessonParseError(f"quiz must have exactly 5 questions, found {len(questions)}")
    return questions


def load_lesson_file(path: Path) -> str:
    text = Path(path).read_text(encoding="utf-8")
    parse_lesson(text)
    return text
