import json
import os
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from app.services.prompts import JYOTISH_SYSTEM_PROMPT
from app.services.validator import ResponseAuditor
from app.services.vector_store import VectorStoreManager
from app.schemas.consultation import AstrologicalConsultation

# Load environment variables (API Keys, etc.)
load_dotenv()


class AIEngine:
    """
    Main Orchestration Engine:
    Manages the flow between data analysis, RAG (Vector Search), and LLM generation.
    """

    def __init__(self):
        # 1. Get API Key
        api_key = os.getenv("OPENAI_API_KEY")

        # Check AI Key
        if not api_key:
            print("CRITICAL ERROR: OPENAI_API_KEY is not set in environment variables!")

        model_name = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        temp = float(os.getenv("AI_TEMPERATURE", 0.3))

        # 2. Initialize LLM
        self.llm = ChatOpenAI(
            model=model_name,
            temperature=temp,
            openai_api_key=api_key
        )

        self.vsm = VectorStoreManager()

    # --- [UPDATED] Helper function to format ALL data for AI and Logs ---
    def _format_planetary_facts(self, astro_data: dict) -> str:
        """
        Converts complex JSON into a clean, human-readable text list.
        It includes BOTH:
        1. Transit Scores (Calculated strength of houses).
        2. Natal Chart (Planetary positions).
        """
        try:
            # Normalize input (dict, json string, or pydantic)
            if hasattr(astro_data, 'dict'):
                data = astro_data.dict()
            elif isinstance(astro_data, str):
                data = json.loads(astro_data)
            else:
                data = astro_data

            lines = []

            # --- SECTION 1: TRANSIT SCORES (The Math) ---
            # Extract summary scores (the core of the forecast)
            scores = data.get("summary_scores")
            if scores:
                lines.append("=== 📊 DAILY TRANSIT SCORES (CALCULATED) ===")
                # Sort scores from Weakest to Strongest for clarity
                sorted_scores = sorted(scores.items(), key=lambda item: item[1])
                for house, score in sorted_scores:
                    lines.append(f"- House {house}: {score} points")
                lines.append("")  # Empty line for separation

            # --- SECTION 2: NATAL CHART (The Context) ---
            # Search for planets in root or inside chart_data
            planets = data.get("planets") or data.get("chart_data", {}).get("planets", {})

            if planets:
                lines.append("=== 👤 NATAL CHART (USER CONTEXT) ===")
                for name, details in planets.items():
                    # Safely extract attributes (handle dict vs object)
                    house = details.get('house') if isinstance(details, dict) else getattr(details, 'house', '?')
                    sign = details.get('sign') if isinstance(details, dict) else getattr(details, 'sign', '?')
                    lines.append(f"- {name}: House {house}, Sign {sign}")

            if not lines:
                return "No scores or planetary data found."

            return "\n".join(lines)

        except Exception as e:
            return f"Error formatting data: {str(e)}"

    async def generate_consultation(self, astro_data: dict) -> AstrologicalConsultation:
        """
        Executes the full cycle of astrological consultation generation.
        """

        # --- [STEP 1] Generate "Clean Text" containing Scores + Planets ---
        clean_facts = self._format_planetary_facts(astro_data)

        # 1. IDENTIFY KEY POINTS (Strength and Weakness)
        scores = astro_data.get("summary_scores", {})
        weakest_house = min(scores, key=scores.get) if scores else "general balance"
        strongest_house = max(scores, key=scores.get) if scores else "general balance"

        # 2. RAG RETRIEVAL (Context Search)
        retriever = self.vsm.get_retriever()
        retriever.search_kwargs = {"k": 6}

        query = f"Remedies for {weakest_house} AND benefits of {strongest_house}"
        docs = await retriever.ainvoke(query)
        context = "\n\n".join([d.page_content for d in docs])

        # 3. PROMPT PREPARATION
        prompt_template = ChatPromptTemplate.from_messages([
            ("system", JYOTISH_SYSTEM_PROMPT),
            # --- [STEP 2] Inject the comprehensive formatted facts into the prompt ---
            ("user", "CRITICAL DATA FOR ANALYSIS (TRUST THESE):\n{formatted_facts}\n\nRaw JSON Data: {astro_data}")
        ])

        # 4. OUTPUT CONFIGURATION
        structured_llm = self.llm.with_structured_output(AstrologicalConsultation)
        chain = prompt_template | structured_llm

        # 5. EXECUTION
        response = await chain.ainvoke({
            "context": context,
            # --- [STEP 3] Pass our variable ---
            "formatted_facts": clean_facts,
            "astro_data": json.dumps(astro_data, ensure_ascii=False),
            "top_tension": weakest_house,
            "super_power": strongest_house
        })

        # 6. Audit (Logic validation)
        audit_results = ResponseAuditor.validate_consultation(astro_data, response)
        if not audit_results["is_valid"]:
            print(f"⚠️ AI Audit Warning: {audit_results['warnings']}")

        # --- [STEP 4] Attach the Full Text to the response object ---
        # This ensures main.py can extract it and save it to the database for the Dashboard
        response.metadata_context = [d.page_content for d in docs]
        response.debug_formatted_input = clean_facts

        return response