import logging
import pandas as pd
from motor.motor_asyncio import AsyncIOMotorClient
from datasets import Dataset
from langchain_openai import ChatOpenAI, OpenAIEmbeddings

# Метрики Ragas
from ragas import evaluate
from ragas.metrics import faithfulness, answer_relevancy, context_precision
from ragas.llms import LangchainLLMWrapper
from ragas.embeddings import LangchainEmbeddingsWrapper

logger = logging.getLogger(__name__)


# --- ГЛОБАЛЬНАЯ ИНИЦИАЛИЗАЦИЯ (для доступа из тестов и Allure) ---
_llm = ChatOpenAI(model="gpt-4o", temperature=0)
_emb = OpenAIEmbeddings(model="text-embedding-3-small")

judge_llm = LangchainLLMWrapper(_llm)
judge_embeddings = LangchainEmbeddingsWrapper(_emb)

# Привязываем судью к метрикам сразу при импорте модуля
for m in [faithfulness, answer_relevancy, context_precision]:
    m.llm = judge_llm
    if hasattr(m, 'embeddings'):
        m.embeddings = judge_embeddings


async def prepare_ragas_datasets(mongo_uri: str):
    client = AsyncIOMotorClient(mongo_uri)
    db = client.joytishai_db
    collection = db.ai_logs


    # Берем записи, ожидающие оценки (limit 5 для теста)
    cursor = collection.find({"evaluation.status": "pending"}).limit(5)
    logs = await cursor.to_list(length=5)

    if not logs:
        return None, None, None, collection

    data_tech = {"question": [], "answer": [], "contexts": [], "reference": []}
    data_knowledge = {"question": [], "answer": [], "contexts": [], "reference": []}

    # ВАШ ИДЕАЛЬНЫЙ ЭТАЛОН
    reference_text = (
        "Сегодня Луна находится в седьмом доме, что приносит позитивные эмоции и поддержку в партнерских отношениях. "
        "Транзитные планеты, такие как Юпитер, также аспектируют Луну, что усиливает удачу и возможности в общении и взаимодействии с окружающими. "
        "В то же время, Солнце, Марс и Меркурий находятся в шестом доме, что может указывать на трудности в службе и здоровье, требующие внимания. "
        "Сильные дома: Четвертый дом, связанный с комфортом, и Девятый дом — удача. "
        "Слабые дома: Пятый дом (творчество) и Восьмой дом (кризисы). "
        "Мудрость: Пятый и девятый дома представляют милость и удачу – хорошую карму. "
        "Девятый дом связан с удачей особым образом (лотереи, везение). "
        "Рекомендации: Обратитесь к семейным ценностям (4) и духовным практикам (9), чтобы преодолеть трудности в творчестве (5) и трансформациях (8)."
    )

    for log in logs:
        user_query = str(log.get("user_query", ""))
        response_obj = log.get("response", {})
        answer = response_obj.get("astrological_analysis", "") if isinstance(response_obj, dict) else str(response_obj)

        # 🪐 Технический датасет
        data_tech["question"].append(user_query)
        data_tech["answer"].append(answer)
        data_tech["contexts"].append([user_query])
        data_tech["reference"].append(user_query)

        # 📚 Контентный датасет (RAG)
        data_knowledge["question"].append(user_query)
        data_knowledge["answer"].append(answer)

        # Получаем реальный контекст из лога
        raw_context = log.get("context", [])
        cleaned_context = [
            item.get("page_content") if isinstance(item, dict) else str(item)
            for item in raw_context
        ]

        # Если контекст пуст, Ragas выдаст 0. Для теста можно добавить фейк,
        # но для жизни оставляем реальный из БД:
        data_knowledge["contexts"].append(cleaned_context if cleaned_context else ["Пустой контекст"])
        data_knowledge["reference"].append(reference_text)

    return Dataset.from_dict(data_tech), Dataset.from_dict(data_knowledge), logs, collection


async def execute_ragas_cycle(mongo_uri: str):
    logger.info("👨‍⚖️ [RAGAS] Запуск финального аудита (RU адаптирован)...")

    ds_tech, ds_knowledge, logs, collection = await prepare_ragas_datasets(mongo_uri)

    if not ds_tech:
        return {"status": "idle"}

    try:
        # Инициализация ИИ-судьи
        llm = ChatOpenAI(model="gpt-4o", temperature=0)
        embeddings = OpenAIEmbeddings(model="text-embedding-3-small")

        judge_llm = LangchainLLMWrapper(llm)
        judge_emb = LangchainEmbeddingsWrapper(embeddings)

        # Настройка метрик (привязываем LLM к каждой)
        metrics = [faithfulness, answer_relevancy, context_precision]
        for m in metrics:
            m.llm = judge_llm
            if hasattr(m, 'embeddings'):
                m.embeddings = judge_emb

        # 1. Техническая оценка
        results_tech = evaluate(dataset=ds_tech, metrics=[faithfulness], llm=judge_llm,
                                embeddings=judge_emb).to_pandas()

        # 2. Контентная оценка
        results_know = evaluate(dataset=ds_knowledge, metrics=metrics, llm=judge_llm, embeddings=judge_emb).to_pandas()

        # 3. Сохранение
        for i, log in enumerate(logs):
            res_t = results_tech.iloc[i]
            res_k = results_know.iloc[i]

            await collection.update_one(
                {"_id": log["_id"]},
                {"$set": {
                    "evaluation.technical_faithfulness": float(res_t.get("faithfulness", 0)),
                    "evaluation.knowledge_faithfulness": float(res_k.get("faithfulness", 0)),
                    "evaluation.relevancy": float(res_k.get("answer_relevancy", 0)),
                    "evaluation.context_precision": float(res_k.get("context_precision", 0)),
                    "evaluation.status": "evaluated",
                    "evaluation.engine": "ragas_ru_v2"
                }}
            )

        return {"status": "success", "processed": len(logs)}

    except Exception as e:
        logger.error(f"❌ Критическая ошибка Ragas: {e}")
        return {"status": "error", "message": str(e)}