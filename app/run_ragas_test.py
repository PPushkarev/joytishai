import asyncio
import os
from dotenv import load_dotenv

# Подгружаем переменные окружения (.env)
load_dotenv()

# Импортируем нашу функцию оценки
from app.services.ragas_engine import execute_ragas_cycle
from ragas.llms import LangchainLLMWrapper
from ragas.embeddings import LangchainEmbeddingsWrapper

async def main():
    # Получаем ссылку на базу из .env
    mongo_uri = os.getenv("MONGO_URI")

    if not mongo_uri:
        print("❌ Ошибка: Не найден MONGO_DETAILS в .env файле!")
        return

    print("🏁 Начинаем тестовый прогон Ragas...")

    # Запускаем функцию
    result = await execute_ragas_cycle(mongo_uri)

    print("\n--- ИТОГИ ---")
    print(result)


if __name__ == "__main__":
    # Запускаем асинхронную функцию
    asyncio.run(main())