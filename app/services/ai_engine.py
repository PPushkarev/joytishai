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

# STEP TWO  MAKE A CONSULTATION FROM AI



class AIEngine:
    """
    Main Orchestration Engine:
    Manages the flow between data analysis, RAG (Vector Search), and LLM generation.
    """

    def __init__(self):
        # 1. get key
        api_key = os.getenv("OPENAI_API_KEY")

        # checking AI key
        if not api_key:
            print("CRITICAL ERROR: OPENAI_API_KEY is not set in environment variables!")


        model_name = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        temp = float(os.getenv("AI_TEMPERATURE", 0.3))

        # 2. transfer OPEN AI key
        self.llm = ChatOpenAI(
            model=model_name,
            temperature=temp,
            openai_api_key=api_key
        )

        self.vsm = VectorStoreManager()

    async def generate_consultation(self, astro_data: dict) -> AstrologicalConsultation:
        """
        Executes the full cycle of astrological consultation generation.
        """

        # 1. IDENTIFY KEY POINTS (Strength and Weakness)
        # Extract scores from the data (assuming they are in "summary_scores")
        scores = astro_data.get("summary_scores", {})

        # Identify the weakest house (maximum negative score)
        weakest_house = min(scores, key=scores.get) if scores else "general balance"

        # Identify the strongest house (maximum positive score)
        strongest_house = max(scores, key=scores.get) if scores else "general balance"

        # 2. RAG RETRIEVAL (Context Search)
        retriever = self.vsm.get_retriever()
        retriever.search_kwargs = {"k": 6}

        # Formulate a query focusing on the weak zone and strong house

        query = f"Remedies for {weakest_house} AND benefits of {strongest_house}"
        docs = await retriever.ainvoke(query)
        context = "\n\n".join([d.page_content for d in docs])

        # 3. PROMPT PREPARATION
        prompt_template = ChatPromptTemplate.from_messages([
            ("system", JYOTISH_SYSTEM_PROMPT),
            ("user", "User planetary scores: {astro_data}")
        ])

        # 4. OUTPUT CONFIGURATION
        structured_llm = self.llm.with_structured_output(AstrologicalConsultation)
        chain = prompt_template | structured_llm



        # 5. EXECUTION
        # Passing weakest_house as top_tension for primary focus
        response = await chain.ainvoke({
            "context": context,
            "astro_data": json.dumps(astro_data, ensure_ascii=False),
            "top_tension": weakest_house,
            "super_power": strongest_house
        })

        # 6 Audit (Logic validation)
        audit_results = ResponseAuditor.validate_consultation(astro_data, response)
        if not audit_results["is_valid"]:
            print(f"⚠️ AI Audit Warning: {audit_results['warnings']}")

        response.metadata_context = [d.page_content for d in docs]
        return response

