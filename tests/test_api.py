import json
import os

import httpx
import pytest
from dotenv import load_dotenv

# Importing the AI engine for the Unit Test
from app.services.ai_engine import AIEngine

load_dotenv()

# --- ENVIRONMENT CONFIGURATION ---

# 1. YOUR SERVICE (Interpretation/Consultant)
# Base URL from env (default to local), but endpoint is fixed from your main.py
MY_SERVICE_BASE = os.getenv("TEST_API_URL", "http://127.0.0.1:8000")
MY_SERVICE_ENDPOINT = "/api/v1/forecast/generate"

# 2. EXTERNAL ENGINE (Astro Engine on Railway)
ASTRO_ENGINE_BASE = os.getenv(
    "ASTRO_ENGINE_URL", "https://jyotishapi-production.up.railway.app"
)
ASTRO_ENGINE_ENDPOINT = "/api/v1/analyze"

# Final URLs construction
INTERPRETATION_URL = f"{MY_SERVICE_BASE.rstrip('/')}{MY_SERVICE_ENDPOINT}"
ASTRO_ENGINE_URL = f"{ASTRO_ENGINE_BASE.rstrip('/')}{ASTRO_ENGINE_ENDPOINT}"

# Global Payload for testing
payload = {
    "chart_data": {
        "name": "Кошка",
        "date": "1980-03-14",
        "time": "17:30",
        "city": "Иркутск",
        "latitude": 52.286,
        "longitude": 104.2807,
        "timezone": "Asia/Irkutsk",
        "utc_offset": 8.0,
        "julian_day": 2444312.89583,
        "lagna": 134.77,
        "sign": "Лев",
        "planets": {
            "Лагна": {
                "degree": "14°46'28''",
                "sign": "Лев",
                "house": 1,
                "nakshatra": "Пурва-Пхалгуни",
                "pada": 1,
                "nakshatra_lord": "Венера",
                "display_name": "Лагна",
                "retrograde": False,
            },
            "Солнце": {
                "degree": "0°22'44''",
                "sign": "Рыбы",
                "house": 8,
                "nakshatra": "Пурва-Бхадрапада",
                "pada": 4,
                "nakshatra_lord": "Юпитер",
                "display_name": "Солнце",
                "retrograde": False,
            },
            "Луна": {
                "degree": "26°43'38''",
                "sign": "Козерог",
                "house": 6,
                "nakshatra": "Дхаништха",
                "pada": 2,
                "nakshatra_lord": "Марс",
                "display_name": "Луна",
                "retrograde": False,
            },
            "Марс": {
                "degree": "5°39'9''",
                "sign": "Лев",
                "house": 1,
                "nakshatra": "Магха",
                "pada": 2,
                "nakshatra_lord": "Кету",
                "display_name": "Марс R",
                "retrograde": True,
            },
            "Меркурий": {
                "degree": "15°13'5''",
                "sign": "Водолей",
                "house": 7,
                "nakshatra": "Шатабхиша",
                "pada": 3,
                "nakshatra_lord": "Раху",
                "display_name": "Меркурий R",
                "retrograde": True,
            },
            "Юпитер": {
                "degree": "9°21'28''",
                "sign": "Лев",
                "house": 1,
                "nakshatra": "Магха",
                "pada": 3,
                "nakshatra_lord": "Кету",
                "display_name": "Юпитер R",
                "retrograde": True,
            },
            "Венера": {
                "degree": "14°54'20''",
                "sign": "Овен",
                "house": 9,
                "nakshatra": "Бхарани",
                "pada": 1,
                "nakshatra_lord": "Венера",
                "display_name": "Венера",
                "retrograde": False,
            },
            "Сатурн": {
                "degree": "0°2'39''",
                "sign": "Дева",
                "house": 2,
                "nakshatra": "Уттара-Пхалгуни",
                "pada": 2,
                "nakshatra_lord": "Солнце",
                "display_name": "Сатурн R",
                "retrograde": True,
            },
            "Раху": {
                "degree": "4°25'44''",
                "sign": "Лев",
                "house": 1,
                "nakshatra": "Магха",
                "pada": 2,
                "nakshatra_lord": "Кету",
                "display_name": "Раху R",
                "retrograde": True,
            },
            "Кету": {
                "degree": "4°25'44''",
                "sign": "Водолей",
                "house": 7,
                "nakshatra": "Дхаништха",
                "pada": 4,
                "nakshatra_lord": "Марс",
                "display_name": "Кету R",
                "retrograde": True,
            },
        },
    },
    "transit_date": "2026-01-02",
}


@pytest.mark.asyncio
async def test_astro_engine_raw_response():
    """TEST 1: Check if the External Astro Engine (Railway) is alive."""
    print(f"\n[ENGINE] Pinging: {ASTRO_ENGINE_URL}")
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(ASTRO_ENGINE_URL, json=payload)

    assert (
        response.status_code == 200
    ), f"External Engine failed: {response.status_code}"
    print("✅ Astro Engine (External) is returning correct data!")


@pytest.mark.asyncio
async def test_ai_generation_logic():
    """TEST 2: Check Internal AI Logic (Unit Test)."""
    generator = AIEngine()
    mock_data = {
        "derived_tables": {
            "house_rulers": {"1": ["Venus", 3]},
            "houses": {"scores": {"1": {"total_score": 3.0, "status": "Great"}}},
        },
        "transits": {"positions": {"Sun": {"house": 3}}},
    }

    print("\n[AI LOGIC] Testing OpenAI generation...")
    result = await generator.generate_consultation(mock_data)

    assert result is not None
    assert len(result.astrological_analysis) > 100
    print(f"✅ AI Logic Test passed! Title: {result.daily_title}")


@pytest.mark.asyncio
async def test_production_flow_with_real_data():
    """TEST 3: FULL INTEGRATION (Testing YOUR live/local service)."""
    print(f"\n[INTEGRATION] Testing YOUR Consultant service at: {INTERPRETATION_URL}")

    async with httpx.AsyncClient(timeout=60.0) as client:
        try:
            response = await client.post(INTERPRETATION_URL, json=payload)
        except httpx.ConnectError:
            pytest.fail(
                f"❌ Connection failed! Is the server running on {MY_SERVICE_BASE}? Run 'make run'!"
            )

    print(f"[INTEGRATION] HTTP Status: {response.status_code}")
    assert response.status_code == 200, f"Server Error: {response.text}"

    result = response.json()

    # Assertions based on your main.py response structure
    assert "source_data" in result, "Response must contain Astro Engine data"
    assert "ai_analysis" in result, "Response must contain AI Interpretation"

    print("\n✅ Full Integration Flow (Engine + Interpretation) is working perfectly!")
