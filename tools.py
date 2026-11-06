import logging
from smolagents import tool
import config
from lesson_parser import load_lesson_file, LessonParseError

log = logging.getLogger("tutor")
LESSONS_DIR = config.BASE_DIR / "lessons"


def list_slugs() -> list:
    return sorted(p.stem for p in LESSONS_DIR.glob("*.md"))


@tool
def read_lesson(topic: str) -> str:
    """Read one lesson file in full and return its markdown.

    Args:
        topic: Exact lesson slug without .md, for example 01_project_structure.
    """
    if not isinstance(topic, str) or not topic.strip():
        return "Error: topic must be a non-empty string."
    topic = topic.strip()
    slugs = list_slugs()
    if topic not in slugs:
        return f"No lesson found for {topic[:60]}. Available: {', '.join(slugs)}"
    try:
        return load_lesson_file(LESSONS_DIR / f"{topic}.md")
    except LessonParseError as e:
        log.warning("malformed lesson %s: %s", topic, e)
        return f"Error: lesson {topic} is malformed ({e})."


import os
import subprocess
import sys
import tempfile

MAX_OUT = 4000
MAX_LINES = 200


@tool
def run_python(code: str) -> str:
    """Run Python source code in the sandbox folder and return stdout, stderr and the exit code.

    Args:
        code: Python source to execute, at most 200 lines.
    """
    if not isinstance(code, str) or not code.strip():
        return "Error: code must be a non-empty string."
    if len(code.splitlines()) > MAX_LINES:
        return "Code too long"
    sandbox = config.SANDBOX_DIR
    sandbox.mkdir(parents=True, exist_ok=True)
    env = {k: v for k, v in os.environ.items() if not k.endswith("_API_KEY")}
    tmp = tempfile.NamedTemporaryFile(dir=sandbox, suffix=".py", delete=False, mode="w", encoding="utf-8")
    try:
        tmp.write(code)
        tmp.close()
        try:
            r = subprocess.run(
                [sys.executable, "-I", tmp.name],
                cwd=sandbox, env=env, capture_output=True, text=True,
                timeout=config.RUN_TIMEOUT,
            )
        except subprocess.TimeoutExpired:
            return f"Timed out after {config.RUN_TIMEOUT}s"
        out = f"{r.stdout}{r.stderr}\nexit code: {r.returncode}"
        return out[:MAX_OUT]
    finally:
        try:
            os.unlink(tmp.name)
        except OSError:
            pass
