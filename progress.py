import json
import os
import shutil
import sys
import tempfile
from datetime import datetime, timezone

import config


def slugs() -> list:
    return sorted(p.stem for p in (config.BASE_DIR / "lessons").glob("*.md"))


def _default() -> dict:
    return {"version": 1, "current_topic": None, "completed": [], "quizzes": []}


def load() -> dict:
    """Load progress.json, recovering from a corrupt file with a backup."""
    path = config.PROGRESS_PATH
    if not path.exists():
        return _default()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            raise ValueError("top level is not an object")
        if not isinstance(data.get("completed"), list) or not isinstance(data.get("quizzes"), list):
            raise ValueError("bad structure")
        data.setdefault("version", 1)
        data.setdefault("current_topic", None)
        return data
    except (ValueError, OSError):
        bak = path.with_name(path.name + ".bak")
        try:
            shutil.copy(path, bak)
        except OSError:
            bak = None
        print(
            f"Warning: progress file was corrupt; backed up to {bak.name if bak else 'nowhere'}, starting fresh.",
            file=sys.stderr,
        )
        return _default()


def save(data: dict) -> None:
    """Write progress.json atomically: temp file, then rename."""
    path = config.PROGRESS_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=path.parent, suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(data, handle, indent=2)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


def set_current(topic: str) -> None:
    data = load()
    data["current_topic"] = topic
    save(data)


def next_topic():
    """First lesson not completed, in filename order."""
    done = set(load()["completed"])
    for slug in slugs():
        if slug not in done:
            return slug
    return None


def _coerce_int(value):
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, str) and value.strip().lstrip("-").isdigit():
        return int(value.strip())
    return None


def record_quiz(topic: str, score: int, total: int) -> str:
    if not isinstance(topic, str) or topic not in slugs():
        return f"Error: unknown topic {str(topic)[:60]}."
    score = _coerce_int(score)
    total = _coerce_int(total)
    if score is None or total is None or total <= 0 or not (0 <= score <= total):
        return "Error: need integers with 0 <= score <= total and total > 0."

    data = load()
    data["quizzes"].append(
        {
            "topic": topic,
            "score": score,
            "total": total,
            "ts": datetime.now(timezone.utc).isoformat(),
        }
    )
    passed = score / total >= config.PASS_RATIO
    if passed and topic not in data["completed"]:
        data["completed"].append(topic)
    save(data)
    if passed:
        return f"Saved: {topic} {score}/{total} (passed)."
    return f"Saved: {topic} {score}/{total} (not passed, need {config.PASS_RATIO:.0%})."


def summary() -> str:
    data = load()
    total = len(slugs())
    line = (
        f"Completed {len(data['completed'])}/{total} lessons. "
        f"Current: {data['current_topic'] or 'none'}."
    )
    if data["quizzes"]:
        quiz = data["quizzes"][-1]
        line += f" Last quiz: {quiz['topic']} {quiz['score']}/{quiz['total']}."
    upcoming = next_topic()
    if upcoming:
        line += f" Next: {upcoming}."
    return line
