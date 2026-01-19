import json
from unittest.mock import AsyncMock, patch
import asyncio
import allure
import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app

TARGET_ENDPOINT = "/api/v1/forecast/generate"

# Fully compliant payload with all required fields for Pydantic
REAL_PAYLOAD = {
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


@allure.feature("Engine")

@pytest.mark.asyncio
class TestEngineCheck:

    @allure.story("Checking SERVER 422 error")
    @allure.description("Verifies that the server returns 422 Unprocessable Entity when an empty payload is sent.")
    async def test_1_pydantic_validation(self, local_client):
        """TEST 1: Verifies 422 error on empty payload."""

        with allure.step(f"Sending empty POST request to {TARGET_ENDPOINT}"):
            response = await local_client.post(TARGET_ENDPOINT, json={})

        with allure.step("Checking if response status is 422"):

            assert response.status_code == 422, f"Expected 422, but got {response.status_code}. Response: {response.text}"



    @allure.story("Error Handling")
    @allure.description("API SERVER JOYTISH DOES NOT WORK")
    async def test_2_request_fails_astro_service(self, local_client):
        """TEST 2: Checks how the app handles an error from the calculation service."""

        with patch(
                "app.main.astro_client.get_transit_data", new_callable=AsyncMock
        ) as mock_astro:
            mock_astro.return_value = {"error": "Connection lost"}

            with allure.step(f"Sending real payload to broken server API JOYITISH"):
                response = await local_client.post(TARGET_ENDPOINT, json=REAL_PAYLOAD)

            # Если снова 200, значит патч не попал в цель
            assert response.status_code == 502, f"Expected 502 Bad Gateway, but got {response.status_code}"




    @allure.story("Error Handling")
    @allure.description("OPEN AI SERVER DOES NOT WORK")
    async def test_3_ai_fails_but_data_exists(self, local_client):
        """TEST 3: Ensures system handles AI timeout gracefully."""
        mock_astro_res = {"status": "ok", "derived_tables": {}, "transits": {}}

        with patch(
            "app.main.astro_client.get_transit_data", new_callable=AsyncMock
        ) as mock_astro:
            with patch(
                "app.main.ai_engine.generate_consultation", new_callable=AsyncMock
            ) as mock_ai:
                mock_astro.return_value = mock_astro_res
                # Имитируем ошибку
                mock_ai.side_effect = Exception("OpenAI Timeout")

                with allure.step(f"Sending request: Astro Engine works, but OpenAI fails"):
                    response = await local_client.post(TARGET_ENDPOINT, json=REAL_PAYLOAD)
                    assert response.status_code == 200,f"Expected 200 even if AI fails, but got {response.status_code}"
                    res_json = response.json()
                    analysis_content = str(res_json.get("ai_analysis", ""))
                    assert "AI Generation Error" in analysis_content, "Error in AI "

    @allure.story("Full Integration Flow")
    @allure.description("AI and API SERVERS WORK FINE")
    async def test_4_full_success_flow(self, local_client):
        """TEST 4: FULL SUCCESS (Verifying nested structure)"""
        mock_astro_res = {"status": "ok", "derived_tables": {}, "transits": {}}
        mock_ai_res = {
            "daily_title": "Success",
            "astrological_analysis": "Full analysis text.",
            "recommendations": ["Rest"],
            "classic_wisdom": "Patience is key.",
        }

        with patch(
            "app.main.astro_client.get_transit_data", new_callable=AsyncMock
        ) as mock_astro:
            with patch(
                "app.main.ai_engine.generate_consultation", new_callable=AsyncMock
            ) as mock_ai:
                mock_astro.return_value = mock_astro_res
                mock_ai.return_value = mock_ai_res

                with allure.step(f" Astro Engine and OpenAI workng"):
                    response = await local_client.post(TARGET_ENDPOINT, json=REAL_PAYLOAD)

                with allure.step("Code checking"):
                    assert response.status_code == 200, f"Expected 200 , but got {response.status_code}"
                    res_json = response.json()

                    allure.attach(
                        json.dumps(res_json, indent=2, ensure_ascii=False),
                        name="Full Success Response",
                        attachment_type=allure.attachment_type.JSON
                    )

                    assert "ai_analysis" in res_json, "Missing ai_analysis block"
                    assert "source_data" in res_json, "Missing source_data block"
                    assert res_json["ai_analysis"]["daily_title"] == "Success"

    @allure.story("Error Handling")
    @allure.description("Check handling of Astro Service Timeout")
    async def test_5_astro_service_timeout(self, local_client):
        """TEST 5: Checks system behavior on external service timeout."""

        # We simulate a hang/timeout using side_effect with asyncio.TimeoutError
        with patch(
                "app.main.astro_client.get_transit_data", side_effect=asyncio.TimeoutError
        ):
            with allure.step("Simulating external API timeout from Joytish service"):
                response = await local_client.post(TARGET_ENDPOINT, json=REAL_PAYLOAD)

            with allure.step("Verifying that server returns Gateway Error (502 or 504)"):
                # Usually, if a dependency times out, we expect 502 or 504
                assert response.status_code in [502, 504], f"Expected Gateway Error, but got {response.status_code}"




    @allure.story("Edge Cases")
    @allure.description("Check handling of empty data from Astro Service")
    async def test_6_astro_returns_empty_data(self, local_client):
        """TEST 6: Checks system stability when Joytish returns empty structures."""

        # Scenario where API is alive but returns empty planets/houses
        mock_astro_res = {"status": "ok", "planets": {}, "houses": []}
        mock_ai_res = {"daily_title": "Limited Info", "ai_analysis": "No data to analyze"}

        with patch(
                "app.main.astro_client.get_transit_data", new_callable=AsyncMock
        ) as mock_astro:
            with patch(
                    "app.main.ai_engine.generate_consultation", new_callable=AsyncMock
            ) as mock_ai:
                mock_astro.return_value = mock_astro_res
                mock_ai.return_value = mock_ai_res

                with allure.step("Sending request with empty astrological data"):
                    response = await local_client.post(TARGET_ENDPOINT, json=REAL_PAYLOAD)

                with allure.step("Code checking for stability"):
                    assert response.status_code == 200, f"Expected 200, but got {response.status_code}"
                    res_json = response.json()
                    assert "source_data" in res_json

