# Project Variables
PYTHON = python
APP_MODULE = app.main:app
TEST_PATH = tests/test_ai_consultation.py

# Default Test Environment Variables (can be overridden)
TEST_API_URL ?= http://127.0.0.1:8000
ANALYZE_ENDPOINT ?= /api/v1/forecast/generate

.PHONY: help install run index test clean deploy

help:
	@echo "Available commands:"
	@echo "  make install  - Install all project dependencies"
	@echo "  make run      - Launch system (indexing + server) via entrypoint"
	@echo "  make index    - Run PDF knowledge base indexing only"
	@echo "  make test     - Run End-to-End automated tests"
	@echo "  make clean    - Remove temporary files and python cache"
	@echo "  make deploy   - Prepare requirements and push to GitHub"

install:
	pip install -r requirements.txt

run:
	@echo "🚀 Launching system..."
	@chmod +x entrypoint.sh
	./entrypoint.sh

index:
	@echo "📚 Updating Knowledge Base..."
	$(PYTHON) -m app.services.vector_store

test:
	@echo "🧪 Running tests..."
	@# Passing variables directly to pytest to ensure consistency
	TEST_API_URL=$(TEST_API_URL) ANALYZE_ENDPOINT=$(ANALYZE_ENDPOINT) pytest $(TEST_PATH) -v -s

clean:
	@echo "🧹 Cleaning up..."
	rm -rf `find . -type d -name __pycache__`
	rm -rf .pytest_cache
	rm -rf .venv

deploy:
	@echo "📦 Preparing for deployment..."
	@# Ensure we don't accidentally push huge cache folders
	make clean
	pip freeze > requirements.txt
	git add .
	@read -p "Enter commit message: " msg; \
	git commit -m "$$msg"
	git push origin main