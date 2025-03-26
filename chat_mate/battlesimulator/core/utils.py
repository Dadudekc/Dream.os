import random
from typing import Dict, Any, List


def estimate_cost(rank: str) -> int:
    """Estimate chakra cost based on technique rank."""
    rank = rank.upper()
    if rank == "B":
        return random.randint(1, 3)
    elif rank == "A":
        return random.randint(4, 7)
    elif rank == "S":
        return random.randint(8, 15)
    elif rank == "ULTIMATE":
        return random.randint(15, 25)
    return 2  # fallback cost


def infer_rank(description: str) -> str:
    """Infer technique rank based on its description."""
    desc = description.lower()
    if "ultimate" in desc:
        return "ULTIMATE"
    if "massive" in desc or "devastating" in desc:
        return "S"
    if "precision" in desc or "swift" in desc:
        return "A"
    return "B"


def suggest_actions() -> List[str]:
    return random.sample([
        "Advance aggressively",
        "Defend and conserve chakra",
        "Exploit environmental hazards",
        "Retreat to re-assess positions"
    ], k=3)


def format_chakra(chakra: Dict[str, int]) -> str:
    return ", ".join([f"{name}: {val}%" for name, val in chakra.items()]) 