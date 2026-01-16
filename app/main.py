import logging
import uvicorn
import os
from fastapi import FastAPI, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field
from typing import Any, Dict, Tuple, Optional, List
from dotenv import load_dotenv

# Import Schemas
from app.schemas.forecast import ForecastRequest, ForecastResponse

# Service Imports
from app.services.astro_client import AstroEngineClient
from app.services.ai_engine import AIEngine
from app.services.logger import MongoAILogger
from app.services.validator import ResponseAuditor

# Load environment variables
load_dotenv()

# Configure Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- FASTAPI APP INITIALIZATION ---
app = FastAPI(title="Jyotish AI Interpretation Service (Open Access)")

# Initialize Core Services
astro_client = AstroEngineClient()
ai_engine = AIEngine()
ai_logger = MongoAILogger()

# --- DATA SCHEMAS ---

class PlanetDetail(BaseModel):
    degree: str
    sign: str
    house: int
    nakshatra: str
    pada: int
    nakshatra_lord: str
    retrograde: bool
    display_name: str
    longitude: Optional[float] = None

class ClientChart(BaseModel):
    name: str
    date: str
    time: str
    city: str
    latitude: float
    longitude: float
    timezone: str
    utc_offset: float
    julian_day: float
    lagna: float
    sign: str
    planets: Dict[str, PlanetDetail]

class ForecastRequest(BaseModel):
    user_id: Optional[int] = Field(None, json_schema_extra={"example": 500123445})
    chart_data: ClientChart
    transit_date: str = Field(..., json_schema_extra={"example": "2026-01-02"})
    language: str = Field(default="en")

class ForecastResponse(BaseModel):
    daily_title: str
    astrological_analysis: str
    classic_wisdom: str
    recommendations: List[str]



# --- HELPER FUNCTIONS AUDIT AI CONSULTATION THAT WE GET---

async def run_safe_generation(raw_data: Any, ai_engine: AIEngine) -> Tuple[Any, Dict[str, Any], Optional[Any]]:
    """
    Executes AI generation with a retry mechanism and response auditing.
    """
    max_retries = 3
    final_consultation = None
    last_raw_response = None
    audit_results = {"is_valid": False, "warnings": ["Process failed or not completed"], "audit_score": 0}

    for attempt in range(max_retries):
        try:
            result = await ai_engine.generate_consultation(raw_data)

            if isinstance(result, tuple) and len(result) == 2:
                ai_interpretation, last_raw_response = result
            else:
                ai_interpretation = result
                last_raw_response = None

            if hasattr(ai_interpretation, "model_dump"):
                audit_results = ResponseAuditor.validate_consultation(raw_data, ai_interpretation)
                if audit_results["is_valid"]:
                    final_consultation = ai_interpretation.model_dump()
                    return final_consultation, audit_results, last_raw_response
            else:
                return ai_interpretation, {"is_valid": True, "warnings": ["Plain text response"]}, last_raw_response

        except Exception as e:
            logger.error(f"Error on attempt {attempt + 1}: {e}")
            if attempt == max_retries - 1:
                return f"AI Generation Error: {str(e)}", audit_results, last_raw_response

    return "Failed to generate valid response after retries", audit_results, last_raw_response



@app.post("/api/v1/forecast/generate", tags=["Core & Analytics"])
async def daily_forecast_analytics(request: ForecastRequest, background_tasks: BackgroundTasks):
    """
    Main endpoint, consultation , RAG-generation, audit and background logging.
    """
    # 1. Get data
    raw_data = await astro_client.get_transit_data(request.model_dump())

    if isinstance(raw_data, dict) and "error" in raw_data:
        raise HTTPException(status_code=502, detail=f"Astro Service Error: {raw_data['error']}")

    final_consultation, audit_results, raw_response = await run_safe_generation(raw_data, ai_engine)

    # --- Transfer open AI file into Dic---

    if raw_response:
        if hasattr(raw_response, "model_dump"):
            raw_response = raw_response.model_dump()
        elif hasattr(raw_response, "dict"):
            raw_response = raw_response.dict()
        elif not isinstance(raw_response, dict):

            raw_response = str(raw_response)


    # 3. LOGGING CODE USING BACKGROUND TASK WITH FAST API
    background_tasks.add_task(
        ai_logger.log_analytics,  # OUR FUNCTION
        request.model_dump(),  # ARG 1 USER
        raw_data,  # BOOKS
        final_consultation,  # ANSWER
        raw_response  # TOKEN (теперь тут лежит словарь, и MongoDB его примет)
    )

    return {
        "source_data": raw_data,
        "ai_analysis": final_consultation,
        "audit_report": audit_results
    }


# --- ENDPOINTS ---

# @app.post("/api/v1/forecast/generate", response_model=ForecastResponse, tags=["Core"])
# async def generate_forecast_endpoint(request: ForecastRequest):
#     try:
#         logger.info(f"Generating consultation for {request.chart_data.name}")
#
#         # 1. Сначала получаем данные от астро-движка (ОБЯЗАТЕЛЬНО)
#         raw_data = await astro_client.get_transit_data(request.model_dump())
#
#         # Проверка на ошибку (тот самый код, который мы тестируем)
#         if isinstance(raw_data, dict) and "error" in raw_data:
#             raise HTTPException(status_code=502, detail=f"Astro Service Error: {raw_data['error']}")
#
#         # 2. Передаем эти данные в ИИ
#         result = await ai_engine.generate_consultation(raw_data)
#         return result
#
#     except HTTPException as he:
#         raise he
#     except Exception as e:
#         logger.error(f"Error in Generation: {str(e)}")
#         raise HTTPException(status_code=500, detail=str(e))
# --- DEBUG WRAPPER (ВРЕМЕННАЯ ФУНКЦИЯ ДЛЯ ОТЛОВКИ ОШИБОК) ---
async def debug_logging_wrapper(logger_func, *args, **kwargs):
    print("\n[DEBUG] 🚀 Начинаем фоновую запись в базу...")
    try:
        # Пытаемся запустить оригинальную функцию логгера
        await logger_func(*args, **kwargs)
        print("[DEBUG] ✅ УСПЕХ! Запись добавлена в MongoDB.\n")
    except Exception as e:
        # Если упало - кричим в консоль
        print(f"\n[DEBUG] ❌ ОШИБКА ЛОГИРОВАНИЯ: {type(e).__name__}")
        print(f"[DEBUG] 📜 Текст ошибки: {e}")
        import traceback
        traceback.print_exc()
        print("\n")



# --- SERVER ENTRY POINT ---
if __name__ == "__main__":

    port = int(os.getenv("PORT", 8000))

    uvicorn.run(app, host="0.0.0.0", port=port)