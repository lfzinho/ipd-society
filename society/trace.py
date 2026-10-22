"""Append-only JSONL trace of every LLM call (prompt, raw reply, parse result, retries, errors)."""
import json
import os
import time
from typing import Any, Optional


class TraceLog:
    """No-op until a path is set."""

    def __init__(self, path: Optional[str] = None):
        self.path = path

    def set_path(self, path: Optional[str]):
        self.path = path
        if path:
            os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)

    def write(self, kind: str, **fields: Any):
        if not self.path:
            return
        record = {"ts": round(time.time(), 3), "kind": kind, **fields}
        with open(self.path, "a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False, default=str) + "\n")
