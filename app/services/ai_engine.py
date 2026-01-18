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

        # 1. ГОТОВИМ ДАННЫЕ
        full_json_dump = json.dumps(astro_data, indent=2, ensure_ascii=False)

        # --- [НАЧАЛО ИЗМЕНЕНИЙ] ---
        # 2. Key Points Analysis (Находим ВСЕ дома с мин/макс баллами)

        # 1. Достаем баллы из правильного места (derived_tables или summary_scores)
        raw_scores = astro_data.get("derived_tables", {}).get("houses", {}).get("scores", {})
        if not raw_scores:
            raw_scores = astro_data.get("summary_scores", {})

        # 2. Приводим к простому виду: {'1': -3, '2': 2}
        scores = {}
        for h, data in raw_scores.items():
            val = data.get("total_score") if isinstance(data, dict) else data
            if val is not None:
                scores[h] = val

        # 3. Находим списки домов
        if scores:
            min_val = min(scores.values())
            max_val = max(scores.values())

            # Собираем список всех домов, у которых этот балл (например: "House 1, House 10")
            weak_list = [f"House {h}" for h, s in scores.items() if s == min_val]
            strong_list = [f"House {h}" for h, s in scores.items() if s == max_val]

            weakest_house = ", ".join(weak_list)
            strongest_house = ", ".join(strong_list)
        else:
            weakest_house = "general balance"
            strongest_house = "general balance"
        # --- [КОНЕЦ ИЗМЕНЕНИЙ] ---




        # # 3. RAG RETRIEVAL
        # retriever = self.vsm.get_retriever()
        # retriever.search_kwargs = {"k": 6}
        # query = f"Remedies for {weakest_house} AND benefits of {strongest_house}"
        # docs = await retriever.ainvoke(query)
        # context = "\n\n".join([d.page_content for d in docs])

        # 3. RAG RETRIEVAL (С ЗАЩИТОЙ ОТ ОШИБОК)
        # Инициализируем переменную ЗАРАНЕЕ, чтобы избежать UnboundLocalError
        context = ""

        try:
            retriever = self.vsm.get_retriever()
            retriever.search_kwargs = {"k": 6}

            # Формируем запрос
            query = (
                f"Vedic remedies, Mantras, Gemstones and specific Upayas for weak {weakest_house}. "
                f"Positive effects and how to strengthen {strongest_house}."
            )

            print(f"🔎 DEBUG: RAG Query: {query}")

            # Пытаемся найти документы
            docs = await retriever.ainvoke(query)

            if docs:
                print(f"✅ DEBUG: Найдено документов: {len(docs)}")
                context = "\n\n".join([d.page_content for d in docs])
            else:
                print("⚠️ DEBUG: RAG вернул пустой список (документы не найдены).")
                context = "No specific remedies found in knowledge base."

        except Exception as e:
            # Если база упала (нет соединения, ошибка FAISS и т.д.), мы не крашим всё приложение
            print(f"🚨 RAG ERROR (Игнорируем и идем дальше): {e}")
            context = "Knowledge base temporarily unavailable."


        # 4. PROMPT PREPARATION
        # Мы добавляем жесткую инструкцию для поля 'recommendations'
        prompt_template = ChatPromptTemplate.from_messages([
            ("system", JYOTISH_SYSTEM_PROMPT),
            ("user", """
                CONTEXT (RAG):
                {context}

                USER DATA:
                {full_data_json}

                VARIABLES:
                - Strongest House: {super_power}
                - Weakest House: {top_tension}

                Generate JSON response now.
                """)
        ])

        structured_llm = self.llm.with_structured_output(AstrologicalConsultation)
        chain = prompt_template | structured_llm

        # 5. EXECUTION
        response = await chain.ainvoke({
            "context": context,
            # Передаем полный дамп в промпт
            "full_data_json": full_json_dump,
            "astro_data": full_json_dump,
            "top_tension": weakest_house,
            "super_power": strongest_house
        })

        # 6. Audit
        audit_results = ResponseAuditor.validate_consultation(astro_data, response)
        if not audit_results["is_valid"]:
            print(f"⚠️ AI Audit Warning: {audit_results['warnings']}")

        # 7. СОХРАНЯЕМ ПОЛНЫЙ ДАМП В ОТВЕТ
        response.metadata_context = [d.page_content for d in docs]
        response.debug_formatted_input = full_json_dump

        return response



    # старая функция работала
    # async def generate_consultation(self, astro_data: dict) -> AstrologicalConsultation:
    #     """
    #     Executes the full cycle of astrological consultation generation.
    #     """
    #
    #
    #     full_json_dump = json.dumps(astro_data, indent=2, ensure_ascii=False)
    #
    #     # 2. Key Points Analysis (оставляем для RAG)
    #     scores = astro_data.get("summary_scores", {})
    #     weakest_house = min(scores, key=scores.get) if scores else "general balance"
    #     strongest_house = max(scores, key=scores.get) if scores else "general balance"
    #
    #
    #
    #
    #     # 3. RAG RETRIEVAL
    #     retriever = self.vsm.get_retriever()
    #     retriever.search_kwargs = {"k": 6}
    #     query = f"Remedies for {weakest_house} AND benefits of {strongest_house}"
    #     docs = await retriever.ainvoke(query)
    #     context = "\n\n".join([d.page_content for d in docs])
    #
    #     # 4. PROMPT PREPARATION
    #     # Убираем лишние фильтры. Скармливаем ИИ полный JSON.
    #     prompt_template = ChatPromptTemplate.from_messages([
    #         ("system", JYOTISH_SYSTEM_PROMPT),
    #         ("user", "HERE IS THE FULL CALCULATION DATA (ANALYSIS SOURCE):\n{full_data_json}")
    #     ])
    #
    #     structured_llm = self.llm.with_structured_output(AstrologicalConsultation)
    #     chain = prompt_template | structured_llm
    #
    #     # 5. EXECUTION
    #     response = await chain.ainvoke({
    #         "context": context,
    #         # Передаем полный дамп в промпт
    #         "full_data_json": full_json_dump,
    #         "astro_data": full_json_dump, # (дублируем для совместимости, если где-то используется)
    #         "top_tension": weakest_house,
    #         "super_power": strongest_house
    #     })
    #
    #     # 6. Audit
    #     audit_results = ResponseAuditor.validate_consultation(astro_data, response)
    #     if not audit_results["is_valid"]:
    #         print(f"⚠️ AI Audit Warning: {audit_results['warnings']}")
    #
    #     # 7. СОХРАНЯЕМ ПОЛНЫЙ ДАМП В ОТВЕТ (ДЛЯ ЛОГГЕРА)
    #     # Теперь main.py заберет этот полный JSON и сохранит в базу
    #     response.metadata_context = [d.page_content for d in docs]
    #     response.debug_formatted_input = full_json_dump
    #
    #     return response