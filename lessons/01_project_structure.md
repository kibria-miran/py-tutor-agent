---
id: 01
title: Project Structure with a src Layout
objectives: [lay out a src-style Python project, explain what a package is]
estimated_min: 15
---
## Concept
A src-style project keeps importable code in src/<name>/ and tests in a
top-level tests/ folder. A directory with __init__.py is a regular package.
The src layout stops you from accidentally importing code from the repo
root instead of the installed package.

## Example (runnable)
```python
from pathlib import Path

files = [
    "myproj/src/myproj/__init__.py",
    "myproj/src/myproj/client.py",
    "myproj/tests/test_client.py",
    "myproj/pyproject.toml",
    "myproj/README.md",
]
for f in files:
    p = Path(f)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.touch()
    print("created", p)
```

## Exercise
Create a src-style layout for a project called `llm_client` with a package,
a `config.py` module inside it, a `tests/` folder with one test file, and a
`pyproject.toml`. Print the file tree.

## Quiz
Q1: In a src-layout project, where does the package code live? | A) src/<name>/ B) the repo root only C) tests/ | answer: A
Q2: Which file marks a directory as a regular package? | A) main.py B) __init__.py C) setup.txt | answer: B
Q3: Where should tests normally live? | A) inside __init__.py B) inside .venv C) a top-level tests/ folder | answer: C
Q4: What is the main benefit of the src layout? | A) faster imports B) avoids accidentally importing from the repo root C) smaller wheels | answer: B
Q5: Which entry belongs in .gitignore? | A) .venv/ B) src/ C) pyproject.toml | answer: A
