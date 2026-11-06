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
    path = config.PROGRESS_PATH
    if not path.exists():
        return _default()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(data, dict) or "completed" not in data or "quizzes" not in data:
            raise ValueError("bad structure")
        return data
    except (ValueError, OSError):
        bak = path.with_name(path.name + ".bak")
        shutil.copy(path, bak)
        print(f"Warning: progress file was corrupt; backed up to {bak.name}, starting fresh.", file=sys.stderr)
        return _default()


def save(data: dict) -> None:
    path = config.PROGRESS_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=path.parent, suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


def set_current(topic: str) -> None:
    data = load()
    data["current_topic"] = topic
    save(data)


def next_topic():
    done = set(load()["completed"])
    for s in slugs():
        if s not in done:
            return s
    return None


def record_quiz(topic: str, score: int, total: int) -> str:
    if topic not in slugs():
        return f"Error: unknown topic {str(topic)[:60]}."
    if not (isinstance(score, int) and isinstance(total, int)) or total <= 0 or not (0 <= score <= total):
        return "Error: need integers with 0 <= score <= total and total > 0."
    data = load()
    data["quizzes"].append({"topic": topic, "score": score, "total": total,
                            "ts": datetime.now(timezone.utc).isoformat()})
    passed = score / total >= config.PASS_RATIO
    if passed and topic not in data["completed"]:
        data["completed"].append(topic)
    save(data)
    return f"Saved: {topic} {score}/{total} ({'passed' if passed else 'not passed'})."


def summary() -> str:
    data = load()
    total = len(slugs())
    line = f"Completed {len(data['completed'])}/{total} lessons. Current: {data['current_topic'] or 'none'}."
    if data["quizzes"]:
        q = data["quizzes"][-1]
        line += f" Last quiz: {q['topic']} {q['score']}/{q['total']}."
    return line
