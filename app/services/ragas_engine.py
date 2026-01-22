import logging
import os
from motor.motor_asyncio import AsyncIOMotorClient
from datasets import Dataset
from ragas import evaluate
from ragas.metrics import faithfulness, answer_relevancy, context_precision
from langchain_openai import ChatOpenAI, OpenAIEmbeddings # <--- ЭТО ВАЖНО
from ragas import evaluate
from ragas.metrics import faithfulness, answer_relevancy, context_precision
from ragas.llms import LangchainLLMWrapper
from ragas.embeddings import LangchainEmbeddingsWrapper

# Настройка логгера
logger = logging.getLogger(__name__)


async def prepare_ragas_dataset(mongo_uri: str):
    """
    БЛОК 1: Подготовка данных
    Достаем логи со статусом 'pending', чистим контекст и формируем Dataset.
    """
    client = AsyncIOMotorClient(mongo_uri)
    db = client.joytishai_db
    collection = db.ai_logs

    # 1. Берем 5 старых логов, которые еще не проверены
    cursor = collection.find({"evaluation.status": "pending"}).limit(5)
    logs = await cursor.to_list(length=5)

    if not logs:
        return None, None, collection

    # 2. Создаем структуру для Ragas
    ragas_data = {
        "question": [],
        "answer": [],
        "contexts": [],
        "ground_truth": []
    }

    # 3. Заполняем списки данными
    for log in logs:
        # --- Вопрос ---
        ragas_data["question"].append(str(log.get("user_query", "")))

        # --- Ответ AI ---
        response_obj = log.get("response", {})
        if isinstance(response_obj, dict):
            ans_text = response_obj.get("astrological_analysis", "")
        else:
            ans_text = str(response_obj)
        ragas_data["answer"].append(ans_text)

        # --- Контекст (Очистка) ---
        raw_context = log.get("context", [])


        print(f"🐛 RAW CONTEXT ID {log['_id']}: {raw_context}")

        cleaned_context = []

        # 👇 ДОБАВЬ ЭТИ СТРОКИ ДЛЯ ОТЛАДКИ 👇
        print(f"\n📦 --- DEBUG ID: {log['_id']} ---")
        print(f"🔑 Ключи в записи: {list(log.keys())}")
        print(f"📄 Содержимое поля 'context': {log.get('context')}")
        print(f"📄 Содержимое поля 'metadata_context': {log.get('metadata_context')}")
        print("-----------------------------------\n")


        for item in raw_context:
            if isinstance(item, str):
                cleaned_context.append(item)
            elif isinstance(item, dict):
                # Ищем текст внутри объекта (page_content или text)
                text = item.get("page_content") or item.get("text") or str(item)
                cleaned_context.append(text)
            else:
                cleaned_context.append(str(item))

        ragas_data["contexts"].append(cleaned_context)

        # Ground Truth (заглушка)
        ragas_data["ground_truth"].append("nan")

    # 4. Создаем Dataset
    dataset = Dataset.from_dict(ragas_data)
    logger.info(f"📊 Подготовлен Dataset из {len(logs)} записей")

    return dataset, logs, collection







async def execute_ragas_cycle(mongo_uri: str):
    """
    БЛОК 2: Ядро оценки (Evaluation Engine)
    Запускает Ragas и сохраняет результаты в MongoDB.
    """
    logger.info("👨‍⚖️ [RAGAS ENGINE] Запуск цикла оценки...")

    # 1. Готовим данные
    dataset, logs, collection = await prepare_ragas_dataset(mongo_uri)

    if not dataset:
        logger.info("💤 Нет логов для проверки (status='pending').")
        return {"status": "idle", "processed": 0}

    # 2. Метрики для судьи
    active_metrics = [
        faithfulness,  # Не врет ли?
        answer_relevancy,  # По теме ли?
        context_precision  # Качественный ли поиск?
    ]

    try:
        logger.info(f"⏳ Передаем {len(logs)} записей судье Ragas...")

        # --- НАСТРОЙКА СУДЬИ ---
        # 1. Модель для оценки (LLM)
        # Используем gpt-4o для точности или gpt-4o-mini для экономии
        # --- НАСТРОЙКА СУДЬИ ---

        # 1. Создаем ChatOpenAI и оборачиваем его для Ragas
        judge_llm = LangchainLLMWrapper(ChatOpenAI(model="gpt-4o", temperature=0))

        # 2. Создаем OpenAIEmbeddings и тоже оборачиваем
        judge_embeddings = LangchainEmbeddingsWrapper(OpenAIEmbeddings(model="text-embedding-3-small"))



        print("\n🔍 --- ПРОВЕРКА ДАННЫХ ДЛЯ RAGAS ---")
        print(f"Вопрос: {dataset['question'][0]}")
        print(f"Контекст (что нашли): {dataset['contexts'][0]}")
        print(f"Ответ (что проверяем): {dataset['answer'][0]}")
        print("---------------------------------------\n")


        # 3. МАГИЯ RAGAS 🚀
        results = evaluate(
            dataset=dataset,
            metrics=active_metrics,
            llm=judge_llm,  # <--- Передаем явно
            embeddings=judge_embeddings  # <--- Передаем явно
        )





        # 4. Сохранение результатов
        df = results.to_pandas()
        count = 0

        for i, log in enumerate(logs):
            scores = df.iloc[i]

            await collection.update_one(
                {"_id": log["_id"]},
                {
                    "$set": {
                        "evaluation.faithfulness": float(scores.get("faithfulness", 0)),
                        "evaluation.relevancy": float(scores.get("answer_relevancy", 0)),
                        "evaluation.context_precision": float(scores.get("context_precision", 0)),
                        "evaluation.status": "evaluated",
                        "evaluation.engine": "ragas_professional"
                    }
                }
            )
            count += 1
            print(f"✅ Ragas ID: {log['_id']} | Faith: {scores.get('faithfulness'):.2f}")

        return {"status": "success", "processed": count}

    except Exception as e:
        logger.error(f"❌ Ошибка внутри Ragas: {e}")
        # Маркируем ошибку в базе, чтобы не зацикливаться
        if logs:
            ids = [log["_id"] for log in logs]
            await collection.update_many(
                {"_id": {"$in": ids}},
                {"$set": {"evaluation.status": "error", "evaluation.error_msg": str(e)}}
            )
        return {"status": "error", "message": str(e)}