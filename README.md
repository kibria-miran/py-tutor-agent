# Python Tutor Agent

A terminal AI tutor that teaches how to structure real Python codebases for
LLM/AI projects: project layout, config, API clients, retries, dataclasses,
logging, testing, prompts, agent loops, RAG layouts, evals, and packaging.

It is built with [smolagents](https://huggingface.co/docs/smolagents) and a
hosted NVIDIA NIM model, so it runs on a small Linux machine with no GPU.

## Requirements

- Linux or macOS (Windows is not supported)
- Python 3.10+
- An NVIDIA NIM API key from <https://build.nvidia.com>
- About 4 GB RAM; all heavy inference happens on the hosted API

## Setup

```bash
cd ~/py-tutor-agent
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env
# edit .env: set NVIDIA_API_KEY and MODEL_ID
python tutor.py
```

`MODEL_ID` must be a model that supports tool calling on NVIDIA NIM. Verify it
on <https://build.nvidia.com>, then put that exact ID in `.env`. Never commit
`.env`.

The first screen prints the model ID (never the key), the number of lessons
found, and your progress summary.

## Commands

| Command | What it does |
| --- | --- |
| `/lesson` | Serve the first lesson you have not completed |
| `/lesson <slug>` | Jump to a specific lesson, for example `/lesson 03_api_clients_and_retries` |
| `/progress` | Show completed lessons, current lesson, and the last quiz |
| `/scaffold <name>` | Create a fixed starter project at `sandbox/<name>/` |
| `/run` | Paste Python code, finish with a line containing `END` |
| `/quiz` | Five static questions on the current lesson; scored in Python |
| `/quit` | Save progress and exit |

Anything that is not a `/command` goes to the tutor agent as free text.

A lesson is marked complete only when its quiz score is at least
`PASS_RATIO` (default 0.6). Reading a lesson alone does not complete it.
`/lesson` without an argument enforces completion order; `/lesson <slug>`
lets you skip ahead. After a quiz, the current lesson stays selected until
you serve another lesson.

## How a lesson turn works

1. `tutor.py` picks the lesson slug (the CLI owns ordering).
2. It creates a new agent and asks it to teach that exact slug.
3. The agent calls `read_lesson`, explains the material, and may call
   `run_python` on the example.
4. The agent ends with the exercise.
5. The CLI prints the answer and suggests `/quiz`.

`/quiz` is deterministic: the CLI parses the lesson's Quiz block, compares
answers in Python, and calls `save_progress` directly. A fresh agent explains
only the wrong answers afterwards.

## Project layout

```text
py-tutor-agent/
  tutor.py             CLI dispatcher, /quiz flow, logging setup
  config.py            settings from .env with defaults
  agent_setup.py       model + agent construction
  tools.py             read_lesson, run_python, scaffold_project,
                       save_progress, get_progress, web_search
  progress.py          atomic progress.json + summary()
  lesson_parser.py     the only lesson/quiz parser
  lessons/             01_...md to 11_...md
  templates/scaffold/  fixed starter tree used by scaffold_project
  prompts/system.md    tutor rules, read at startup
  sandbox/             generated code and scaffolded projects
  logs/tutor.log       rotating log
  tests/               offline tests + one opt-in integration test
```

## Lesson format

A lesson is markdown with front-matter and four required sections:

```markdown
---
id: 03
title: API Clients, Timeouts, and Retries
objectives: [add timeouts, retry transient failures]
estimated_min: 20
---
## Concept
...
## Example (runnable)
```python
print("exactly one python block")
```
## Exercise
...
## Quiz
Q1: question | A) ... B) ... C) ... | answer: B
...(exactly five)
```

`lesson_parser.py` validates all of this. A malformed lesson makes
`read_lesson` return an error string and writes a warning to the log.

## Tutor tools and safety

The agent can only call the registered tools:

- `read_lesson(topic)` returns one lesson's full markdown.
- `run_python(code)` writes a temp file in `sandbox/`, runs it with
  `python -I`, enforces a timeout, and truncates output to 4000 characters.
  The child process receives a copy of the environment with `*_API_KEY`
  variables removed.
- `scaffold_project(name)` copies the fixed template to `sandbox/<name>/`.
  Names must match `^[a-z0-9_]{1,40}$`.
- `get_progress()` returns a human-readable summary.
- `web_search(query)` is registered only when `WEB_SEARCH_ENABLED=true`
  (and requires the optional `ddgs` package). Results are untrusted text.

`save_progress` exists as a tool, but the CLI calls it directly after `/quiz`
so the model does not decide scores.

Important limits:

- `run_python` is a subprocess with a timeout, not a real security sandbox.
  Network access is not blocked in this MVP. Never run the tutor as root.
- Never put API keys in prompts, lessons, or `sandbox/`.
- The log never records the key or the full prompt.

## Tests

Offline suite (no API credits):

```bash
source .venv/bin/activate
python -m pytest -m "not integration"
```

The one integration test hits NVIDIA NIM and is skipped unless
`NVIDIA_API_KEY` is set:

```bash
python -m pytest -m integration
```

The suite covers tool validation, path traversal, oversized code, the
run timeout, API-key scrubbing, lesson parsing, atomic progress writes,
corrupt-file recovery, CLI dispatch, and the retry forwarding check.

## Troubleshooting

- **401/403** – check `NVIDIA_API_KEY` in `.env`; auth errors are not retried.
- **429/5xx** – the OpenAI client retries three times with backoff, then the
  tutor reports a rate-limit or API error.
- **Model not found** – `MODEL_ID` must match a model on `build.nvidia.com`.
- **Tool calls fail** – pick a NIM model that supports tool calling.
- **Timeout** – generated code is killed after `RUN_TIMEOUT` seconds.
- **Corrupt progress.json** – it is copied to `progress.json.bak` and a fresh
  file starts automatically.

## Out of scope for this MVP

No web UI, Docker, RAG implementation, multi-agent orchestration, CodeAgent,
Windows support, or tracing. Those are deliberate later steps.
