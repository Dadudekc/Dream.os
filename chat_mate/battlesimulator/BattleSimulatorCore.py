import random
from typing import Dict, Any, List

class SimulationStageEngine:
    """
    Encapsulates one stage of battle simulation.
    Handles:
      - Stage timing and progression
      - Tactical action simulation (with rank inference)
      - Chakra cost calculation and deduction
      - Positional and condition updates
      - Generating a battle dashboard and anime-style narration
    """
    def __init__(self, char_a: Dict[str, Any], char_b: Dict[str, Any], initial_chakra: Dict[str, int], global_log: List[str]):
        self.char_a = char_a
        self.char_b = char_b
        self.chakra = initial_chakra.copy()  # e.g. {"Victor": 200, "Solomon": 200}
        self.global_log = global_log  # Shared log for all simulation events
        self.stage = 0
        self.time_elapsed = 0  # in seconds
        self.positions = {char_a["name"]: "Center", char_b["name"]: "Center"}
        self.conditions = {char_a["name"]: "Healthy", char_b["name"]: "Healthy"}
        self.action_log: List[Dict[str, Any]] = []
        self.environment = self._select_random_environment()

    def _select_random_environment(self) -> str:
        environments = [
            "Abandoned Leaf Village training grounds",
            "Hidden Forest with perilous terrain",
            "Ravaged battlefield near a ruined fortress",
            "Fog-shrouded valley with unstable ground"
        ]
        env = random.choice(environments)
        self._log(f"Environment selected: {env}")
        return env

    def _log(self, entry: str):
        log_entry = f"[Stage Engine] {entry}"
        self.global_log.append(log_entry)
        print(log_entry)

    def _estimate_cost(self, rank: str) -> int:
        # Chakra cost estimation based on technique rank.
        rank = rank.upper()
        if rank == "B":
            return random.randint(1, 3)
        elif rank == "A":
            return random.randint(4, 7)
        elif rank == "S":
            return random.randint(8, 15)
        elif rank == "ULTIMATE":
            return random.randint(15, 25)
        return 2  # default cost

    def _infer_rank(self, description: str) -> str:
        # Infer rank based on keywords in the description.
        desc = description.lower()
        if "ultimate" in desc:
            return "ULTIMATE"
        if "massive" in desc or "devastating" in desc:
            return "S"
        if "precision" in desc or "swift" in desc:
            return "A"
        return "B"

    def _simulate_actions(self, character: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Randomly selects 1-3 valid actions from the combatant's signature techniques.
        Infers rank based on technique description.
        """
        techniques = character.get("signature_techniques", [])
        if not techniques:
            return []
        num_actions = random.randint(1, min(3, len(techniques)))
        actions = random.sample(techniques, k=num_actions)
        validated = []
        for action in actions:
            if action.get("name") and action.get("type") and action.get("description"):
                # Use provided rank if available; otherwise infer from description.
                rank = action.get("rank") or self._infer_rank(action["description"])
                validated.append({
                    "name": action["name"],
                    "type": action["type"],
                    "rank": rank,
                    "description": action["description"],
                    "source": character["name"]
                })
        self.action_log.append({character["name"]: validated})
        self._log(f"{character['name']} executes: {[act['name'] for act in validated]}")
        return validated

    def _apply_chakra_costs(self, name: str, actions: List[Dict[str, Any]]):
        total_cost = 0
        for action in actions:
            cost = self._estimate_cost(action.get("rank", "B"))
            total_cost += cost
        self.chakra[name] -= total_cost
        self._log(f"{name} expended {total_cost}% chakra; remaining: {self.chakra[name]}%")

    def _resolve_positions(self):
        # Placeholder for positional logic; can be enhanced with grid dynamics.
        self.positions[self.char_a["name"]] = "Flank"
        self.positions[self.char_b["name"]] = "Center"
        self._log("Positions updated: " + str(self.positions))

    def _resolve_conditions(self):
        # Update conditions based on chakra thresholds.
        for name, chakra in self.chakra.items():
            if chakra < 20:
                self.conditions[name] = "Fatigued"
            else:
                self.conditions[name] = "Healthy"
        self._log("Conditions updated: " + str(self.conditions))

    def _suggest_actions(self, character: Dict[str, Any]) -> List[str]:
        # Tactical suggestions can be refined further.
        suggestions = [
            "Advance aggressively",
            "Defend and conserve chakra",
            "Exploit environmental hazards",
            "Retreat to re-assess positions"
        ]
        return random.sample(suggestions, k=3)

    def _render_battle_dashboard(self, stage_duration: int) -> Dict:
        dashboard = {
            "stage": self.stage,
            "time_elapsed_in_stage": stage_duration,
            "total_time_elapsed": self.time_elapsed,
            "chakra": self.chakra.copy(),
            "conditions": self.conditions.copy(),
            "positions": self.positions.copy(),
            "environment": self.environment,
            "suggested_actions": {
                self.char_a["name"]: self._suggest_actions(self.char_a),
                self.char_b["name"]: self._suggest_actions(self.char_b)
            },
            "prompt": f"Stage {self.stage} complete. Do you wish to proceed to Stage {self.stage + 1}?"
        }
        self._log("Dashboard rendered")
        return dashboard

    def render_narration(self) -> str:
        # Generate a narrative from the last stage's actions.
        narration_lines = [f"Stage {self.stage} Battle Report:"]
        # Use only the latest actions (if available)
        for entry in self.action_log[-2:]:
            for name, actions in entry.items():
                for act in actions:
                    narration_lines.append(
                        f"{name} unleashes '{act['name']}' ({act['type']} - {act['rank']} Rank). {act['description']} strikes with brutal precision!"
                    )
        narration_lines.append(f"Environment: {self.environment}")
        narration_lines.append("Chakra Status: " +
            ", ".join([f"{name}: {chakra}%" for name, chakra in self.chakra.items()]))
        narration = "\n".join(narration_lines)
        self._log("Narration generated")
        return narration

    def run_stage(self) -> Dict:
        self.stage += 1
        stage_duration = random.randint(30, 60)
        self.time_elapsed += stage_duration
        self._log(f"--- Stage {self.stage} initiated. {stage_duration} seconds elapsed this stage ---")

        # Simulate actions for both combatants.
        actions_a = self._simulate_actions(self.char_a)
        actions_b = self._simulate_actions(self.char_b)

        self._apply_chakra_costs(self.char_a["name"], actions_a)
        self._apply_chakra_costs(self.char_b["name"], actions_b)

        self._resolve_positions()
        self._resolve_conditions()

        dashboard = self._render_battle_dashboard(stage_duration)
        return dashboard


class BattleSimulatorCore:
    """
    Main battle simulator engine.
    Sets up combatants, initializes chakra reserves based on traits/roles,
    and manages stage progression.
    """
    def __init__(self, char_a: Dict[str, Any], char_b: Dict[str, Any]):
        self.char_a = char_a
        self.char_b = char_b
        self.global_log: List[str] = []
        self.initial_chakra = self._initialize_chakra()
        self.stage_engine = SimulationStageEngine(self.char_a, self.char_b, self.initial_chakra, self.global_log)

    def _initialize_chakra(self) -> Dict[str, int]:
        # Determine initial chakra based on character traits.
        def chakra_for(char: Dict[str, Any]) -> int:
            base = 100
            if "Sage Mode" in char.get("core_traits", []) or "Sage Mode" in char.get("role_status", ""):
                base = 165
            if "Perfect Jinchūriki" in char.get("role_status", ""):
                base = 200
            return base

        chakra = {
            self.char_a["name"]: chakra_for(self.char_a),
            self.char_b["name"]: chakra_for(self.char_b)
        }
        self._log(f"Initial chakra set: {chakra}")
        return chakra

    def _log(self, entry: str):
        log_entry = f"[BattleSimulatorCore] {entry}"
        self.global_log.append(log_entry)
        print(log_entry)

    def run_full_simulation(self, stages: int = 1) -> Dict:
        simulation_results = []
        for _ in range(stages):
            dashboard = self.stage_engine.run_stage()
            narration = self.stage_engine.render_narration()
            simulation_results.append({
                "dashboard": dashboard,
                "narration": narration
            })
            self._log(f"Completed Stage {dashboard['stage']}")
        final_state = {
            "final_chakra": self.stage_engine.chakra,
            "stages_run": stages,
            "global_log": self.global_log,
            "results": simulation_results
        }
        return final_state


# === Example Usage ===
if __name__ == "__main__":
    # Sample character definitions (could be loaded from JSON in production)
    char_victor = {
        "name": "Victor",
        "role_status": "Perfect Jinchūriki",
        "core_traits": ["Full Sync Mode", "Strategic Resolve", "Sage Mode"],
        "signature_techniques": [
            {
                "name": "Gravity Collapse Zone",
                "type": "Area Denial",
                "description": "A devastating gravitational sinkhole that crushes all within range."
            },
            {
                "name": "Skyfang Barrage",
                "type": "Ranged Strike",
                "description": "A flurry of talon missiles in curved gravitational arcs with swift precision."
            }
        ]
    }
    char_solomon = {
        "name": "Solomon",
        "role_status": "Exile / Wanderer; Perfect Jinchūriki",
        "core_traits": ["Calculated and stoic", "Controlled escalation"],
        "signature_techniques": [
            {
                "name": "Eclipse Fang Severance",
                "type": "Dimensional Chain",
                "description": "Chains that sever chakra pathways with brutal efficiency."
            },
            {
                "name": "Enkō no Ōkami",
                "type": "Summon",
                "description": "Summons a blazing wolf pack with visceral, relentless strikes."
            }
        ]
    }

    simulator = BattleSimulatorCore(char_victor, char_solomon)
    # Run simulation for 2 stages as demonstration.
    results = simulator.run_full_simulation(stages=2)
    for stage in results["results"]:
        print(stage["narration"])
        print(stage["dashboard"])
        print("-" * 80)
    print("\nFinal Simulation Results:")
    print(results)
