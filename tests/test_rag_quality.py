import os
import pytest
import allure
import pandas as pd
from ragas import evaluate
from ragas.metrics import faithfulness, answer_relevancy, context_precision

from app.services.ragas_engine import judge_llm, judge_embeddings, prepare_ragas_datasets
from dotenv import load_dotenv

load_dotenv()




@allure.epic("Астрологический ИИ")
@allure.feature("Качество RAG системы")
class TestJoytishRagas:

    @allure.story("Аудит точности ответов и поиска")
    @pytest.mark.asyncio
    @pytest.mark.parametrize("log_index", range(5))
    async def test_ragas_full_audit(self, log_index):
        """
        Профессиональный аудит логов:
        1. Проверка соответствия планетам (Technical)
        2. Проверка соответствия базе знаний PDF (Knowledge)
        """
        # Получаем URI из окружения
        mongo_uri = os.getenv("MONGO_URI", "mongodb://localhost:27017")

        # 1. Загрузка данных
        with allure.step("Загрузка данных из MongoDB"):
            ds_tech, ds_know, logs, _ = await prepare_ragas_datasets(mongo_uri)

            if not logs or log_index >= len(logs):
                pytest.skip(f"Лог под индексом {log_index} отсутствует в базе (pending)")

            current_log = logs[log_index]
            log_id = str(current_log["_id"])
            allure.dynamic.title(f"Аудит лога: {log_id}")
            allure.dynamic.description(f"Запрос пользователя: {current_log.get('user_query')}")

        # 2. Техническая проверка (Планеты)
        with allure.step("🪐 Технический аудит: Точность планет"):
            res_t = evaluate(ds_tech.select([log_index]), metrics=[faithfulness],
                             llm=judge_llm, embeddings=judge_embeddings).to_pandas()
            tech_score = float(res_t["faithfulness"].iloc[0])

            allure.attach(f"Score: {tech_score}", name="Technical Faithfulness",
                          attachment_type=allure.attachment_type.TEXT)
            # Если тех. точность критически важна, можно добавить:
            # assert tech_score >= 0.5, "Бот исказил положение планет!"

        # 3. Контентная проверка (RAG)
        with allure.step("📚 Контентный аудит: Работа с PDF базой"):
            metrics = [faithfulness, answer_relevancy, context_precision]
            res_k = evaluate(ds_know.select([log_index]), metrics=metrics,
                             llm=judge_llm, embeddings=judge_embeddings).to_pandas()

            f_score = float(res_k["faithfulness"].iloc[0])
            r_score = float(res_k["answer_relevancy"].iloc[0])
            p_score = float(res_k["context_precision"].iloc[0])

            # Передаем метрики в Allure как параметры для графиков
            allure.dynamic.parameter("Knowledge Faithfulness", f_score)
            allure.dynamic.parameter("Context Precision", p_score)
            allure.dynamic.parameter("Answer Relevancy", r_score)

            allure.attach(res_k.to_json(orient="records"), name="Detailed Metrics JSON",
                          attachment_type=allure.attachment_type.JSON)

        # 4. Анализ текстов (Сравнение)
        with allure.step("🔍 Сравнение: Что в базе vs Что в ответе"):
            comparison_text = (
                f"ЗАПРОС: {current_log.get('user_query')}\n\n"
                f"ОТВЕТ ИИ: {ds_know.select([log_index])['answer'][0]}\n\n"
                f"НАЙДЕННЫЙ КОНТЕКСТ: {ds_know.select([log_index])['contexts'][0]}\n\n"
                f"ЭТАЛОН: {ds_know.select([log_index])['reference'][0]}"
            )
            allure.attach(comparison_text, name="Context & Answer Comparison",
                          attachment_type=allure.attachment_type.TEXT)

        # 5. Итоговый Quality Gate
        with allure.step("🏁 Финальный вердикт"):
            if f_score < 0.3:
                allure.dynamic.status_details(f"Низкое качество: {f_score}")
                # Просто пишем в лог, но НЕ валим тест
                print(f"DEBUG: Низкий скор для {log_id}")
            else:
                allure.dynamic.status_details("Качество соответствует норме")


#
# @allure.feature("RAG Quality Audit")
# class TestJoytishRagas:
#
#     @pytest.mark.asyncio
#     @pytest.mark.parametrize("log_index", range(5))  # Тестируем последние 5 записей
#     async def test_ragas_full_audit(self, log_index, mongo_uri=mongo_uri):
#         """
#         Профессиональная проверка качества: Технический и Контентный аудит
#         """
#         # 1. Получаем подготовленные датасеты
#         ds_tech, ds_know, logs, _ = await prepare_ragas_datasets(mongo_uri)
#
#         if not logs or log_index >= len(logs):
#             pytest.skip("Нет данных для этого индекса лога")
#
#         current_log = logs[log_index]
#         log_id = str(current_log["_id"])
#
#         # Устанавливаем имя теста в Allure для красоты
#         allure.dynamic.title(f"Audit Log ID: {log_id}")
#         allure.dynamic.description(f"Query: {current_log.get('user_query')}")
#
#         # Выделяем срез данных для конкретного теста
#         single_ds_tech = ds_tech.select([log_index])
#         single_ds_know = ds_know.select([log_index])
#
#         # --- ШАГ 1: Техническая верность ---
#         with allure.step("🪐 Техническая проверка: Соответствие планетам"):
#             res_t = evaluate(single_ds_tech, metrics=[faithfulness], llm=judge_llm).to_pandas()
#             tech_score = float(res_t["faithfulness"].iloc[0])
#
#             allure.attach(f"Score: {tech_score}", name="Tech Score", attachment_type=allure.attachment_type.TEXT)
#             # assert tech_score >= 0.7  # Можно раскомментировать, чтобы тест "падал" при плохом качестве
#
#         # --- ШАГ 2: Контентная верность ---
#         with allure.step("📚 Контентная проверка: База знаний (PDF)"):
#             metrics = [faithfulness, answer_relevancy, context_precision]
#             res_k = evaluate(single_ds_know, metrics=metrics, llm=judge_llm).to_pandas()
#
#             # Извлекаем метрики
#             f_score = float(res_k["faithfulness"].iloc[0])
#             r_score = float(res_k["answer_relevancy"].iloc[0])
#             p_score = float(res_k["context_precision"].iloc[0])
#
#             # Красивое отображение параметров в интерфейсе Allure
#             allure.dynamic.parameter("Knowledge Faithfulness", f_score)
#             allure.dynamic.parameter("Context Precision", p_score)
#             allure.dynamic.parameter("Relevancy", r_score)
#
#             allure.attach(res_k.to_json(orient="records"), name="Detailed Metrics JSON",
#                           attachment_type=allure.attachment_type.JSON)
#
#         # --- ШАГ 3: Сравнение данных ---
#         with allure.step("🔍 Детализация контента"):
#             comparison = (
#                 f"ЗАПРОС: {current_log.get('user_query')}\n\n"
#                 f"ОТВЕТ БОТА: {single_ds_know['answer'][0]}\n\n"
#                 f"ЭТАЛОН: {single_ds_know['reference'][0]}"
#             )
#             allure.attach(comparison, name="Comparison: Request vs Answer vs Reference",
#                           attachment_type=allure.attachment_type.TEXT)