# MAKE A SHEME OF CONSULTATION

from typing import List, Optional

from pydantic import BaseModel, Field


class AstrologicalConsultation(BaseModel):
    """
    Structured response schema for the Jyotish AI engine.
    Focuses on: Title, Analysis, and RAG-based Classic Wisdom.
    """

    # 1. Positive title of the Day
    daily_title: str = Field(
        description="A short and impactful title focusing on a positive action for the day."
    )

    # 2. Current transit houses situation
    astrological_analysis: str = Field(
        description="Detailed explanation of current planetary transits, identifying the strongest and weakest houses based on calculated scores."
    )

    # 3. Quote from PDF
    classic_wisdom: str = Field(
        description="A relevant quote or deep insight from the provided PDF context (RAG) that supports the analysis."
    )

    # 4. Recommendations
    recommendations: List[str] = Field(
        description="A list of several specific, actionable recommendations for the user."
    )

    debug_formatted_input: Optional[str] = Field(
        None, description="Technical field for logs"
    )

    # Technical field to store RAG context for logging and evaluation
    # It won't be visible to the user if you don't include it in the final UI
    metadata_context: Optional[List[str]] = Field(
        default=None,
        description="Technical field to store retrieved context docs for auditing",
    )
