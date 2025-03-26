import os
import json
from battlesimulator.CharacterParser import CharacterParser
from battlesimulator.CharacterLoader import load_all_characters, load_character, list_character_names
from battlesimulator.core.engine import SimulationStageEngine

CHARACTER_DIR = os.path.join(os.path.dirname(__file__), "characters")
MAIN_CONFIG = os.path.join(os.path.dirname(__file__), "main.json")

SIM_INSTANCES = {}  # Track active simulations by user/channel


class CommandRouter:
    def __init__(self):
        self.character_parser = CharacterParser()
        self.characters = self._load_all_characters()

    def _load_all_characters(self):
        characters = {}
        for filename in os.listdir(CHARACTER_DIR):
            if filename.endswith(".json"):
                path = os.path.join(CHARACTER_DIR, filename)
                try:
                    with open(path, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        characters[data["name"]] = data
                except Exception as e:
                    print(f"⚠️ Failed to load {filename}: {str(e)}")
        return characters

    def list_roster(self):
        return list(self.characters.keys())

    def get_character(self, name):
        return self.characters.get(name)

    def simulate_battle(self, name1, name2):
        char1 = self.get_character(name1)
        char2 = self.get_character(name2)
        if not char1 or not char2:
            return f"❌ One or both characters not found: {name1}, {name2}"

        result = {
            "character_1": name1,
            "character_2": name2,
            "result": f"{name1} and {name2} clashed. Simulation module pending deeper logic...",
            "mode": "preview"
        }

        self._write_to_main(result)
        return result

    def _write_to_main(self, simulation_data):
        config = {}
        if os.path.exists(MAIN_CONFIG):
            with open(MAIN_CONFIG, "r", encoding="utf-8") as f:
                config = json.load(f)
        config["last_simulation"] = simulation_data
        with open(MAIN_CONFIG, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2)

    def compare_characters(self, name1, name2):
        char1 = self.get_character(name1)
        char2 = self.get_character(name2)
        if not char1 or not char2:
            return f"❌ One or both characters not found: {name1}, {name2}"

        def extract_traits(char):
            return {
                "Traits": char.get("core_traits", []),
                "Execution Modes": char.get("core_systems_execution_model", {}).get("operational_modes", []),
                "Power Tier": char.get("relative_power_standing", ""),
                "Simulator Keys": char.get("simulator_key_points", {})
            }

        return {
            "comparison": {
                name1: extract_traits(char1),
                name2: extract_traits(char2)
            }
        }

    def load_character_from_file(self, filepath):
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
                name = data["name"]
                self.characters[name] = data
                print(f"✅ Loaded character: {name}")
                return name
        except Exception as e:
            print(f"❌ Failed to load character from {filepath}: {str(e)}")
            return None


def handle_command(command: str, user_id: str = "default") -> str:
    tokens = command.strip().lower().split()

    if command.startswith("!characters"):
        return ", ".join(list_character_names())

    elif command.startswith("!simulate"):
        try:
            name_a, name_b = tokens[1].capitalize(), tokens[3].capitalize()
            char_a = load_character(name_a)
            char_b = load_character(name_b)
            chakra = {char_a["name"]: 200, char_b["name"]: 200}
            sim = SimulationStageEngine(char_a, char_b, chakra, [])
            SIM_INSTANCES[user_id] = sim
            dashboard = sim.run_stage()
            return f"Simulating {name_a} vs {name_b}...\nStage {dashboard['stage']} complete."
        except Exception as e:
            return f"Simulation error: {str(e)}"

    elif command.startswith("!status"):
        sim = SIM_INSTANCES.get(user_id)
        if not sim:
            return "No simulation in progress."
        return f"Current Stage: {sim.stage}\nChakra: {sim.chakra}"

    elif command.startswith("!narration"):
        sim = SIM_INSTANCES.get(user_id)
        if not sim:
            return "No active simulation to narrate."
        return sim.render_narration()

    elif command.startswith("!next"):
        sim = SIM_INSTANCES.get(user_id)
        if not sim:
            return "No simulation in progress."
        dashboard = sim.run_stage()
        return f"Stage {dashboard['stage']} complete.\nPrompt: {dashboard['prompt']}"

    return "Unknown command. Use `!characters`, `!simulate A vs B`, `!status`, `!narration`, `!next`"
