# JyotishAI Interpretation Service
![Python](https://img.shields.io/badge/python-3.11+-blue.svg)
![FastAPI](https://img.shields.io/badge/FastAPI-0.104.1-05998b.svg)
![OpenAI](https://img.shields.io/badge/AI-GPT--4o-orange.svg)
![ChromaDB](https://img.shields.io/badge/VectorDB-Chroma-red.svg)
![MongoDB](https://img.shields.io/badge/NoSQL-MongoDB-47A248.svg)
![CI Status](https://github.com/PPushkarev/JYOTISHAPI/actions/workflows/tests.yml/badge.svg)
![Docker](https://img.shields.io/badge/Docker-Ready-blue.svg)
![Tests](https://img.shields.io/badge/Tests-Passing-brightgreen.svg)
![Railway](https://img.shields.io/badge/Deployed%20on-Railway-black.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)
![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)

A professional microservice for interpreting Vedic (Jyotish) horoscopes. The system utilizes **RAG (Retrieval-Augmented Generation)** to analyze planetary transits based on classical scriptures and modern astrological expertise.

---

## Key Features

graph TD
    A[Client Request] --> B[FastAPI Orchestrator]
    B --> C[Astro Engine API]
    C -- Raw Data --> B
    B --> D[Vector DB ChromaDB]
    D -- Context/Books --> B
    B --> E[OpenAI GPT-4o]
    E -- AI Analysis --> F[AI Auditor]
    F -- Validated Response --> B
    B --> G[Client Response]
    B -.-> H[(MongoDB Logs)]

* **Deep Interpretation**: Generates detailed forecasts using OpenAI (GPT-4o) verified against an indexed knowledge base.
* **Knowledge Base (RAG)**: Automated indexing of astrological PDF treatises into ChromaDB to ensure high accuracy of predictions.
* **Safe Generation Pipeline**: Integrated retry mechanism (up to 3 attempts) for AI responses to ensure schema compliance and stability.
* **Analytics & Logging**: Background processing and storage of all requests, raw engine data, and AI responses in MongoDB.
* **AI Auditor**: Automatic validation layer that scores every response for logical consistency and astrological precision.

---

## Tech Stack

* **Framework**: FastAPI (Python 3.11+)
* **AI/LLM**: OpenAI GPT-4o / LangChain
* **Vector DB**: ChromaDB (for RAG context)
* **Database**: MongoDB (for analytics and logging)
* **Testing**: Pytest (Asyncio-based)
* **Deployment**: Docker, Railway, GitHub Actions (CI/CD)

---

## Project Structure

* **app/**: Main application package.
    * **main.py**: FastAPI entry point and endpoint orchestration.
    * **services/**: Business logic (AI Engine, Astro Client, Vector Store, Logger).
    * **schemas/**: Pydantic models for request/response validation.
* **tests/**: Automated unit and integration test suite.
* **.github/workflows/**: CI/CD pipeline configuration (Automated testing & deployment).
* **Dockerfile**: Container configuration.
* **Procfile**: Deployment command for Railway.
* **entrypoint.sh**: Startup script for sequential execution (Indexing -> Server).

---

## Quick Start
### Development Commands (Makefile)

The project includes a `Makefile` to simplify common development tasks. 

* **Install dependencies**: `make install`
* **Run full system**: `make run` (Triggers indexing and starts the server)
* **Rebuild Knowledge Base**: `make index` (Updates the ChromaDB vector store)
* **Execute Tests**: `make test` (Runs End-to-End integration tests)
* **Cleanup**: `make clean` (Removes cache and temporary files)
* **Fast Deploy**: `make deploy` (Cleans, updates requirements, and pushes to GitHub)
* 
###  Environment Configuration
Create a `.env` file in the root directory:
```env

OPENAI_API_KEY: Your secret key from OpenAI, used to authorize GPT-4o requests for horoscope generation. 
OPENAI_MODEL: The specific AI model version used by the service, such as gpt-4o. 
AI_TEMPERATURE: Controls the balance between factual and creative AI responses; lower values ensure more consistent astrological logic. 
MONGO_URI: The full connection string for your MongoDB database, used for background logging and analytics storage. 
API_AUTH_TOKEN: A private security token used to authenticate and protect your API endpoints from unauthorized access. 
TEST_API_URL: The base URL used by the automated test suite to verify the service status, usually http://127.0.0.1:8000. 
ANALYZE_ENDPOINT: The internal path for the interpretation logic, specifically /api/v1/forecast/generate. 
ASTRO_ENGINE_URL: The URL of the external Astro Engine service that calculates planetary positions and house points. 
ASTRO_CALCULATE_ENDPOINT: The specific remote endpoint used to fetch technical transit data from the Astro Engine. 
PYTHONPATH: Set to the root directory to ensure the system correctly finds and imports your application modules. 
PORT: The network port the server listens on, which is automatically assigned in production environments like Railway.