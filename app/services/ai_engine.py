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

    # --- [НОВОЕ] Вспомогательная функция для превращения JSON в текст ---
    def _format_planetary_facts(self, astro_data: dict) -> str:
        """
        Превращает сложный JSON в простой список фактов для ИИ.
        Пример: "- Луна: Дом 6, Знак Козерог"
        """
        try:
            # Нормализация входных данных (dict или json string)
            if hasattr(astro_data, 'dict'):
                data = astro_data.dict()
            elif isinstance(astro_data, str):
                data = json.loads(astro_data)
            else:
                data = astro_data

            # Ищем планеты (структура может быть вложенной)
            # Сначала ищем в корне, потом в chart_data
            planets = data.get("planets") or data.get("chart_data", {}).get("planets", {})

            if not planets: return "No planetary data found."

            facts = []
            for name, details in planets.items():
                # Безопасно достаем значения, даже если details это объект
                house = details.get('house') if isinstance(details, dict) else getattr(details, 'house', '?')
                sign = details.get('sign') if isinstance(details, dict) else getattr(details, 'sign', '?')
                facts.append(f"- {name}: House {house}, Sign {sign}")

            return "\n".join(facts)
        except Exception as e:
            return f"Error formatting data: {str(e)}"

    async def generate_consultation(self, astro_data: dict) -> AstrologicalConsultation:
        """
        Executes the full cycle of astrological consultation generation.
        """

        # --- [НОВОЕ] 1. Генерируем "Чистый Текст" для ИИ ---
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
            # --- [НОВОЕ] Передаем formatted_facts в промпт ---
            ("user", "PLANETARY FACTS (TRUST THESE):\n{formatted_facts}\n\nFull Planetary Scores: {astro_data}")
        ])

        # 4. OUTPUT CONFIGURATION
        structured_llm = self.llm.with_structured_output(AstrologicalConsultation)
        chain = prompt_template | structured_llm

        # 5. EXECUTION
        response = await chain.ainvoke({
            "context": context,
            # --- [НОВОЕ] Передаем нашу переменную ---
            "formatted_facts": clean_facts,
            "astro_data": json.dumps(astro_data, ensure_ascii=False),
            "top_tension": weakest_house,
            "super_power": strongest_house
        })

        # 6 Audit (Logic validation)
        audit_results = ResponseAuditor.validate_consultation(astro_data, response)
        if not audit_results["is_valid"]:
            print(f"⚠️ AI Audit Warning: {audit_results['warnings']}")

        # --- [НОВОЕ] Прикрепляем текст к ответу, чтобы main.py мог его сохранить ---
        response.metadata_context = [d.page_content for d in docs]
        response.debug_formatted_input = clean_facts

        return response