import json
import os
import re
from typing import List, Dict


class ResonanceScorer:
    """
    Loads a resonance model (e.g. romantic.json) and scores a given profile dict
    based on alignment with desired traits, bonus traits, and deal breakers.
    """

    def __init__(self, model_path: str):
        if not os.path.exists(model_path):
            raise FileNotFoundError(f"Resonance model not found: {model_path}")

        with open(model_path, "r") as f:
            self.model = json.load(f)

        # Normalize terms for matching
        self.required_traits = [t.lower() for t in self.model.get("primary_traits_required", [])]
        self.deal_breakers = [t.lower() for t in self.model.get("deal_breakers", [])]
        self.bonus_traits = [t.lower() for t in self.model.get("bonus_traits", [])]
        self.keywords = [t.lower() for t in self.model.get("frequency_keywords", [])]
        self.zip_code = self.model.get("location_priority", {}).get("zip", "").strip()
        self.location_keywords = [self.zip_code.lower()] + [
            kw.lower() for kw in self.model.get("location_priority", {}).get("keywords", ["houston", "htx"])
        ]

    def score_profile(self, profile: Dict) -> Dict:
        """
        Given a profile dictionary with keys like bio, location, etc,
        return a dictionary with a resonance score and match notes.
        """
        bio = profile.get("bio", "").lower()
        location = profile.get("location", "").lower()

        # Early reject if any deal breakers appear
        for breaker in self.deal_breakers:
            if breaker in bio:
                return {"score": 0.0, "reason": f"Deal breaker: {breaker}"}

        score = 0
        notes = []

        # Score required traits
        matched_traits = [trait for trait in self.required_traits if trait in bio]
        score += len(matched_traits) * 2
        if matched_traits:
            notes.append(f"Matched traits: {', '.join(matched_traits)}")

        # Score bonus traits
        matched_bonus = [trait for trait in self.bonus_traits if trait in bio]
        score += len(matched_bonus)
        if matched_bonus:
            notes.append(f"Bonus traits: {', '.join(matched_bonus)}")

        # Keyword vibe alignment
        matched_keywords = [kw for kw in self.keywords if kw in bio]
        score += len(matched_keywords)
        if matched_keywords:
            notes.append(f"Frequency keywords: {', '.join(matched_keywords)}")

        # Location boost
        if self.zip_code and self.zip_code in location:
            score += 3
            notes.append("Exact ZIP match")
        elif any(loc in location for loc in self.location_keywords):
            score += 1
            notes.append("Location keyword match")

        # Final normalization
        normalized_score = min(score / 15.0, 1.0)
        return {
            "score": round(normalized_score, 2),
            "notes": notes
        }