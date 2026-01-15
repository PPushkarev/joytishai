import logging
from app.schemas.consultation import AstrologicalConsultation
# Setup logging to track audit results in the console
logger = logging.getLogger(__name__)



# CHEKING ANWERS TO OUR PATTER AND GET SCORE

class ResponseAuditor:
    """
    Validates AI-generated consultation against the mathematical truth
    from the Astro Engine and the defined Pydantic schema.
    """

    @staticmethod
    def validate_consultation(astro_data: dict, ai_response: AstrologicalConsultation) -> dict:
        results = {
            "is_valid": True,
            "warnings": [],
            "audit_score": 100
        }

        # --- 1. HOUSE STRENGTH CONSISTENCY CHECK ---
        # Get the summary scores to identify real strong/weak spots
        summary_scores = astro_data.get("summary_scores", {})

        if summary_scores:
            worst_score = min(summary_scores.values())
            # best_score = max(summary_scores.values())

            analysis_lower = ai_response.astrological_analysis.lower()

            # Check: If a house is critically weak (e.g., < -4),
            # ensure AI doesn't describe the general situation as "perfect"
            if worst_score <= -4:
                positive_keywords = ["perfect", "ideal", "flawless", "no risks"]
                if any(word in analysis_lower for word in positive_keywords):
                    results["warnings"].append(
                        "Tone Mismatch: Critical weakness detected, but AI tone is overly optimistic.")
                    results["audit_score"] -= 30

        # --- 2. RECOMMENDATIONS STRUCTURE CHECK ---
        # Ensure that recommendations is a list with at least 2 items
        if not isinstance(ai_response.recommendations, list) or len(ai_response.recommendations) < 1:
            results["is_valid"] = False
            results["warnings"].append("Structure Error: Recommendations must be a list of at least 1 items.")
            results["audit_score"] -= 40

        # --- 3. RAG CONTEXT CHECK ---
        if len(ai_response.classic_wisdom) < 30:
            results["warnings"].append("Content Warning: Classical wisdom field is too short or generic.")
            results["audit_score"] -= 20

        # Final validity check
        if results["audit_score"] < 50:
            results["is_valid"] = False

        if not results["is_valid"]:
            logger.error(f"❌ AUDIT FAILED | Score: {results['audit_score']} | Reasons: {results['warnings']}")

        return results