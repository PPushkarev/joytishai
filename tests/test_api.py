# --- INTEGRATIONAL TEST  ---

import os
import pytest
from dotenv import load_dotenv

from app.services.ai_engine import AIEngine
import allure

load_dotenv()

# 1. SERVICE (Interpretation/Consultant)
# Base URL from env (default to local), but endpoint is fixed from your main.py
MY_SERVICE_BASE = os.getenv("TEST_API_URL", "http://127.0.0.1:8000")
MY_SERVICE_ENDPOINT = "/api/v1/forecast/generate"

# 2. EXTERNAL ENGINE
ASTRO_ENGINE_BASE = os.getenv(
    "ASTRO_ENGINE_URL", "https://jyotishapi-production.up.railway.app"
)
ASTRO_ENGINE_ENDPOINT = "/api/v1/analyze"

# Final URLs construction
INTERPRETATION_URL = f"{MY_SERVICE_BASE.rstrip('/')}{MY_SERVICE_ENDPOINT}"
ASTRO_ENGINE_URL = f"{ASTRO_ENGINE_BASE.rstrip('/')}{ASTRO_ENGINE_ENDPOINT}"

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

payload_ai = {
    "user_id": 500123445,
    "chart_data": {
        "name": "Собака",
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
                "retrograde": False,
                "display_name": "Лагна"
            },
            "Солнце": {
                "degree": "0°22'44''",
                "sign": "Рыбы",
                "house": 8,
                "nakshatra": "Пурва-Бхадрапада",
                "pada": 4,
                "nakshatra_lord": "Юпитер",
                "retrograde": False,
                "display_name": "Солнце"
            },
            "Луна": {
                "degree": "26°43'38''",
                "sign": "Козерог",
                "house": 6,
                "nakshatra": "Дхаништха",
                "pada": 2,
                "nakshatra_lord": "Марс",
                "retrograde": False,
                "display_name": "Луна",
                "longitude": 26.72722222222222
            },
            "Марс": {
                "degree": "5°39'9''",
                "sign": "Лев",
                "house": 1,
                "nakshatra": "Магха",
                "pada": 2,
                "nakshatra_lord": "Кету",
                "retrograde": True,
                "display_name": "Марс R"
            },
            "Меркурий": {
                "degree": "15°13'5''",
                "sign": "Водолей",
                "house": 7,
                "nakshatra": "Шатабхиша",
                "pada": 3,
                "nakshatra_lord": "Раху",
                "retrograde": True,
                "display_name": "Меркурий R"
            },
            "Юпитер": {
                "degree": "9°21'28''",
                "sign": "Лев",
                "house": 1,
                "nakshatra": "Магха",
                "pada": 3,
                "nakshatra_lord": "Кету",
                "retrograde": True,
                "display_name": "Юпитер R"
            },
            "Венера": {
                "degree": "14°54'20''",
                "sign": "Овен",
                "house": 9,
                "nakshatra": "Бхарани",
                "pada": 1,
                "nakshatra_lord": "Венера",
                "retrograde": False,
                "display_name": "Венера"
            },
            "Сатурн": {
                "degree": "0°2'39''",
                "sign": "Дева",
                "house": 2,
                "nakshatra": "Уттара-Пхалгуни",
                "pada": 2,
                "nakshatra_lord": "Солнце",
                "retrograde": True,
                "display_name": "Сатурн R"
            },
            "Раху": {
                "degree": "4°25'44''",
                "sign": "Лев",
                "house": 1,
                "nakshatra": "Магха",
                "pada": 2,
                "nakshatra_lord": "Кету",
                "retrograde": True,
                "display_name": "Раху R"
            },
            "Кету": {
                "degree": "4°25'44''",
                "sign": "Водолей",
                "house": 7,
                "nakshatra": "Дхаништха",
                "pada": 4,
                "nakshatra_lord": "Марс",
                "retrograde": True,
                "display_name": "Кету R"
            }
        }
    },
    "transit_date": "2026-01-02",
    "language": "ru"
}


