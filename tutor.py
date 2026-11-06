import logging
import sys
import time
from logging.handlers import RotatingFileHandler

import agent_setup
import config
import progress
from lesson_parser import LessonParseError, parse_quiz
from tools import run_python, save_progress, scaffold_project

try:
    from smolagents import AgentMaxStepsError
except ImportError:  # pragma: no cover - depends on smolagents version
    class AgentMaxStepsError(Exception):
        pass

try:
    import openai
except ImportError:  # pragma: no cover
    openai = None

log = logging.getLogger("tutor")

SESSION_STEP_BUDGET = max(config.MAX_STEPS * 10, 30)
COMMANDS = "/lesson [slug], /progress, /scaffold <name>, /run, /quiz, /quit"


def setup_logging() -> None:
    """Configure the file log plus warning-only stderr output."""
    if log.handlers:
        return
    log.setLevel(getattr(logging, str(config.LOG_LEVEL).upper(), logging.INFO))
    log.propagate = False
    config.LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    file_handler = RotatingFileHandler(
        config.LOG_PATH, maxBytes=1_000_000, backupCount=3, encoding="utf-8"
    )
    file_handler.setFormatter(
        logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s")
    )
    stderr_handler = logging.StreamHandler(sys.stderr)
    stderr_handler.setLevel(logging.WARNING)
    stderr_handler.setFormatter(logging.Formatter("%(levelname)s: %(message)s"))
    log.addHandler(file_handler)
    log.addHandler(stderr_handler)
    # smolagents logs each step to the console at INFO; our own log covers it.
    logging.getLogger("smolagents").setLevel(logging.WARNING)


def print_banner() -> None:
    print("=" * 62)
    print("Python Tutor Agent - Python codebases for LLM/AI")
    print(f"Model: {config.MODEL_ID or '(not set)'}")
    print(f"Lessons found: {len(progress.slugs())}")
    print(progress.summary())
    print("Type /lesson to begin, or ask a question.")
    print("=" * 62)


