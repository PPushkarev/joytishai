import json
from unittest.mock import AsyncMock, patch

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


@pytest.mark.asyncio
async def test_1_pydantic_validation():
    """TEST 1: Verifies 422 error on empty payload."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.post(TARGET_ENDPOINT, json={})
    assert response.status_code == 422
    print("✅ Pydantic validation test passed.")


@pytest.mark.asyncio
async def test_2_request_fails_astro_service():
    """TEST 2: Checks how the app handles an error from the calculation service."""

    # ПУТЬ ПАТЧА: Попробуй заменить на путь к самому КЛАССУ сервиса
    # Например, если он лежит в app/services/astro_connector.py:
    # patch("app.services.astro_connector.AstroService.get_transit_data", ...)

    # Но для начала попробуем "ленивый" патч самого модуля:
    with patch(
        "app.main.astro_client.get_transit_data", new_callable=AsyncMock
    ) as mock_astro:
        mock_astro.return_value = {"error": "Connection lost"}

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            response = await ac.post(TARGET_ENDPOINT, json=REAL_PAYLOAD)

    # Если снова 200, значит патч не попал в цель
    assert response.status_code == 502
    print("✅ Service failure test finally passed!")


@pytest.mark.asyncio
async def test_3_ai_fails_but_data_exists():
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

            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as ac:
                response = await ac.post(TARGET_ENDPOINT, json=REAL_PAYLOAD)

    # Теперь твой код возвращает 200, так как run_safe_generation ловит исключение
    assert response.status_code == 200
    res_json = response.json()
    assert "AI Generation Error" in res_json["ai_analysis"]
    print("✅ AI failure handling test passed.")


@pytest.mark.asyncio
async def test_4_full_success_flow():
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

            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as ac:
                response = await ac.post(TARGET_ENDPOINT, json=REAL_PAYLOAD)

    assert response.status_code == 200
    res_json = response.json()

    # ПРОВЕРКА ВЛОЖЕННОЙ СТРУКТУРЫ
    assert "ai_analysis" in res_json
    assert "source_data" in res_json
    assert res_json["ai_analysis"]["daily_title"] == "Success"
    print("✅ Full success flow test passed.")
