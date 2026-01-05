
# FIRST STEP MAKE A REQUEST TO JOYTISH API SERVER AND GET RESOPNSE JSON



import httpx
import os
from dotenv import load_dotenv

load_dotenv()

class AstroEngineClient:
    """
    Service client to interact with API JYOTISH , the Astrology Calculation Engine.
    Handles asynchronous service-to-service communication.
    """

    def __init__(self):
        # Pulling configuration from environment variables
        self.base_url = os.getenv("ASTRO_ENGINE_URL")
        self.endpoint = os.getenv("ASTRO_CALCULATE_ENDPOINT", "/api/v1/analyze")
        # Setting reasonable timeouts for the external API call
        self.timeout = httpx.Timeout(15.0, connect=5.0)


    async def get_transit_data(self, request_payload: dict):
        """
        Sends natal chart data and target transit date to the Engine API.
        request_payload: expected to contain 'natal_data' and 'transit_date'.
        """
        # Clean URL construction to avoid double slashes
        url = f"{self.base_url.rstrip('/')}/{self.endpoint.lstrip('/')}"

        # Using AsyncClient as a context manager for efficient connection pooling
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                # Sending the dictionary directly as JSON
                response = await client.post(url, json=request_payload)

                # Raise an exception for 4xx or 5xx status codes
                response.raise_for_status()

                # Return the 8 technical dictionaries from Service 1
                return response.json()

            except httpx.HTTPStatusError as e:
                return {
                    "error": f"API error: {e.response.status_code}",
                    "detail": e.response.text
                }
            except httpx.RequestError as e:
                return {"error": f"Connection failed: {str(e)}"}
            except Exception as e:
                return {"error": f"Unexpected error: {str(e)}"}