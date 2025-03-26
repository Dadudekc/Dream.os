import os
import json
from battlesimulator.CharacterParser import CharacterParser
from battlesimulator.CharacterLoader import load_all_characters, load_character, list_character_names
from battlesimulator.core.engine import SimulationStageEngine
from battlesimulator.tournament_runner import run_tournament, format_leaderboard, save_tournament_results
import discord  # Ensure you have the discord.py library installed
import asyncio  # Added for asyncio operations
from discord.ext import commands
from typing import Dict, Any

CHARACTER_DIR = os.path.join(os.path.dirname(__file__), "characters")
MAIN_CONFIG = os.path.join(os.path.dirname(__file__), "main.json")

SIM_INSTANCES = {}  # Track active simulations by user/channel

# Initialize the Discord client
client = commands.Bot(command_prefix='!', intents=discord.Intents.all())

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

    elif command.startswith("!tournament"):
        results = run_tournament(full_battle=False)  # Default to single stage
        save_tournament_results(results)
        return format_leaderboard(results)

    elif command.startswith("!leaderboard"):
        try:
            with open("battlesimulator/main.json", "r") as f:
                data = json.load(f)
            results = data.get("tournament_results", {})
            if not results:
                return "No leaderboard found. Run `!tournament` first."
            return format_leaderboard(results)
        except Exception as e:
            return f"Error reading leaderboard: {e}"

    elif command.startswith("!profile"):
        name = tokens[1].capitalize()
        character = load_character(name)
        if not character:
            return f"❌ Character '{name}' not found."
        
        traits = character.get("core_traits", [])
        execution_modes = character.get("core_systems_execution_model", {}).get("operational_modes", [])
        power_tier = character.get("relative_power_standing", "")
        simulator_keys = character.get("simulator_key_points", {})

        profile_info = (
            f"**Profile for {name}:**\n"
            f"**Traits:** {', '.join(traits) if traits else 'None'}\n"
            f"**Execution Modes:** {', '.join(execution_modes) if execution_modes else 'None'}\n"
            f"**Power Tier:** {power_tier if power_tier else 'Unknown'}\n"
            f"**Simulator Keys:** {simulator_keys if simulator_keys else 'None'}"
        )
        return profile_info

    return "Unknown command. Use `!characters`, `!simulate A vs B`, `!status`, `!narration`, `!next`"

async def start_dm_battle(user):
    """Initiates a DM battle with Solomon in God Mode"""
    # Send initial message
    await user.send("You have encountered Solomon in God Mode! This battle cannot be won, but you can try your best!")
    
    # Battle loop
    while True:
        # Provide options to the player
        await user.send("Choose your action:\n1. Attack\n2. Defend\n3. Use Item\n4. Retreat")
        
        try:
            def check(m):
                return m.author == user and isinstance(m.channel, discord.DMChannel)
            
            msg = await client.wait_for('message', check=check, timeout=30)
            
            # Process the player's choice
            if msg.content == "1":
                await user.send("You attack Solomon! He takes no damage, but you feel the pressure!")
            elif msg.content == "2":
                await user.send("You defend yourself! Solomon smirks, knowing he cannot be beaten.")
            elif msg.content == "3":
                await user.send("You use an item! It has no effect on Solomon.")
            elif msg.content == "4":
                await user.send("You decide to retreat. Solomon lets you go, but the encounter haunts you.")
                break
            else:
                await user.send("Invalid choice! Please select a valid action.")
                
        except asyncio.TimeoutError:
            await user.send("You took too long to respond! The battle continues...")

@client.command()
async def battle(ctx):
    """Starts a battle with Solomon in God Mode"""
    await start_dm_battle(ctx.author)