@allure.feature("API")
@pytest.mark.asyncio
class TestAstroEngineAPI:



    @allure.story("JOYTISHAPI")
    @allure.description("Check if the External Astro Engine (Railway) is alive")

    async def test_1_astro_engine_raw_response(self, api_client):
        """TEST 1: Check if the External Astro Engine (Railway) is alive."""
        with allure.step(f"\n[ENGINE] Pinging: {ASTRO_ENGINE_URL}"):
            response = await api_client.post(ASTRO_ENGINE_URL, json=payload)
            response_time = response.elapsed.total_seconds()

        with allure.step("Checking time response"):
            allure.attach(str(response_time), name="Response Time (sec)", attachment_type=allure.attachment_type.TEXT)
            assert response_time < 10, "Response is slow!"

        with allure.step("Checking code response"):
            assert (response.status_code == 200), f"External Engine failed: {response.status_code}"
            data = response.json()
            assert len(data) > 0, "Response is empty!"

    @allure.story("JOYTISHAI")
    @allure.description("Check Internal AI Logic (Integration Test).")

    async def test_2_ai_generation_logic(self):
        """TEST 2: Check Internal AI Logic (Unit Test)."""
        generator = AIEngine()
        with allure.step("Checking AI connection using AI Engine"):
            result = await generator.generate_consultation(payload_ai)

        allure.attach(
            str(result.astrological_analysis),
            name="Full AI Response",
            attachment_type=allure.attachment_type.TEXT
        )
        assert result is not None
        assert len(result.astrological_analysis) > 100, "AI Response is empty!"

    @allure.story("Production external endpoit")
    @allure.description("FULL INTEGRATION (Testing  service orchestrator).")
    @allure.story("Production End-to-End Flow")
    @allure.description(
        "Perform a full integration test by calling the live API and validating the AI-generated astrological report.")
    async def test_3_production_flow_with_real_data(self, api_client):
        """
        TEST 3: Validate the full orchestration flow.
        Checks connection to Railway, RAG context retrieval, and OpenAI response formatting.
        """

        # 1. Dispatch Request
        with allure.step(f"POST request to: {INTERPRETATION_URL}"):
            response = await api_client.post(
                INTERPRETATION_URL,
                json=payload_ai,
                timeout=60.0  # Increased timeout for deep AI analysis
            )

        # 2. Validate HTTP Status
        with allure.step("Validate HTTP 200 Status"):
            status = response.status_code
            print(f"\n[DEBUG] Connection Status: {status}")
            assert status == 200, f"Expected 200 OK, but got {status}. Response: {response.text}"

        # 3. Parse and Debug Response Data
        with allure.step("Extract and Debug JSON Response"):
            try:
                data = response.json()
            except Exception as e:
                pytest.fail(f"Failed to parse JSON response: {e}")

            # PRINT FOR LOCAL DEBUGGING (Visible in PyCharm and GitHub Actions Logs)
            print("\n" + "=" * 60)
            print("--- AI SERVICE RESPONSE DEBUG ---")
            print(f"Response Keys: {list(data.keys())}")
            # This will show us EXACTLY what is inside the field
            print(f"Content of 'astrological_analysis': '{data.get('astrological_analysis')}'")
            print("=" * 60 + "\n")

            # Attach the full raw JSON to Allure for visual inspection
            import json
            allure.attach(
                json.dumps(data, indent=2, ensure_ascii=False),
                name="Raw API Response",
                attachment_type=allure.attachment_type.JSON
            )

        # 4. Assert Content Integrity
        with allure.step("Verify Astrological Content"):
            # Attempt to retrieve content from primary or fallback keys
            analysis = data.get("astrological_analysis")

            # Diagnostic attachment
            allure.attach(
                str(analysis),
                name="Extracted Analysis Text",
                attachment_type=allure.attachment_type.TEXT
            )

            # Check if the field exists and is not an empty string/None
            assert analysis is not None, "The 'astrological_analysis' key is missing from the response!"
            assert isinstance(analysis, str), f"Expected string in analysis, but got {type(analysis)}"

            content_len = len(analysis.strip())
            print(f"[DEBUG] Character count: {content_len}")

            # Final validation: Content must be descriptive (at least 100 characters)
            assert content_len > 100, (
                f"AI generated an insufficient response. "
                f"Length: {content_len} chars. Content: '{analysis}'"
            )

    async def test_3_production_flow_with_real_data(self, api_client):
        """TEST 3: FULL INTEGRATION (Testing API JOYTISH server and AI Consultation)."""

        with allure.step(f"Calling My Service: {INTERPRETATION_URL}"):
            response = await api_client.post(INTERPRETATION_URL, json=payload_ai)

        with allure.step("Checking code response"):
            assert (response.status_code == 200), f"External Engine failed: {response.status_code}"

        with allure.step("Extracting and Checking AI Text"):
            data = response.json()


            ai_text_content = data.get("ai_analysis", "")


            allure.attach(
                str(ai_text_content),
                name="Actual AI Analysis Text",
                attachment_type=allure.attachment_type.TEXT
            )

            assert ai_text_content  != None, f"AI text is not exist"

