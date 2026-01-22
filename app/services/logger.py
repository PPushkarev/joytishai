import datetime
import os
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv
# framework for worKing with DB
from motor.motor_asyncio import AsyncIOMotorClient

load_dotenv()


# CREATE CLASS FOR WORKING WITH ATLAS DB FOR LOGGING PURPUSE


class MongoAILogger:
    def __init__(self):
        self.uri = os.getenv("MONGO_URI")
        self.client = AsyncIOMotorClient(self.uri)
        self.db = self.client.joytishai_db
        self.collection = self.db.ai_logs

    # Just counting how much we spent for users quires, what we found in Vector base, raw transit data , AI response for counting
    async def log_request(
        self,
        user_query: str,
        retrieved_docs: List[Dict[str, Any]],
        ai_response: Any,
        usage: Dict[str, int],
        formatted_input: Optional[str] = None,  # [OK] Новое поле
        model_name: str = "gpt-4o-mini",
    ):
        # How much we spent in OpenAI
        p_tokens = usage.get("prompt_tokens", 0)
        c_tokens = usage.get("completion_tokens", 0)

        # Cost of spent
        cost = (p_tokens * 0.15 / 1_000_000) + (c_tokens * 0.60 / 1_000_000)

        log_entry = {
            "timestamp": datetime.datetime.utcnow(),
            "user_query": user_query,
            "formatted_input": formatted_input,  # [OK] Сохраняем
            "context": retrieved_docs,
            "response": ai_response,
            "stats": {"tokens": usage, "cost_usd": cost, "model": model_name},
            "evaluation": {
                "faithfulness": None,
                "relevancy": None,
                "status": "pending",
            },
        }

        result = await self.collection.insert_one(log_entry)
        return result.inserted_id

    # AS a final we ge id record in DB

    # WE USING THIS FUNCTION TO GET INFORMATION FROM RESPONSE FAST API and get to async def log_request

    async def log_analytics(
            self, request, raw_data, final_res, raw_ai_obj, formatted_text=None
    ):
        """INTEGRATION WITH FastAPI"""

        try:
            docs = []

            # --- [FIX] УЛУЧШЕННЫЙ ПОИСК КОНТЕКСТА ---
            # 1. Если final_res — это словарь (dict)
            if isinstance(final_res, dict):
                docs = final_res.get("metadata_context") or final_res.get("context") or []

            # 2. Если final_res — это Pydantic объект
            elif hasattr(final_res, "metadata_context"):
                docs = final_res.metadata_context

            # 3. Если в ответе пусто, пробуем найти в raw_data (запасной вариант)
            if not docs and isinstance(raw_data, dict):
                docs = raw_data.get("relevant_texts", [])

            # Гарантируем, что docs — это список
            if docs is None:
                docs = []
            # ----------------------------------------

            # Извлекаем usage из объекта OpenAI
            if raw_ai_obj and hasattr(raw_ai_obj, "usage"):
                usage_data = {
                    "prompt_tokens": raw_ai_obj.usage.prompt_tokens,
                    "completion_tokens": raw_ai_obj.usage.completion_tokens,
                    "total_tokens": raw_ai_obj.usage.total_tokens,
                }
            else:
                usage_data = {"total_tokens": 0}

            # Мы передаем docs в retrieved_docs, а внутри log_request оно сохранится в поле "context"
            await self.log_request(
                user_query=str(request.chart_data),
                retrieved_docs=docs,
                ai_response=final_res,
                usage=usage_data,
                formatted_input=formatted_text,
            )

            # Полезный принт, чтобы видеть в консоли сервера, сохраняется ли контекст
            print(f"📝 [LOGGER] Logged request. Context items: {len(docs)}")

        except Exception as e:
            print(f"❌ Logging error: {e}")

    #  OLD VERSION
    # async def log_analytics(
    #     self, request, raw_data, final_res, raw_ai_obj, formatted_text=None
    # ):
    #     """INTEGRATION WHIT  FastAPI"""
    #
    #     try:
    #         docs = []
    #
    #         # 1. Пытаемся достать контекст из ответа AI (мы его туда прицепили в AIEngine)
    #         if hasattr(final_res, "metadata_context"):
    #             docs = final_res.metadata_context
    #         # 2. Если нет, пробуем из сырых данных (старый способ)
    #         elif isinstance(raw_data, dict):
    #             docs = raw_data.get("relevant_texts", [])
    #
    #         # Извлекаем usage из объекта OpenAI
    #         if raw_ai_obj and hasattr(raw_ai_obj, "usage"):
    #             usage_data = {
    #                 "prompt_tokens": raw_ai_obj.usage.prompt_tokens,
    #                 "completion_tokens": raw_ai_obj.usage.completion_tokens,
    #                 "total_tokens": raw_ai_obj.usage.total_tokens,
    #             }
    #         else:
    #             usage_data = {"total_tokens": 0}
    #
    #         await self.log_request(
    #             user_query=str(request.chart_data),
    #             retrieved_docs=docs,
    #             ai_response=final_res,
    #             usage=usage_data,  # <--- ЗАПЯТУЮ ДОБАВИЛ
    #             formatted_input=formatted_text,  # [OK] Передаем дальше
    #         )
    #     except Exception as e:
    #         print(f"Logging error: {e}")
