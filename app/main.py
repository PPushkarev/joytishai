import logging
import uvicorn
import os
from fastapi import FastAPI, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field
from typing import Any, Dict, Tuple, Optional, List
from dotenv import load_dotenv
from app.services.judge_engine import execute_judge_cycle
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





# --- SIMPL FUNCTION FOR ATLAS DB LOGGING ANSERS INFORMATION FOR AI JUDGE---
async def simple_log_execution(user_data: Any, context: Any, answer: dict, raw_tokens: Any):
    """
    Write info in DB
    """

    safe_tokens = raw_tokens
    try:
        if hasattr(raw_tokens, "model_dump"):
            safe_tokens = raw_tokens.model_dump()
        elif hasattr(raw_tokens, "dict"):
            safe_tokens = raw_tokens.dict()
        elif not isinstance(raw_tokens, dict):
            safe_tokens = str(raw_tokens)
    except Exception as e:
        safe_tokens = f"Error serializing tokens: {str(e)}"
    try:

        await ai_logger.log_analytics(
            user_data,
            context,
            answer,
            safe_tokens
        )

    except Exception as e:

        print(f"❌ [LOG] Error loggin functin: {e}")






@app.post("/api/v1/forecast/generate", tags=["Core & Analytics"])
async def daily_forecast_analytics(request: ForecastRequest):

    """
    Main endpoint: Consultation -> Validation -> Simple Logging
    """

    # 1. Get data (Astro)
    raw_data = await astro_client.get_transit_data(request.model_dump())

    if isinstance(raw_data, dict) and "error" in raw_data:
        raise HTTPException(status_code=502, detail=f"Astro Service Error: {raw_data['error']}")

    # 2. Answer generation(AI + Validation)
    final_consultation, audit_results, raw_response = await run_safe_generation(raw_data, ai_engine)

    # 3. SIMPLE LOGGING ( BackgroundTasks)
    await simple_log_execution(
        request,
        raw_data,
        final_consultation,
        raw_response
    )

    # 4. get result
    return {
        "source_data": raw_data,
        "ai_analysis": final_consultation,
        "audit_report": audit_results
    }



# FUNCTION FOR JUDGE ANSWERS STATISTIC MODEL



@app.get("/api/v1/analytics/stats", tags=["Core & Analytics"])
async def get_analytics_summary():
    """
    Retrieves the average quality of consultations (faithfulness, relevancy)
    and general usage statistics based on AI Judge evaluations.
    """

    # 1. Calculate statistics (Aggregation Pipeline)
    pipeline = [
        {
            "$match": { "evaluation.status": "evaluated" }  # Filter: only evaluated logs
        },
        {
            "$group": {
                "_id": None,
                "total_consultations": {"$sum": 1},
                "avg_faithfulness": {"$avg": "$evaluation.faithfulness"},
                "avg_relevancy": {"$avg": "$evaluation.relevancy"},
                "avg_score": {"$avg": "$evaluation.score"}
            }
        },
        {
            "$project": {
                "_id": 0,
                "total_consultations": 1,
                "avg_faithfulness": {"$round": ["$avg_faithfulness", 2]},
                "avg_relevancy": {"$round": ["$avg_relevancy", 2]}
            }
        }
    ]

    # Execute the pipeline
    stats = await ai_logger.collection.aggregate(pipeline).to_list(length=1)

    # 2. Fetch recent evaluated logs for display
    recent_logs = await ai_logger.collection.find(
        {"evaluation.status": "evaluated"},
        {"response": 0, "context": 0, "source_data": 0} # Exclude heavy fields to optimize response speed
    ).sort("timestamp", -1).limit(5).to_list(length=5)

    # 3. SERIALIZATION FIX: Convert ObjectId to String
    # FastAPI cannot serialize binary MongoDB ObjectIds to JSON, so we convert them manually.
    for log in recent_logs:
        if "_id" in log:
            log["_id"] = str(log["_id"])

    return {
        "statistics": stats[0] if stats else "No data yet",
        "recent_evaluations": recent_logs
    }


# --- NEW ADMIN ENDPOINT ---
@app.post("/api/v1/admin/run-judge", tags=["Admin Tools"])
async def trigger_judge_manual(background_tasks: BackgroundTasks):
    """
    Triggers the AI Judge process in the background.
    Useful for manual execution from the Admin Dashboard.
    """
    mongo_uri = os.getenv("MONGO_URI")

    if not mongo_uri:
        return {"error": "MONGO_URI not configured on server"}

    # Run in background (non-blocking)
    background_tasks.add_task(execute_judge_cycle, mongo_uri)

    return {
        "message": "Judge started in background 🚀",
        "info": "Results will appear in the dashboard shortly."
    }

# --- SERVER ENTRY POINT ---
if __name__ == "__main__":

    port = int(os.getenv("PORT", 8000))

    uvicorn.run(app, host="0.0.0.0", port=port)