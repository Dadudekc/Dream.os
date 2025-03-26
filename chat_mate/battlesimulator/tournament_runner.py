from battlesimulator.CharacterLoader import load_all_characters
from battlesimulator.core.engine import SimulationStageEngine
from typing import Dict, Any, List
import itertools
import json


def run_tournament(full_battle: bool = False) -> Dict[str, Any]:
    characters = load_all_characters()
    names = list(characters.keys())
    results = {name: {"wins": 0, "losses": 0, "total_chakra": 0} for name in names}

    for a, b in itertools.combinations(names, 2):
        char_a = characters[a]
        char_b = characters[b]
        chakra = {a: 200, b: 200}
        sim = SimulationStageEngine(char_a, char_b, chakra, [])

        if full_battle:
            for _ in range(3):
                sim.run_stage()
        else:
            sim.run_stage()

        chakra_a = sim.chakra[a]
        chakra_b = sim.chakra[b]
        results[a]["total_chakra"] += chakra_a
        results[b]["total_chakra"] += chakra_b

        if chakra_a > chakra_b:
            results[a]["wins"] += 1
            results[b]["losses"] += 1
        elif chakra_b > chakra_a:
            results[b]["wins"] += 1
            results[a]["losses"] += 1

    return results


def format_leaderboard(results: Dict[str, Any]) -> str:
    sorted_leaderboard = sorted(results.items(), key=lambda x: (-x[1]["wins"], -x[1]["total_chakra"]))
    lines = ["🏆 Tournament Leaderboard:"]
    for i, (name, stats) in enumerate(sorted_leaderboard, 1):
        lines.append(f"{i}. {name}: {stats['wins']}W - {stats['losses']}L | Chakra: {stats['total_chakra']}")
    return "\n".join(lines)


def save_tournament_results(results: Dict[str, Any], filepath: str = "battlesimulator/main.json"):
    try:
        with open(filepath, "r") as f:
            data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        data = {}

    data["tournament_results"] = results
    with open(filepath, "w") as f:
        json.dump(data, f, indent=2)


if __name__ == "__main__":
    results = run_tournament(full_battle=False)
    save_tournament_results(results)
    print(format_leaderboard(results)) 