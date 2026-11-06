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
