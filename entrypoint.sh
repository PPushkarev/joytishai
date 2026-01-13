#!/bin/sh

echo "--- [1/3] Indexing Knowledge Base ---"
# Добавляем || true, чтобы если индексация упадет, билд шел дальше
python -m app.services.vector_store || echo "Indexing failed, skipping..."

echo "--- [2/3] Running AI Judge Evaluation ---"
python -m scripts.run_evals --mode summary || echo "Evaluation failed, skipping..."

echo "--- [3/3] Starting FastAPI Server ---"
# Самая важная строка. PORT подхватится от Railway автоматически
exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}