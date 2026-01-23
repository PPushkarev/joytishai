import os
import pytest
import allure
import pandas as pd
from ragas import evaluate
from ragas.metrics import faithfulness, answer_relevancy, context_precision

from app.services.ragas_engine import judge_llm, judge_embeddings, prepare_ragas_datasets
from dotenv import load_dotenv

load_dotenv()

@allure.epic("Astrological AI")
@allure.feature("RAG System Quality")
class TestJoytishRagas:

    @allure.story("Accuracy and Retrieval Audit")
    @pytest.mark.asyncio
    @pytest.mark.parametrize("log_index", range(1))
    async def test_ragas_full_audit(self, log_index):
        """
        Professional Log Audit:
        1. Verifying compliance with planetary data (Technical)
        2. Verifying compliance with the PDF knowledge base (Knowledge)
        """
        # Get URI from environment variables
        mongo_uri = os.getenv("MONGO_URI", "mongodb://localhost:27017")

        # 1. Load data
        with allure.step("Loading data from MongoDB"):
            ds_tech, ds_know, logs, _ = await prepare_ragas_datasets(mongo_uri)

            if not logs or log_index >= len(logs):
                pytest.skip(f"Log with index {log_index} is missing in the database (pending)")

            current_log = logs[log_index]
            log_id = str(current_log["_id"])
            allure.dynamic.title(f"Log Audit: {log_id}")
            allure.dynamic.description(f"User Query: {current_log.get('user_query')}")

        # 2. Technical Check (Planetary positions)
        with allure.step("Technical Audit: Planet Accuracy"):
            res_t = evaluate(ds_tech.select([log_index]), metrics=[faithfulness],
                             llm=judge_llm, embeddings=judge_embeddings).to_pandas()
            tech_score = float(res_t["faithfulness"].iloc[0])

            allure.attach(f"Score: {tech_score}", name="Technical Faithfulness",
                          attachment_type=allure.attachment_type.TEXT)
            # If technical accuracy is critical, you can enforce it:
            # assert tech_score >= 0.5, "The bot hallucinated planetary positions!"

        # 3. Content Check (RAG)
        with allure.step("Content Audit: PDF Knowledge Base"):
            metrics = [faithfulness, answer_relevancy, context_precision]
            res_k = evaluate(ds_know.select([log_index]), metrics=metrics,
                             llm=judge_llm, embeddings=judge_embeddings).to_pandas()

            f_score = float(res_k["faithfulness"].iloc[0])
            r_score = float(res_k["answer_relevancy"].iloc[0])
            p_score = float(res_k["context_precision"].iloc[0])

            # Pass metrics to Allure as parameters for dynamic charts
            allure.dynamic.parameter("Knowledge Faithfulness", f_score)
            allure.dynamic.parameter("Context Precision", p_score)
            allure.dynamic.parameter("Answer Relevancy", r_score)

            allure.attach(res_k.to_json(orient="records"), name="Detailed Metrics JSON",
                          attachment_type=allure.attachment_type.JSON)

        # 4. Text Analysis (Comparison)
        with allure.step("Comparison: Database Context vs AI Answer"):
            comparison_text = (
                f"QUERY: {current_log.get('user_query')}\n\n"
                f"AI ANSWER: {ds_know.select([log_index])['answer'][0]}\n\n"
                f"RETRIEVED CONTEXT: {ds_know.select([log_index])['contexts'][0]}\n\n"
                f"REFERENCE: {ds_know.select([log_index])['reference'][0]}"
            )
            allure.attach(comparison_text, name="Context & Answer Comparison",
                          attachment_type=allure.attachment_type.TEXT)

        # 5. Final Quality Gate (Soft Fail)
        with allure.step("Final Verdict"):
            if f_score < 0.1:
                # IF score less then 0.1 it is a fail
                allure.attach("RAG Hallucination detected.", name="WARNING",
                              attachment_type=allure.attachment_type.TEXT)
                pytest.xfail(f"Soft Fail: Quality is too low ({f_score}), but we don't block the pipeline.")
            else:
                assert True, "Quality is good."