class TutorApp:
    """Deterministic command dispatcher plus a chat agent."""

    def __init__(self, input_fn=input, output_fn=print):
        self._input = input_fn
        self._print = output_fn
        self.agent = None
        self.session_steps = 0
        self._warned_budget = False

    def run(self) -> None:
        while True:
            try:
                line = self._input("\nyou> ")
            except (EOFError, KeyboardInterrupt):
                self._print("")
                return
            if not self.handle(line):
                return

    def handle(self, line: str) -> bool:
        line = (line or "").strip()
        if not line:
            return True
        if not line.startswith("/"):
            self.chat(line)
            return True

        command, _, arg = line.partition(" ")
        command = command.lower()
        arg = arg.strip()

        if command == "/quit":
            self._save_and_exit()
            return False
        if command == "/lesson":
            self.cmd_lesson(arg)
        elif command == "/progress":
            self._print(progress.summary())
        elif command == "/scaffold":
            self.cmd_scaffold(arg)
        elif command == "/run":
            self.cmd_run()
        elif command == "/quiz":
            self.cmd_quiz()
        else:
            self._print(f"Unknown command. Available: {COMMANDS}")
        return True

    # ---------------------------------------------------------------- lesson
    def cmd_lesson(self, slug: str) -> None:
        if slug:
            if slug not in progress.slugs():
                self._print(
                    f"No lesson found for {slug}. Available: {', '.join(progress.slugs())}"
                )
                return
            topic = slug
        else:
            topic = progress.next_topic()
            if topic is None:
                self._print("All lessons complete")
                return

        progress.set_current(topic)
        self.agent = None
        self.agent = self._build_agent()
        if self.agent is None:
            return
        log.info("serving lesson %s", topic)
        task = (
            f"Teach lesson {topic}. Call read_lesson for that exact slug first, "
            "then explain the concept, run the example with run_python if useful, "
            "and finish with the exercise. Do not change the lesson file."
        )
        answer = self._run_agent(task, self.agent)
        if answer is None:
            return
        if self._count_tool_calls(self.agent) == 0:
            log.warning("lesson %s finished without a tool call (prose only)", topic)
        self._print("Run /quiz to complete this lesson.")

    # --------------------------------------------------------------- scaffold
    def cmd_scaffold(self, name: str) -> None:
        if not name:
            self._print("Usage: /scaffold <name>")
            return
        self._print(scaffold_project(name))

    # -------------------------------------------------------------------- run
    def cmd_run(self) -> None:
        self._print("Paste Python code. Finish with a line containing END.")
        lines = []
        while True:
            try:
                line = self._input("... ")
            except EOFError:
                break
            if line.strip() == "END":
                break
            lines.append(line)
        self._print(run_python("\n".join(lines)))

    # ------------------------------------------------------------------- quiz
    def cmd_quiz(self) -> None:
        topic = progress.load().get("current_topic")
        if not topic:
            self._print("No current lesson. Use /lesson first.")
            return
        path = config.BASE_DIR / "lessons" / f"{topic}.md"
        try:
            questions = parse_quiz(path.read_text(encoding="utf-8"))
        except (OSError, LessonParseError) as exc:
            log.warning("cannot run quiz for %s: %s", topic, exc)
            self._print(f"Could not load the quiz for {topic}.")
            return

        wrong = []
        score = 0
        for question in questions:
            self._print(f"\nQ{question['n']}: {question['question']}")
            for letter in sorted(question["options"]):
                self._print(f"  {letter}) {question['options'][letter]}")
            answer = self._read_answer(question)
            if answer == question["answer"]:
                score += 1
            else:
                wrong.append((question, answer))

        total = len(questions)
        self._print(save_progress(topic, score, total))

        if not wrong:
            return
        parts = [f"Lesson {topic}."]
        for question, answer in wrong:
            said = answer or "invalid"
            parts.append(
                f"Q{question['n']}: {question['question']} "
                f"(you said {said}; correct {question['answer']})."
            )
        parts.append(
            "Explain each wrong answer in at most two sentences. "
            "If you need context, call read_lesson for the slug at most once. "
            "Do not change any files."
        )
        explain_agent = self._build_agent()
        if explain_agent is not None:
            log.info("explaining %d wrong answer(s) for %s", len(wrong), topic)
            self._run_agent("\n".join(parts), explain_agent)

    def _read_answer(self, question: dict) -> str:
        valid = ", ".join(sorted(question["options"]))
        for attempt in range(2):
            try:
                raw = self._input(f"Your answer ({valid}): ")
            except EOFError:
                return ""
            raw = raw.strip().upper()
            if raw in question["options"]:
                return raw
            if attempt == 0:
                self._print(f"Please enter one of {valid}.")
        return ""

    # ------------------------------------------------------------------- chat
    def chat(self, text: str) -> None:
        agent = self._ensure_agent()
        if agent is None:
            return
        if self._run_agent(text, agent, reset=False) is not None:
            self._trim_memory(agent)

    # --------------------------------------------------------------- internals
    def _build_agent(self):
        try:
            return agent_setup.build_agent()
        except Exception as exc:  # setup errors are user-facing
            log.exception("could not build agent")
            self._print(self._friendly_error(exc))
            return None

    def _ensure_agent(self):
        if self.agent is None:
            self.agent = self._build_agent()
        return self.agent

    def _run_agent(self, task: str, agent, reset: bool = True):
        started = time.perf_counter()
        steps_before = len(getattr(getattr(agent, "memory", None), "steps", []) or [])
        try:
            answer = agent.run(task, reset=reset)
        except AgentMaxStepsError:
            log.warning("agent hit max_steps=%s", config.MAX_STEPS)
            self._print(
                f"Stopped after {config.MAX_STEPS} steps. "
                "Try a narrower request, for example one lesson or one question."
            )
            return None
        except Exception as exc:
            log.exception("agent run failed")
            self._print(self._friendly_error(exc))
            return None

        elapsed = time.perf_counter() - started
        steps = list(getattr(getattr(agent, "memory", None), "steps", []) or [])
        new_steps = max(0, len(steps) - steps_before)
        self.session_steps += new_steps
        self._log_usage(steps[steps_before:] if steps_before <= len(steps) else steps)
        log.info(
            "agent run: %d steps, %d tool call(s), %.2fs",
            new_steps,
            self._count_tool_calls(agent),
            elapsed,
        )
        if (
            not self._warned_budget
            and self.session_steps >= 0.8 * SESSION_STEP_BUDGET
        ):
            self._warned_budget = True
            self._print(
                "Heads-up: this session is getting long. "
                "Use /progress and start a fresh session when convenient."
            )

        text = str(answer).strip() if answer is not None else ""
        self._print(text if text else "(agent returned no answer)")
        return answer

    def _log_usage(self, steps) -> None:
        input_tokens = 0
        output_tokens = 0
        found = False
        for step in steps:
            usage = getattr(step, "token_usage", None)
            if usage is None:
                continue
            found = True
            input_tokens += getattr(usage, "input_tokens", 0) or 0
            output_tokens += getattr(usage, "output_tokens", 0) or 0
        if found:
            log.info("tokens: input=%d output=%d", input_tokens, output_tokens)

    @staticmethod
    def _count_tool_calls(agent) -> int:
        count = 0
        steps = getattr(getattr(agent, "memory", None), "steps", []) or []
        for step in steps:
            calls = getattr(step, "tool_calls", None)
            if calls:
                count += len(calls)
        return count

    @staticmethod
    def _trim_memory(agent) -> None:
        memory = getattr(agent, "memory", None)
        steps = getattr(memory, "steps", None)
        if not steps:
            return
        keep = max(2, config.HISTORY_MESSAGES)
        if len(steps) > keep:
            del steps[:-keep]

    def _friendly_error(self, exc: Exception) -> str:
        seen = set()
        current = exc
        while current is not None and id(current) not in seen:
            seen.add(id(current))
            if openai is not None:
                if isinstance(current, openai.AuthenticationError):
                    return "Authentication failed: check NVIDIA_API_KEY in .env."
                if isinstance(current, openai.APITimeoutError):
                    return "The NVIDIA API timed out. Check the network and try again."
                if isinstance(current, openai.RateLimitError):
                    return "NVIDIA API rate limit reached. Wait a moment and try again."
                if isinstance(current, openai.APIStatusError):
                    return f"NVIDIA API returned HTTP {current.status_code}. See logs/tutor.log."
            current = getattr(current, "__cause__", None) or getattr(
                current, "__context__", None
            )
        return "The tutor hit an unexpected error. See logs/tutor.log."

    def _save_and_exit(self) -> None:
        try:
            progress.save(progress.load())
        except OSError as exc:
            log.warning("could not save progress on exit: %s", exc)
        self._print("Progress saved. Bye.")


def main() -> int:
    setup_logging()
    if not config.NVIDIA_API_KEY or not config.MODEL_ID:
        print(
            "Configuration error: set NVIDIA_API_KEY and MODEL_ID in .env "
            "(see README.md)."
        )
        return 1
    print_banner()
    TutorApp().run()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
