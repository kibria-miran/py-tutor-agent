---
id: 03
title: API Clients, Timeouts, and Retries
objectives: [add timeouts to API calls, retry transient failures with exponential backoff, avoid retrying auth errors]
estimated_min: 20
---
## Concept
Every network call needs a timeout. Without one, a stalled server can
hang your program forever. A good client also retries transient
failures: HTTP 429 (rate limit) and 5xx responses. It does not retry
401 or 403, because the request will keep failing.

Retries use exponential backoff: wait 1 second, then 2, then 4. Add a
small random jitter when several clients may retry at once. Cap the
number of attempts so a broken dependency cannot loop forever. Keep
retry logic in one client layer, not scattered through the code.

## Example (runnable)
```python
import time
from dataclasses import dataclass


@dataclass
class Response:
    status: int
    body: str


attempts = {"n": 0}


def flaky_call() -> Response:
    attempts["n"] += 1
    if attempts["n"] < 3:
        return Response(503, "try again")
    return Response(200, "ok")


def request_with_retry(call, retries: int = 3, base_delay: float = 0.1) -> Response:
    response = Response(500, "no attempt made")
    for attempt in range(retries):
        response = call()
        transient = response.status == 429 or response.status >= 500
        if not transient:
            return response
        if attempt < retries - 1:
            time.sleep(base_delay * (2**attempt))
    return response


result = request_with_retry(flaky_call)
print(f"status={result.status} attempts={attempts['n']}")
```

## Exercise
Extend the example so retries happen only for 429 and 5xx responses.
Add a `max_delay` cap and a tiny random jitter. Write a second fake
call that always returns 401 and prove it is tried exactly once.

## Quiz
Q1: Why does every API call need a timeout? | A) to make code longer B) to avoid hanging forever on a stalled server C) to avoid authentication | answer: B
Q2: Which responses should normally be retried? | A) 429 and 5xx B) 401 and 403 C) 200 and 201 | answer: A
Q3: What does exponential backoff do? | A) doubles the wait after each failed attempt B) sends requests faster C) removes all errors | answer: A
Q4: Why add jitter to backoff delays? | A) to make logs shorter B) to spread out retries from many clients C) to skip the timeout | answer: B
Q5: Where should retry logic live? | A) in every call site B) only in the API client layer C) inside the prompt | answer: B
