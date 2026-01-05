from pydantic import BaseModel, Field
from typing import Dict, Any, List, Optional

# Описание данных по конкретной планете
class PlanetInfo(BaseModel):
    degree: str
    sign: str
    house: int
    nakshatra: str
    pada: int
    nakshatra_lord: str
    retrograde: bool
    display_name: str
    longitude: Optional[float] = None

# Структура натальной карты
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
    planets: Dict[str, PlanetInfo]

# Финальный запрос, который приходит от бота
class ForecastRequest(BaseModel):
    chart_data: ClientChart
    transit_date: str

# То, что мы вернем боту после работы ИИ
class ForecastResponse(BaseModel):
    daily_title: str
    astrological_analysis: str
    classic_wisdom: str
    recommendations: List[str]