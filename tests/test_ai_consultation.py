# End-to-End TEST CHECKING ALL SYSTEM AND FINAL WORKING PROCESS


import os

import httpx
import pytest
from dotenv import load_dotenv

load_dotenv()


@pytest.mark.asyncio
async def test_api_consultation_full_flow():
    # Собираем URL из компонентов
    base_url = os.getenv("TEST_API_URL", "http://127.0.0.1:8000")
    endpoint = os.getenv("ANALYZE_ENDPOINT", "/api/v1/forecast/generate")


    api_url = f"{base_url.rstrip('/')}{endpoint}"

    print(f"\n🚀 Target API: {api_url}")
    """
    End-to-End TEST CHECKING ALL SYSTEM AND FINAL WORKING PROCESS
    """

    payload = {
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
                    "display_name": "Лагна",
                },
                "Солнце": {
                    "degree": "0°22'44''",
                    "sign": "Рыбы",
                    "house": 8,
                    "nakshatra": "Пурва-Бхадрапада",
                    "pada": 4,
                    "nakshatra_lord": "Юпитер",
                    "retrograde": False,
                    "display_name": "Солнце",
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
                    "longitude": 26.72722222222222,
                },
                "Марс": {
                    "degree": "5°39'9''",
                    "sign": "Лев",
                    "house": 1,
                    "nakshatra": "Магха",
                    "pada": 2,
                    "nakshatra_lord": "Кету",
                    "retrograde": True,
                    "display_name": "Марс R",
                },
                "Меркурий": {
                    "degree": "15°13'5''",
                    "sign": "Водолей",
                    "house": 7,
                    "nakshatra": "Шатабхиша",
                    "pada": 3,
                    "nakshatra_lord": "Раху",
                    "retrograde": True,
                    "display_name": "Меркурий R",
                },
                "Юпитер": {
                    "degree": "9°21'28''",
                    "sign": "Лев",
                    "house": 1,
                    "nakshatra": "Магха",
                    "pada": 3,
                    "nakshatra_lord": "Кету",
                    "retrograde": True,
                    "display_name": "Юпитер R",
                },
                "Венера": {
                    "degree": "14°54'20''",
                    "sign": "Овен",
                    "house": 9,
                    "nakshatra": "Бхарани",
                    "pada": 1,
                    "nakshatra_lord": "Венера",
                    "retrograde": False,
                    "display_name": "Венера",
                },
                "Сатурн": {
                    "degree": "0°2'39''",
                    "sign": "Дева",
                    "house": 2,
                    "nakshatra": "Уттара-Пхалгуни",
                    "pada": 2,
                    "nakshatra_lord": "Солнце",
                    "retrograde": True,
                    "display_name": "Сатурн R",
                },
                "Раху": {
                    "degree": "4°25'44''",
                    "sign": "Лев",
                    "house": 1,
                    "nakshatra": "Магха",
                    "pada": 2,
                    "nakshatra_lord": "Кету",
                    "retrograde": True,
                    "display_name": "Раху R",
                },
                "Кету": {
                    "degree": "4°25'44''",
                    "sign": "Водолей",
                    "house": 7,
                    "nakshatra": "Дхаништха",
                    "pada": 4,
                    "nakshatra_lord": "Марс",
                    "retrograde": True,
                    "display_name": "Кету R",
                },
            },
        },
        "transit_date": "2026-01-02",
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(api_url, json=payload, timeout=60.0)

    assert response.status_code == 200

    data = response.json()

    # Извлекаем анализ
    # ... (предыдущая часть кода теста)

    # Извлекаем анализ
    ai_report = data.get("ai_analysis")

    print("\n" + "=" * 60)
    print("🤖 AI RESPONSE RECEIVED:")
    print("=" * 60)

    # Если ИИ прислал словарь (JSON)
    if isinstance(ai_report, dict):
        print(f"📌 TITLE: {ai_report.get('daily_title')}")
        print(f"🔬 ANALYSIS: {ai_report.get('astrological_analysis')}")
        print(f"🏛 WISDOM: {ai_report.get('classic_wisdom')}")

        # --- НОВЫЙ БЛОК: РЕКОМЕНДАЦИИ ---
        print("\n💡 RECOMMENDATIONS:")
        recs = ai_report.get("recommendations", [])
        if recs:
            for idx, rec in enumerate(recs, 1):
                print(f"  {idx}. {rec}")
        else:
            print("  (No recommendations provided)")
        # -------------------------------

    else:
        print(ai_report)

    # Добавим также проверку (assertion), что рекомендации пришли и это список
    assert "recommendations" in ai_report
    assert isinstance(ai_report["recommendations"], list)
    assert len(ai_report["recommendations"]) > 0

    print("=" * 60)
