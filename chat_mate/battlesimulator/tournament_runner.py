from battlesimulator.CharacterLoader import load_all_characters
from battlesimulator.core.engine import SimulationStageEngine
from typing import Dict, Any, List
import itertools


def run_tournament_stage_only() -> Dict[str, Any]:
    characters = load_all_characters()
    names = list(characters.keys())
    results = {name: {"wins": 0, "losses": 0, "total_chakra": 0} for name in names}

    for a, b in itertools.combinations(names, 2):
        char_a = characters[a]
        char_b = characters[b]
        chakra = {a: 200, b: 200}
        sim = SimulationStageEngine(char_a, char_b, chakra, [])
        sim.run_stage()

        # Determine winner based on chakra remaining
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
        else:
            # Draw logic can be expanded
            pass

    return results


def format_leaderboard(results: Dict[str, Any]) -> str:
    sorted_leaderboard = sorted(results.items(), key=lambda x: (-x[1]["wins"], -x[1]["total_chakra"]))
    lines = ["🏆 Tournament Leaderboard:"]
    for i, (name, stats) in enumerate(sorted_leaderboard, 1):
        lines.append(f"{i}. {name}: {stats['wins']}W - {stats['losses']}L | Chakra: {stats['total_chakra']}")
    return "\n".join(lines)


if __name__ == "__main__":
    results = run_tournament_stage_only()
    leaderboard = format_leaderboard(results)
    print(leaderboard) 