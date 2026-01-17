import json
import os
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from app.services.prompts import JYOTISH_SYSTEM_PROMPT
from app.services.validator import ResponseAuditor
from app.services.vector_store import VectorStoreManager
from app.schemas.consultation import AstrologicalConsultation

# Load environment variables
load_dotenv()

class AIEngine:
    """
    Main Orchestration Engine.
    """

    def __init__(self):
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            print("CRITICAL ERROR: OPENAI_API_KEY is not set!")

        model_name = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        temp = float(os.getenv("AI_TEMPERATURE", 0.3))

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

        # 1. ГОТОВИМ ДАННЫЕ: БЕРЕМ ВСЁ КАК ЕСТЬ (RAW JSON)
        # Мы просто превращаем весь словарь с данными в строку JSON.
        # indent=2 нужен, чтобы в Дашборде это выглядело читаемо, а не одной строкой.
        # ensure_ascii=False позволит видеть русские буквы нормально.
        full_json_dump = json.dumps(astro_data, indent=2, ensure_ascii=False)

        # 2. Key Points Analysis (оставляем для RAG)
        scores = astro_data.get("summary_scores", {})
        weakest_house = min(scores, key=scores.get) if scores else "general balance"
        strongest_house = max(scores, key=scores.get) if scores else "general balance"

        # 3. RAG RETRIEVAL
        retriever = self.vsm.get_retriever()
        retriever.search_kwargs = {"k": 6}
        query = f"Remedies for {weakest_house} AND benefits of {strongest_house}"
        docs = await retriever.ainvoke(query)
        context = "\n\n".join([d.page_content for d in docs])

        # 4. PROMPT PREPARATION
        # Убираем лишние фильтры. Скармливаем ИИ полный JSON.
        prompt_template = ChatPromptTemplate.from_messages([
            ("system", JYOTISH_SYSTEM_PROMPT),
            ("user", "HERE IS THE FULL CALCULATION DATA (ANALYSIS SOURCE):\n{full_data_json}")
        ])

        structured_llm = self.llm.with_structured_output(AstrologicalConsultation)
        chain = prompt_template | structured_llm

        # 5. EXECUTION
        response = await chain.ainvoke({
            "context": context,
            # Передаем полный дамп в промпт
            "full_data_json": full_json_dump,
            "astro_data": full_json_dump, # (дублируем для совместимости, если где-то используется)
            "top_tension": weakest_house,
            "super_power": strongest_house
        })

        # 6. Audit
        audit_results = ResponseAuditor.validate_consultation(astro_data, response)
        if not audit_results["is_valid"]:
            print(f"⚠️ AI Audit Warning: {audit_results['warnings']}")

        # 7. СОХРАНЯЕМ ПОЛНЫЙ ДАМП В ОТВЕТ (ДЛЯ ЛОГГЕРА)
        # Теперь main.py заберет этот полный JSON и сохранит в базу
        response.metadata_context = [d.page_content for d in docs]
        response.debug_formatted_input = full_json_dump

        return response