import re
import json
from typing import Dict, Optional


class CharacterParser:
    def __init__(self, template_path: Optional[str] = None):
        self.template_path = template_path or "character_template.md"

    def parse_profile(self, raw_text: str) -> Dict:
        profile = {
            "name": "",
            "domain_affiliation": "",
            "titles_epithets": [],
            "role_status": "",
            "core_traits": [],
            "relative_power_standing": "",
            "personality_philosophy": {},
            "physical_appearance": {},
            "backstory_snapshot": {},
            "core_systems_execution_model": {},
            "dreamcraft_capabilities": {},
            "combat_simulation_logic": {},
            "quotes_and_resonance": {},
            "simulator_key_points": {},
            "final_remark": {}
        }

        sections = self._split_sections(raw_text)

        for section, content in sections.items():
            if "overview" in section or "identity" in section:
                self._parse_identity_block(content, profile)
            elif "personality" in section:
                self._parse_personality_block(content, profile)
            elif "appearance" in section:
                self._parse_appearance_block(content, profile)
            elif "backstory" in section:
                self._parse_backstory_block(content, profile)
            elif "core systems" in section or "execution model" in section:
                self._parse_core_systems_block(content, profile)
            elif "dreamcraft" in section or "capabilities" in section:
                self._parse_dreamcraft_block(content, profile)
            elif "combat simulation" in section or "simulation logic" in section:
                self._parse_combat_logic_block(content, profile)
            elif "quote" in section or "resonance" in section:
                self._parse_quote_block(content, profile)
            elif "key points" in section or "simulator" in section:
                self._parse_simulator_keys_block(content, profile)
            elif "final remark" in section:
                self._parse_final_remark_block(content, profile)

        return profile

    def _split_sections(self, raw_text: str) -> Dict[str, str]:
        pattern = r"(?<=\n)(?=---\n(.*)\n---)"
        split_text = re.split(pattern, raw_text)
        sections = {}
        current_section = None
        for line in split_text:
            line = line.strip()
            if line.startswith('---') and len(line) > 3:
                current_section = line.strip("- ").lower()
                sections[current_section] = ""
            elif current_section:
                sections[current_section] += line + "\n"
        return sections

    def _parse_identity_block(self, content: str, profile: Dict):
        name_match = re.search(r"Name: (.*)", content)
        if name_match:
            profile["name"] = name_match.group(1).strip()

        domain_match = re.search(r"Clan/Aliation|Domain/Affiliation: (.*)", content)
        if domain_match:
            profile["domain_affiliation"] = domain_match.group(1).strip()

        titles = re.findall(r"The .+", content)
        profile["titles_epithets"] = [title.strip() for title in titles]

        role_match = re.search(r"Role/Status: (.*)", content)
        if role_match:
            profile["role_status"] = role_match.group(1).strip()

        profile["core_traits"] = self._parse_bullets(content)
        power_standing_match = re.search(r"Relative Power Standing: (.*)", content)
        if power_standing_match:
            profile["relative_power_standing"] = power_standing_match.group(1).strip()

    def _parse_personality_block(self, content: str, profile: Dict):
        traits = self._parse_numbered(content)
        quote_match = re.search(r'>\s*(.*)', content)
        profile["personality_philosophy"] = {
            "personality_traits": traits,
            "guiding_outlook": quote_match.group(1).strip() if quote_match else ""
        }

    def _parse_appearance_block(self, content: str, profile: Dict):
        fields = {}
        for line in content.splitlines():
            if ':' in line:
                k, v = line.split(':', 1)
                fields[k.strip().lower()] = v.strip()
        profile["physical_appearance"] = {
            "digital_form": fields.get("digital form", ""),
            "symbolic_traits": fields.get("symbolic traits", ""),
            "aura": fields.get("aura", "")
        }

    def _parse_backstory_block(self, content: str, profile: Dict):
        story_points = self._parse_numbered(content)
        profile["backstory_snapshot"] = {f"point_{i+1}": p for i, p in enumerate(story_points)}

    def _parse_core_systems_block(self, content: str, profile: Dict):
        profile["core_systems_execution_model"] = {
            "operational_modes": [],
            "execution_rules": [],
            "tools_and_blades": {}
        }

        if "Full Sync Mode" in content:
            profile["core_systems_execution_model"]["operational_modes"].append({
                "mode": "Full Sync Mode",
                "description": "Maximum velocity execution; instantly implements, optimizes, and scales strategies"
            })

        if "Red-Green-Refactor" in content:
            profile["core_systems_execution_model"]["operational_modes"].append({
                "mode": "Red-Green-Refactor Mode",
                "description": "Precision mode for debugging, architecture, and test-driven design"
            })

        blades = []
        if "ChatGPT" in content:
            blades.append("The Architect’s Edge (ChatGPT)")
        if "Cursor" in content:
            blades.append("Cursor (Execution Workhorse)")

        profile["core_systems_execution_model"]["tools_and_blades"] = {
            "primary_blade": blades[0] if blades else "",
            "secondary_blade": blades[1] if len(blades) > 1 else "",
            "support_units": ["AgentDispatcher", "Aletheia", "DreamOS", "Aria"]
        }

        rules = self._parse_bullets(content)
        profile["core_systems_execution_model"]["execution_rules"] = rules

    def _parse_dreamcraft_block(self, content: str, profile: Dict):
        techniques = []
        blocks = re.split(r'\n(?=\d+\.\s)', content)
        for block in blocks:
            match = re.search(r"\d+\. ([^(]+) \(([^)]+)\):\s*(.*)", block)
            if match:
                techniques.append({
                    "name": match.group(1).strip(),
                    "type": match.group(2).strip(),
                    "effect": match.group(3).strip()
                })
        profile["dreamcraft_capabilities"]["techniques"] = techniques

    def _parse_combat_logic_block(self, content: str, profile: Dict):
        triggers = self._parse_bullets(content)
        profile["combat_simulation_logic"]["escalation_triggers"] = triggers
        profile["combat_simulation_logic"]["dominance_cycle"] = [
            "Initialize feedback loop",
            "Merge data into architectural state",
            "Execute convergence protocol",
            "Stabilize via growth recursion"
        ]
        profile["combat_simulation_logic"]["resource_management"] = (
            "Processes everything as data—no emotional energy lost to friction; turns stress into structure"
        )

    def _parse_quote_block(self, content: str, profile: Dict):
        quotes = re.findall(r'“([^”]+)”', content)
        profile["quotes_and_resonance"] = {
            "quotes": quotes,
            "dream_resonance": "He doesn’t conquer the Dreamscape. He builds it into something worth inheriting."
        }

    def _parse_simulator_keys_block(self, content: str, profile: Dict):
        keys = self._parse_bullets(content)
        profile["simulator_key_points"] = {f"key_{i+1}": point for i, point in enumerate(keys)}

    def _parse_final_remark_block(self, content: str, profile: Dict):
        quote_match = re.search(r'"([^"]+)"', content)
        profile["final_remark"] = {
            "statement": content.strip().splitlines()[0],
            "quote": quote_match.group(1) if quote_match else ""
        }

    def _parse_bullets(self, text: str):
        return [line.strip("- ").strip() for line in text.splitlines() if line.strip().startswith("-")]

    def _parse_numbered(self, text: str):
        return [line.strip().split('.', 1)[1].strip() for line in text.splitlines() if re.match(r"^\d+\.", line)]

    def save_to_json(self, data: Dict, path: str = "output_character.json"):
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
