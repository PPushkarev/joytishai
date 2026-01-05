import datetime
import os
from typing import Any, Dict, List
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

load_dotenv()


class MongoAILogger:
    def __init__(self):
        self.uri = os.getenv("MONGO_URI")
        self.client = AsyncIOMotorClient(self.uri)
        self.db = self.client.joytishai_db
        self.collection = self.db.ai_logs
        # МЫ УДАЛИЛИ TIKTOKEN ОТСЮДА 🗑️

    async def log_request(
            self,
            user_query: str,
            retrieved_docs: List[Dict[str, Any]],
            ai_response: Any,
            usage: Dict[str, int],
            model_name: str = "gpt-4o"
    ):
        # Берем данные напрямую из словаря usage, который пришел из OpenAI
        p_tokens = usage.get("prompt_tokens", 0)
        c_tokens = usage.get("completion_tokens", 0)

        # Рассчитываем стоимость (актуально для gpt-4o)
        cost = (p_tokens * 5.0 / 1_000_000) + (c_tokens * 15.0 / 1_000_000)

        log_entry = {
            "timestamp": datetime.datetime.utcnow(),
            "user_query": user_query,
            "context": retrieved_docs,
            "response": ai_response,
            "stats": {
                "tokens": usage,
                "cost_usd": cost,
                "model": model_name
            },
            "evaluation": {
                "faithfulness": None,
                "relevancy": None,
                "status": "pending"
            }
        }

        result = await self.collection.insert_one(log_entry)
        return result.inserted_id

    async def log_analytics(self, request, raw_data, final_res, raw_ai_obj):
        """Метод для интеграции с FastAPI"""
        try:
            docs = raw_data.get("relevant_texts", []) if isinstance(raw_data, dict) else []

            # Извлекаем usage из объекта OpenAI
            if raw_ai_obj and hasattr(raw_ai_obj, 'usage'):
                usage_data = {
                    "prompt_tokens": raw_ai_obj.usage.prompt_tokens,
                    "completion_tokens": raw_ai_obj.usage.completion_tokens,
                    "total_tokens": raw_ai_obj.usage.total_tokens
                }
            else:
                usage_data = {"total_tokens": 0}

            await self.log_request(
                user_query=str(request.chart_data),
                retrieved_docs=docs,
                ai_response=final_res,
                usage=usage_data
            )
        except Exception as e:
            print(f"Logging error: {e}")