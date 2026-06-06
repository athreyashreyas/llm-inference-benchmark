"""Prompt loading and selection utilities."""

import json
import random
from pathlib import Path
from typing import List, Dict


PROMPTS_PATH = Path(__file__).parent.parent / "data" / "prompts.json"


def load_prompts(path: Path = PROMPTS_PATH) -> List[Dict]:
    """Load the full prompt bank from disk."""
    with open(path) as f:
        return json.load(f)


def get_prompts_by_type(prompt_type: str, path: Path = PROMPTS_PATH) -> List[Dict]:
    """Return all prompts matching a given type ('short', 'medium', 'long')."""
    return [p for p in load_prompts(path) if p["type"] == prompt_type]


def sample_prompts(prompt_type: str, n: int, seed: int | None = None) -> List[Dict]:
    """Sample n prompts of a given type, with optional seeding for reproducibility."""
    prompts = get_prompts_by_type(prompt_type)
    rng = random.Random(seed)
    if n <= len(prompts):
        return rng.sample(prompts, n)
    # Sample with replacement if n exceeds pool size
    return [rng.choice(prompts) for _ in range(n)]


def shuffle_prompts(prompts: List[Dict], seed: int | None = None) -> List[Dict]:
    """Return a shuffled copy of the prompt list."""
    rng = random.Random(seed)
    shuffled = list(prompts)
    rng.shuffle(shuffled)
    return shuffled
