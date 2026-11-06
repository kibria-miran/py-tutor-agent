---
id: 02
title: Configuration and Secrets with .env
objectives: [load config from environment variables, keep secrets out of code and git]
estimated_min: 15
---
## Concept
Configuration belongs in the environment, not in source code. A local
`.env` file holds development values, `python-dotenv` loads it into
`os.environ`, and `.gitignore` keeps it out of git. Production should
inject the same variables from the platform, so the code does not care
where they came from.

Read configuration once at startup, validate it, and fail fast with a
clear message when something required is missing. Never print a secret;
mask it if you must show that it is present.

## Example (runnable)
```python
import os
from pathlib import Path
from dotenv import load_dotenv

Path("sample.env").write_text(
    "APP_ENV=dev\nREQUEST_TIMEOUT=30\n",
    encoding="utf-8",
)
load_dotenv("sample.env")

app_env = os.getenv("APP_ENV", "dev")
timeout = int(os.getenv("REQUEST_TIMEOUT", "30"))
print(f"env={app_env} timeout={timeout}")

if not os.getenv("LLM_API_KEY"):
    print("LLM_API_KEY is missing: real code should fail fast here")
```

## Exercise
Create `config.py` that reads `LLM_API_KEY`, `MODEL_ID`, and
`REQUEST_TIMEOUT` from the environment. Raise a clear error if
`LLM_API_KEY` is missing, give the timeout a default, and add a
`masked_key()` helper that prints only the last four characters.
Create a matching `.env.example` with placeholder values.

## Quiz
Q1: What should never be committed to git? | A) .env B) README.md C) pyproject.toml | answer: A
Q2: Which library loads a .env file into os.environ? | A) argparse B) python-dotenv C) pathlib | answer: B
Q3: Why validate configuration at startup? | A) it makes imports slower B) it fails fast with a clear error C) it hides missing keys | answer: B
Q4: Where should production secrets come from? | A) hardcoded strings B) the platform environment C) a comment in code | answer: B
Q5: What is the safest way to show that a key exists? | A) print the whole key B) print os.environ C) print only a masked suffix | answer: C
