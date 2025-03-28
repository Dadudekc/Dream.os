import json
import os
from typing import List, Dict


class ResonanceScorer:
    """
    Loads a resonance model (e.g. romantic.json, side_chick.json, etc.)
    and scores a given profile dict based on alignment with:
      - required traits
      - bonus traits
      - frequency keywords
      - deal breakers
      - location preference (ZIP or keywords)

    Designed for dynamic model switching via `load_model(path)`.
    """

    def __init__(self, model_path: str):
        self.model_path = model_path
        self.load_model(model_path)

    def load_model(self, model_path: str):
        """
        Loads a new resonance blueprint and reinitializes scoring attributes.
        """
        if not os.path.exists(model_path):
            raise FileNotFoundError(f"Resonance model not found: {model_path}")

        with open(model_path, "r") as f:
            self.model = json.load(f)

        self.model_path = model_path
        self.required_traits = [t.lower() for t in self.model.get("primary_traits_required", [])]
        self.bonus_traits = [t.lower() for t in self.model.get("bonus_traits", [])]
        self.deal_breakers = [t.lower() for t in self.model.get("deal_breakers", [])]
        self.keywords = [t.lower() for t in self.model.get("frequency_keywords", [])]

        loc_pref = self.model.get("location_priority", {})
        self.zip_code = loc_pref.get("zip", "").strip()
        self.location_keywords = [self.zip_code.lower()] + [
            kw.lower() for kw in loc_pref.get("keywords", ["houston", "htx"])
        ]

    def score_profile(self, profile: Dict) -> Dict:
        """
        Given a profile dict, return a score (0.0–1.0) and match notes.
        Profile must contain at minimum: 'bio', 'location'
        """
        bio = profile.get("bio", "").lower()
        location = profile.get("location", "").lower()

        # Early rejection via deal breakers
        for breaker in self.deal_breakers:
            if breaker in bio:
                return {"score": 0.0, "reason": f"Deal breaker: {breaker}"}

        score = 0
        notes = []

        # Required trait matches (high weight)
        matched_required = [t for t in self.required_traits if t in bio]
        score += len(matched_required) * 2
        if matched_required:
            notes.append(f"Required traits matched: {', '.join(matched_required)}")

        # Bonus trait matches
        matched_bonus = [t for t in self.bonus_traits if t in bio]
        score += len(matched_bonus)
        if matched_bonus:
            notes.append(f"Bonus traits: {', '.join(matched_bonus)}")

        # Frequency keyword matches
        matched_keywords = [k for k in self.keywords if k in bio]
        score += len(matched_keywords)
        if matched_keywords:
            notes.append(f"Frequency keywords matched: {', '.join(matched_keywords)}")

        # Location scoring
        if self.zip_code and self.zip_code in location:
            score += 3
            notes.append("Exact ZIP code match")
        elif any(k in location for k in self.location_keywords):
            score += 1
            notes.append("Location keyword match")

        # Normalize and return
        normalized_score = min(score / 15.0, 1.0)
        return {
            "score": round(normalized_score, 2),
            "notes": notes
        }