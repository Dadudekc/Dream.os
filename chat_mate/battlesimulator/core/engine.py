import random
from typing import Dict, Any, List
from battlesimulator.core.utils import estimate_cost, infer_rank, suggest_actions, format_chakra


class SimulationStageEngine:
    def __init__(self, char_a: Dict[str, Any], char_b: Dict[str, Any], chakra: Dict[str, int], global_log: List[str]):
        self.char_a = char_a
        self.char_b = char_b
        self.chakra = chakra.copy()
        self.global_log = global_log
        self.stage = 0
        self.time_elapsed = 0
        self.positions = {char_a["name"]: "Center", char_b["name"]: "Center"}
        self.conditions = {char_a["name"]: "Healthy", char_b["name"]: "Healthy"}
        self.action_log: List[Dict[str, Any]] = []
        self.environment = self._select_random_environment()

    def _log(self, msg: str):
        log_msg = f"[Engine] {msg}"
        self.global_log.append(log_msg)
        print(log_msg)

    def _select_random_environment(self) -> str:
        options = [
            "Abandoned Leaf Village training grounds",
            "Hidden Forest with perilous terrain",
            "Ravaged battlefield near a ruined fortress",
            "Fog-shrouded valley with unstable ground"
        ]
        env = random.choice(options)
        self._log(f"Environment selected: {env}")
        return env

    def _simulate_actions(self, character: Dict[str, Any]) -> List[Dict[str, Any]]:
        techniques = character.get("signature_techniques", [])
        if not techniques:
            return []
        actions = random.sample(techniques, k=random.randint(1, min(3, len(techniques))))
        validated = []
        for action in actions:
            if action.get("name") and action.get("type") and action.get("description"):
                rank = action.get("rank") or infer_rank(action["description"])
                validated.append({
                    "name": action["name"],
                    "type": action["type"],
                    "rank": rank,
                    "description": action["description"],
                    "source": character["name"]
                })
        self.action_log.append({character["name"]: validated})
        self._log(f"{character['name']} executes: {[a['name'] for a in validated]}")
        return validated

    def _apply_chakra_costs(self, name: str, actions: List[Dict[str, Any]]):
        total = sum([estimate_cost(a["rank"]) for a in actions])
        self.chakra[name] -= total
        self._log(f"{name} spent {total}% chakra. Remaining: {self.chakra[name]}%")

    def _resolve_positions(self):
        self.positions[self.char_a["name"]] = "Flank"
        self.positions[self.char_b["name"]] = "Center"
        self._log("Positions resolved.")

    def _resolve_conditions(self):
        for name in self.chakra:
            self.conditions[name] = "Fatigued" if self.chakra[name] < 20 else "Healthy"
        self._log("Conditions updated.")

    def _render_dashboard(self, duration: int) -> Dict[str, Any]:
        return {
            "stage": self.stage,
            "time_elapsed_in_stage": duration,
            "total_time_elapsed": self.time_elapsed,
            "chakra": self.chakra.copy(),
            "conditions": self.conditions.copy(),
            "positions": self.positions.copy(),
            "environment": self.environment,
            "suggested_actions": {
                self.char_a["name"]: suggest_actions(),
                self.char_b["name"]: suggest_actions()
            },
            "prompt": f"Stage {self.stage} complete. Proceed to Stage {self.stage + 1}?"
        }

    def render_narration(self) -> str:
        lines = [f"Stage {self.stage} Battle Report:"]
        for entry in self.action_log[-2:]:
            for name, actions in entry.items():
                for act in actions:
                    lines.append(
                        f"{name} unleashed '{act['name']}' ({act['type']} - {act['rank']} Rank). {act['description']}"
                    )
        lines.append(f"Environment: {self.environment}")
        lines.append("Chakra Status: " + format_chakra(self.chakra))
        self._log("Narration generated.")
        return "\n".join(lines)

    def run_stage(self) -> Dict[str, Any]:
        self.stage += 1
        duration = random.randint(30, 60)
        self.time_elapsed += duration
        self._log(f"--- Stage {self.stage} begins ({duration}s) ---")
        actions_a = self._simulate_actions(self.char_a)
        actions_b = self._simulate_actions(self.char_b)
        self._apply_chakra_costs(self.char_a["name"], actions_a)
        self._apply_chakra_costs(self.char_b["name"], actions_b)
        self._resolve_positions()
        self._resolve_conditions()
        return self._render_dashboard(duration) 