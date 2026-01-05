#!/bin/sh


echo "--- [1/3] Indexing Knowledge Base ---"
python -m app.services.vector_store


echo "--- [2/3] Running AI Judge Evaluation ---"
python -m scripts.run_evals --mode summary


echo "--- [3/3] Starting FastAPI Server ---"
exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}