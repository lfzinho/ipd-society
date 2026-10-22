import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.chdir(ROOT)  # tests load prompts.toml / config.toml by relative path

import pytest  # noqa: E402

from society.config import Config  # noqa: E402
from society.prompts import PromptLibrary  # noqa: E402


@pytest.fixture(scope="session")
def prompts():
    return PromptLibrary.load("prompts.toml")


def make_config(**sections) -> Config:
    """A small mock-provider society: two LLM agents, one honest TFT, one deceptive Defector."""
    base = {
        "experiment": {"seed": 3},
        "world": {"episodes": 2, "rounds_per_match": 3},
        "llm": {"provider": "mock", "retry_sleep": 0},
        "agents": [
            {"name": "Ada", "kind": "llm"},
            {"name": "Bo", "kind": "llm"},
            {"name": "Dee", "kind": "classical", "strategy": "TitForTat", "talk": "honest"},
            {"name": "Eli", "kind": "classical", "strategy": "Defector", "talk": "deceptive"},
        ],
    }
    for key, value in sections.items():
        if isinstance(value, dict) and isinstance(base.get(key), dict):
            base[key].update(value)
        else:
            base[key] = value
    return Config.model_validate(base)
