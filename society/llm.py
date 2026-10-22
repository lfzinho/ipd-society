"""One place that talks to a language model.

`LLMClient.ask()` sends a prompt, parses the JSON reply into a pydantic model, retries on
failure and writes a trace record. If every attempt fails it raises `LLMCallFailed`; the
caller (an agent) decides what the neutral fallback is, and `FallbackGuard` stops the run
if too many fallbacks happen in a row, so an outage cannot silently turn into noise.

Providers: `openrouter`, `ollama` (any OpenAI-compatible chat endpoint) and `mock`, an
offline stand-in whose behaviour is defined in `society/mock.py` and used by the tests.
"""
import json
import os
import re
import time
from collections import Counter
from typing import Any, Callable, Dict, Optional, Type, TypeVar

from pydantic import BaseModel

from society.trace import TraceLog

T = TypeVar("T", bound=BaseModel)


class LLMCallFailed(Exception):
    """One logical call failed after all retries."""


class LLMUnavailableError(RuntimeError):
    """Too many consecutive fallbacks: the run stops so the cause can be fixed and resumed."""


def extract_json(text: str) -> Dict[str, Any]:
    """Parses the first JSON object in a reply (models sometimes wrap it in prose or code fences)."""
    text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        raise ValueError(f"no JSON object in reply: {text[:120]!r}")
    return json.loads(match.group(0))


class FallbackGuard:
    """Counts consecutive fallbacks across all agents and aborts when a threshold is reached."""

    def __init__(self, limit: int):
        self.limit = limit
        self.consecutive = 0

    def ok(self):
        self.consecutive = 0

    def failed(self, who: str):
        self.consecutive += 1
        if self.consecutive >= self.limit:
            raise LLMUnavailableError(
                f"{self.consecutive} consecutive LLM failures (last: {who}). "
                f"See trace.jsonl for the errors; rerun the same command to resume."
            )


class LLMClient:
    def __init__(self, provider: str, model: Optional[str], temperature: float = 0.4, max_retries: int = 3,
                 timeout: float = 120.0, retry_sleep: float = 1.0, trace: Optional[TraceLog] = None,
                 mock_fn: Optional[Callable[..., BaseModel]] = None):
        self.provider = provider
        self.model = model or {"openrouter": os.getenv("OPENROUTER_MODEL", "anthropic/claude-haiku-5.5"),
                               "ollama": os.getenv("OLLAMA_MODEL", "llama3"), "mock": "mock"}[provider]
        self.temperature = temperature
        self.max_retries = max(1, max_retries)
        self.timeout = timeout
        self.retry_sleep = retry_sleep
        self.trace = trace or TraceLog()
        self.mock_fn = mock_fn
        self.stats: Counter = Counter()
        self._client = None

    def _client_for_provider(self):
        if self._client is not None:
            return self._client
        from openai import OpenAI
        if self.provider == "openrouter":
            key = os.getenv("OPENROUTER_API_KEY") or os.getenv("OPEN_ROUTER_KEY")
            if not key:
                raise RuntimeError("OPENROUTER_API_KEY is not set")
            self._client = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=key, timeout=self.timeout)
        else:
            host = os.getenv("OLLAMA_HOST", "http://localhost:11434")
            if "://" not in host:
                host = "http://" + host
            self._client = OpenAI(base_url=host.rstrip("/").removesuffix("/v1") + "/v1", api_key="ollama",
                                  timeout=self.timeout)
        return self._client

    def _raw_call(self, prompt: str) -> tuple:
        """Returns (reply text, (prompt_tokens, completion_tokens))."""
        client = self._client_for_provider()
        completion = client.chat.completions.create(
            model=self.model, temperature=self.temperature,
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
        )
        usage = getattr(completion, "usage", None)
        tokens = (getattr(usage, "prompt_tokens", 0) or 0, getattr(usage, "completion_tokens", 0) or 0)
        return completion.choices[0].message.content or "", tokens

    def ask(self, kind: str, prompt: str, schema: Type[T], agent: str = "", hint: Optional[dict] = None,
            **trace_fields) -> T:
        errors = []
        started = time.time()
        for attempt in range(1, self.max_retries + 1):
            try:
                if self.provider == "mock":
                    parsed = self.mock_fn(kind, schema, hint or {})
                    raw, tokens = parsed.model_dump_json(), (0, 0)
                else:
                    raw, tokens = self._raw_call(prompt)
                    parsed = schema.model_validate(extract_json(raw))
                self.stats["calls"] += 1
                self.stats["retries"] += attempt - 1
                self.stats["prompt_tokens"] += tokens[0]
                self.stats["completion_tokens"] += tokens[1]
                self.trace.write(kind, agent=agent, prompt=prompt, raw=raw, parsed=parsed.model_dump(),
                                 attempts=attempt, errors=errors, tokens=list(tokens),
                                 latency=round(time.time() - started, 2), **trace_fields)
                return parsed
            except Exception as e:  # network, rate limit, bad JSON, schema mismatch
                errors.append(f"{type(e).__name__}: {e}")
                self.stats["parse_failures" if isinstance(e, (ValueError, json.JSONDecodeError)) else "errors"] += 1
                if attempt < self.max_retries:
                    time.sleep(self.retry_sleep * attempt)
        self.stats["failed_calls"] += 1
        self.trace.write(kind, agent=agent, prompt=prompt, failed=True, attempts=self.max_retries,
                         errors=errors, latency=round(time.time() - started, 2), **trace_fields)
        raise LLMCallFailed(f"{kind} for {agent}: {errors[-1]}")
