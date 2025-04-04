import json
import os
import logging
from pathlib import Path
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)

class ResonanceScorer:
    """
    Loads multiple resonance models from a directory (e.g. romantic.json, friendship.json)
    and scores a given profile dict based on alignment with a selected model's criteria:
      - required traits
      - bonus traits
      - frequency keywords
      - deal breakers
      - location preference (ZIP or keywords)
    """

    def __init__(self, models_dir_path: str):
        """
        Initializes the scorer by loading all models from the specified directory.

        Args:
            models_dir_path: Path to the directory containing resonance model JSON files.
        """
        self.models_dir = Path(models_dir_path)
        self.models: Dict[str, Dict] = {}
        self._load_all_models()

    def _load_all_models(self):
        """Loads all .json models from the models directory."""
        if not self.models_dir.is_dir():
            logger.error(f"Models directory not found or is not a directory: {self.models_dir}")
            return

        loaded_count = 0
        for file_path in self.models_dir.glob('*.json'):
            model_name = file_path.stem
            try:
                with open(file_path, "r", encoding='utf-8') as f:
                    model_data = json.load(f)
                    self.models[model_name] = model_data
                    loaded_count += 1
                    logger.debug(f"Loaded resonance model '{model_name}' from {file_path}")
            except json.JSONDecodeError as e:
                logger.error(f"Failed to decode JSON for model {file_path.name}: {e}")
            except Exception as e:
                logger.error(f"Failed to load model {file_path.name}: {e}")

        if loaded_count > 0:
            logger.info(f"Successfully loaded {loaded_count} resonance models from {self.models_dir}")
        else:
            logger.warning(f"No resonance models were loaded from {self.models_dir}")

    def score_profile(self, profile: Dict, model_name: str) -> Dict:
        """
        Given a profile dict, return a score (0.0–1.0) and match notes
        based on the specified resonance model.
        Profile must contain at minimum: 'bio', 'location'

        Args:
            profile: Dictionary representing the user profile.
            model_name: The name of the resonance model to use (e.g., 'romantic').

        Returns:
            Dict: Scoring results including 'score' and 'notes'.
        """
        # Get the specified model
        model = self.models.get(model_name)
        if not model:
            logger.error(f"Requested resonance model '{model_name}' not found.")
            return {"score": 0.0, "reason": f"Model '{model_name}' not loaded.", "notes": []}

        # Extract criteria from the selected model
        required_traits = [t.lower() for t in model.get("primary_traits_required", [])]
        bonus_traits = [t.lower() for t in model.get("bonus_traits", [])]
        deal_breakers = [t.lower() for t in model.get("deal_breakers", [])]
        keywords = [t.lower() for t in model.get("frequency_keywords", [])]
        loc_pref = model.get("location_priority", {})
        zip_code = loc_pref.get("zip", "").strip()
        location_keywords = [zip_code.lower()] + [kw.lower() for kw in loc_pref.get("keywords", ["houston", "htx"])]
        
        # --- Scoring Logic (using extracted criteria) ---
        bio = profile.get("bio", "").lower()
        location = profile.get("location", "").lower()

        # Early rejection via deal breakers
        for breaker in deal_breakers:
            if breaker in bio:
                return {"score": 0.0, "reason": f"Deal breaker: {breaker} (Model: {model_name})", "notes": []}

        score = 0
        notes = []

        # Required trait matches (high weight)
        matched_required = [t for t in required_traits if t in bio]
        score += len(matched_required) * 2
        if matched_required:
            notes.append(f"Required traits matched: {', '.join(matched_required)}")

        # Bonus trait matches
        matched_bonus = [t for t in bonus_traits if t in bio]
        score += len(matched_bonus)
        if matched_bonus:
            notes.append(f"Bonus traits: {', '.join(matched_bonus)}")

        # Frequency keyword matches
        matched_keywords = [k for k in keywords if k in bio]
        score += len(matched_keywords)
        if matched_keywords:
            notes.append(f"Frequency keywords matched: {', '.join(matched_keywords)}")

        # Location scoring
        if zip_code and zip_code in location:
            score += 3
            notes.append("Exact ZIP code match")
        elif any(k in location for k in location_keywords):
            score += 1
            notes.append("Location keyword match")

        # Normalize and return
        # Determine max possible score based on model weights (adjust if weights change)
        max_score = (len(required_traits) * 2) + len(bonus_traits) + len(keywords) + 3 
        normalized_score = min(score / max_score, 1.0) if max_score > 0 else 0.0
        
        return {
            "score": round(normalized_score, 2),
            "notes": notes,
            "model_used": model_name
        }
