# TESTING STEP BY STEP LOGIC


import os
import pytest
import allure
from dotenv import load_dotenv
load_dotenv()


MY_SERVICE_BASE = os.getenv("TEST_API_URL", "http://127.0.0.1:8000")
INTERPRETATION_URL = f"{MY_SERVICE_BASE.rstrip('/')}/api/v1/forecast/generate"

base_payload = {
    "user_id": 101,
    "chart_data": {
        "name": "CoT Tester",
        "date": "1990-01-01",
        "time": "12:00",
        "city": "London",
        "latitude": 51.5,
        "longitude": -0.12,
        "timezone": "Europe/London",
        "utc_offset": 0.0,
        "julian_day": 2447893.0,
        "lagna": 0.0,
        "sign": "Aries",
        "planets": {}
    },
    "transit_date": "2026-01-01",
    "language": "en"
}


@allure.feature("Chain-of-Thought (CoT) Verification")
@pytest.mark.asyncio
class TestReasoning:

    @allure.title("CoT RELIABILITY: Verification of the model's logical steps")
    @allure.description("Force the model to break down its reasoning into 3 steps and verify logical consistency.")
    async def test_step_by_step_reasoning(self, network_client):
        payload = base_payload.copy()

        # Inject prompt to trigger the reasoning logic
        payload["user_query"] = (
            "Что меня ждет сегодня? "
            "Думай шаг за шагом: "
            "Шаг 1: Оцени влияние транзита Солнца. "
            "Шаг 2: Оцени влияние транзита Луны. "
            "Шаг 3: Сделай итоговый прогноз на день. "
            "Обязательно используй слово 'Шаг' перед каждым пунктом."
        )

        with allure.step("Sending request with CoT requirement"):
            response = await network_client.post(INTERPRETATION_URL, json=payload)
            data = response.json()
            ai_text = str(data.get("ai_analysis", {}).get("astrological_analysis", ""))

            allure.attach(ai_text, name="Bot Response (Draft)", attachment_type=allure.attachment_type.TEXT)

        with allure.step("Verifying the presence of reasoning steps (Semantic Parsing)"):
            text_lower = ai_text.lower()

            # assert logic
            assert "солнц" in text_lower, "LOGIC ERROR: The bot skipped analyzing the Sun!"
            assert "лун" in text_lower, "LOGIC ERROR: The bot skipped analyzing the Moon!"


            reasoning_markers = ["однако", "таким образом", "что указывает", "приведет к"]
            has_conclusion = any(marker in text_lower for marker in reasoning_markers)
            assert has_conclusion, "LOGIC ERROR: The bot analyzed planets but failed to make a final conclusion!"

        with allure.step("Verifying the depth of reasoning"):
            # if test less then 300 sybmbols is bad(
            assert len(ai_text) > 300, "LOGIC ERROR: The text is too short to contain Step-by-Step reasoning."