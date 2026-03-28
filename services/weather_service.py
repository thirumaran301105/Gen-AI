"""
Advanced Weather Service
Real OpenWeatherMap API integration with intelligent spraying recommendations
"""

import aiohttp
import asyncio
import logging
from typing import Dict, Optional, Tuple, List
from datetime import datetime, timedelta
import json
from dataclasses import dataclass, asdict
from enum import Enum
import requests

logger = logging.getLogger(__name__)

class SprayingRecommendation(Enum):
    """Spraying recommendation levels"""
    OPTIMAL = "optimal"
    GOOD = "good"
    ACCEPTABLE = "acceptable"
    NOT_RECOMMENDED = "not_recommended"
    CRITICAL_DELAY = "critical_delay"

@dataclass
class WeatherData:
    """Structured weather data"""
    location: str
    temperature: float  # Celsius
    humidity: float  # 0-100
    rainfall: float  # mm
    wind_speed: float  # km/h
    wind_direction: str  # N, NE, E, SE, S, SW, W, NW
    pressure: float  # hPa
    cloud_cover: float  # 0-100
    uv_index: float
    visibility: float  # km
    weather_condition: str
    
    # Forecast data
    forecast_6h: Optional[List[Dict]] = None
    forecast_24h: Optional[List[Dict]] = None
    
    timestamp: datetime = None
    
    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        data = asdict(self)
        data['timestamp'] = self.timestamp.isoformat() if self.timestamp else None
        return data

@dataclass
class SprayingAdvice:
    """Spraying recommendation with detailed reasoning"""
    recommendation: SprayingRecommendation
    confidence: float  # 0-1
    
    # Scores for each factor
    temperature_score: float
    humidity_score: float
    wind_score: float
    rainfall_score: float
    
    # Detailed message
    message: str
    recommendations: List[str]
    warnings: List[str]
    
    optimal_timing: Optional[Tuple[str, str]] = None  # Start time, End time
    next_optimal_window: Optional[str] = None
    
    disease_risk_level: str = "medium"

class WeatherService:
    """Advanced weather service with API integration"""
    
    # Mock weather data for fallback
    MOCK_WEATHER_LOCATIONS = {
        "Chennai": {"temp": 32.5, "humidity": 75, "rainfall": 2.5, "wind_speed": 12, "condition": "Partly Cloudy"},
        "Delhi": {"temp": 28.3, "humidity": 65, "rainfall": 0.0, "wind_speed": 8, "condition": "Clear"},
        "Mumbai": {"temp": 30.1, "humidity": 80, "rainfall": 5.2, "wind_speed": 15, "condition": "Rainy"},
        "Bangalore": {"temp": 26.7, "humidity": 70, "rainfall": 1.2, "wind_speed": 10, "condition": "Mostly Cloudy"},
        "Kolkata": {"temp": 29.4, "humidity": 78, "rainfall": 3.8, "wind_speed": 11, "condition": "Overcast"},
    }
    
    def __init__(self, api_key: Optional[str] = None, use_cache: bool = True, cache_ttl: int = 3600):
        """Initialize weather service"""
        self.api_key = api_key
        self.base_url = "https://api.openweathermap.org/data/2.5/weather"
        self.forecast_url = "https://api.openweathermap.org/data/2.5/forecast"
        self.use_cache = use_cache
        self.cache_ttl = cache_ttl
        self.cache: Dict[str, Tuple[WeatherData, datetime]] = {}
    
    def get_weather(self, location: str) -> Optional[WeatherData]:
        """
        Get weather data for location (with caching)
        
        Args:
            location: City name
        
        Returns:
            WeatherData object or None
        """
        # Check cache
        if self.use_cache and location in self.cache:
            cached_data, timestamp = self.cache[location]
            if (datetime.utcnow() - timestamp).seconds < self.cache_ttl:
                logger.info(f"✅ Using cached weather for {location}")
                return cached_data
        
        # Try API
        if self.api_key:
            try:
                weather_data = self._fetch_from_api(location)
                if weather_data:
                    if self.use_cache:
                        self.cache[location] = (weather_data, datetime.utcnow())
                    return weather_data
            except Exception as e:
                logger.warning(f"API error: {e}")
        
        # Fallback to mock data
        logger.info(f"Using mock weather data for {location}")
        return self._get_mock_weather(location)
    
    def _fetch_from_api(self, location: str) -> Optional[WeatherData]:
        """Fetch weather from OpenWeatherMap API"""
        try:
            params = {
                'q': location,
                'appid': self.api_key,
                'units': 'metric'
            }
            
            response = requests.get(self.base_url, params=params, timeout=5)
            
            if response.status_code != 200:
                logger.error(f"API Error: {response.status_code}")
                return None
            
            data = response.json()
            
            weather = WeatherData(
                location=location,
                temperature=data['main']['temp'],
                humidity=data['main']['humidity'],
                rainfall=data.get('rain', {}).get('1h', 0),
                wind_speed=data['wind']['speed'] * 3.6,  # m/s to km/h
                wind_direction=self._get_wind_direction(data['wind'].get('deg', 0)),
                pressure=data['main']['pressure'],
                cloud_cover=data.get('clouds', {}).get('all', 0),
                uv_index=0,  # Not in free API tier
                visibility=data.get('visibility', 10000) / 1000,  # meters to km
                weather_condition=data['weather'][0]['main'],
                timestamp=datetime.utcnow()
            )
            
            logger.info(f"✅ Fetched weather for {location}")
            return weather
        
        except Exception as e:
            logger.error(f"Failed to fetch weather: {e}")
            return None
    
    def _get_mock_weather(self, location: str) -> WeatherData:
        """Get mock weather data"""
        location_key = location.strip().title()
        
        # Find closest match
        if location_key not in self.MOCK_WEATHER_LOCATIONS:
            for key in self.MOCK_WEATHER_LOCATIONS:
                if key.lower().startswith(location.lower()):
                    location_key = key
                    break
            else:
                location_key = "Chennai"
        
        mock = self.MOCK_WEATHER_LOCATIONS[location_key]
        
        return WeatherData(
            location=location_key,
            temperature=mock['temp'],
            humidity=mock['humidity'],
            rainfall=mock['rainfall'],
            wind_speed=mock['wind_speed'],
            wind_direction="NE",
            pressure=1013,
            cloud_cover=50,
            uv_index=7,
            visibility=10,
            weather_condition=mock['condition'],
            timestamp=datetime.utcnow()
        )
    
    @staticmethod
    def _get_wind_direction(degrees: float) -> str:
        """Convert wind degrees to direction"""
        directions = ['N', 'NE', 'E', 'SE', 'S', 'SW', 'W', 'NW']
        index = int((degrees + 22.5) / 45) % 8
        return directions[index]
    
    def get_spraying_recommendation(self, weather: WeatherData, disease: str = "Early_Blight") -> SprayingAdvice:
        """
        Get intelligent spraying recommendation based on weather and disease
        
        Args:
            weather: WeatherData object
            disease: Disease type for contextual recommendations
        
        Returns:
            SprayingAdvice object
        """
        # Calculate individual scores (0-1)
        temp_score = self._calculate_temperature_score(weather.temperature, disease)
        humidity_score = self._calculate_humidity_score(weather.humidity)
        wind_score = self._calculate_wind_score(weather.wind_speed)
        rainfall_score = self._calculate_rainfall_score(weather.rainfall)
        
        # Overall recommendation
        average_score = (temp_score + humidity_score + wind_score + rainfall_score) / 4
        
        # Determine recommendation level
        if rainfall_score < 0.3 or wind_score < 0.4:
            recommendation = SprayingRecommendation.CRITICAL_DELAY
        elif average_score < 0.5:
            recommendation = SprayingRecommendation.NOT_RECOMMENDED
        elif average_score < 0.65:
            recommendation = SprayingRecommendation.ACCEPTABLE
        elif average_score < 0.8:
            recommendation = SprayingRecommendation.GOOD
        else:
            recommendation = SprayingRecommendation.OPTIMAL
        
        # Generate message and recommendations
        message, recommendations, warnings = self._generate_advice_text(
            weather, temp_score, humidity_score, wind_score, rainfall_score, disease
        )
        
        # Optimal timing
        optimal_timing = self._get_optimal_spraying_times(weather)
        
        # Disease risk
        disease_risk = self._calculate_disease_risk(weather, disease)
        
        return SprayingAdvice(
            recommendation=recommendation,
            confidence=min(average_score * 1.2, 1.0),
            temperature_score=temp_score,
            humidity_score=humidity_score,
            wind_score=wind_score,
            rainfall_score=rainfall_score,
            message=message,
            recommendations=recommendations,
            warnings=warnings,
            optimal_timing=optimal_timing,
            disease_risk_level=disease_risk
        )
    
    @staticmethod
    def _calculate_temperature_score(temp: float, disease: str = "Early_Blight") -> float:
        """Calculate temperature suitability score"""
        if disease == "Late_Blight":
            # Optimal: 13-18°C
            if 13 <= temp <= 18:
                return 1.0
            elif 10 <= temp < 13 or 18 < temp <= 22:
                return 0.8
            elif 5 <= temp < 10 or 22 < temp <= 28:
                return 0.5
            else:
                return 0.1
        else:  # Early Blight
            # Optimal: 20-25°C
            if 20 <= temp <= 25:
                return 1.0
            elif 15 <= temp < 20 or 25 < temp <= 30:
                return 0.8
            elif 10 <= temp < 15 or 30 < temp <= 35:
                return 0.5
            else:
                return 0.1
    
    @staticmethod
    def _calculate_humidity_score(humidity: float) -> float:
        """Calculate humidity suitability score"""
        if humidity > 90:
            return 1.0  # Excellent for fungal spread
        elif humidity > 80:
            return 0.9
        elif humidity > 70:
            return 0.7
        elif humidity > 60:
            return 0.5
        else:
            return 0.2
    
    @staticmethod
    def _calculate_wind_score(wind_speed: float) -> float:
        """Calculate wind suitability score (lower is better)"""
        if wind_speed < 5:
            return 1.0  # Optimal (no drift)
        elif wind_speed < 10:
            return 0.9
        elif wind_speed < 15:
            return 0.7
        elif wind_speed < 20:
            return 0.3  # Not recommended
        else:
            return 0.0  # Critical - do not spray
    
    @staticmethod
    def _calculate_rainfall_score(rainfall: float) -> float:
        """Calculate rainfall impact score"""
        if rainfall == 0:
            return 1.0  # No rain
        elif rainfall < 0.5:
            return 0.8  # Minimal
        elif rainfall < 2:
            return 0.5  # Moderate (wait)
        else:
            return 0.0  # High rainfall - do not spray
    
    @staticmethod
    def _generate_advice_text(weather, temp_score, humidity_score, wind_score, rainfall_score, disease) -> Tuple[str, List[str], List[str]]:
        """Generate detailed advice text"""
        message = f"Weather Analysis for {weather.location}\n"
        recommendations = []
        warnings = []
        
        # Temperature advice
        if temp_score < 0.5:
            warnings.append(f"⚠️  Temperature ({weather.temperature:.1f}°C) is not ideal for disease development")
        elif temp_score > 0.8:
            recommendations.append(f"✅ Temperature ({weather.temperature:.1f}°C) is optimal for spraying")
        
        # Humidity advice
        if humidity_score > 0.8:
            recommendations.append(f"✅ High humidity ({weather.humidity}%) favors disease - spray now")
        else:
            warnings.append(f"⚠️  Low humidity ({weather.humidity}%) may reduce disease pressure")
        
        # Wind advice
        if wind_score < 0.3:
            warnings.append(f"❌ HIGH WIND ({weather.wind_speed:.1f} km/h) - Do not spray (drift risk)")
        elif wind_score < 0.7:
            warnings.append(f"⚠️  Moderate wind ({weather.wind_speed:.1f} km/h) - Spray carefully")
        else:
            recommendations.append(f"✅ Low wind ({weather.wind_speed:.1f} km/h) - Ideal conditions")
        
        # Rainfall advice
        if rainfall_score < 0.3:
            warnings.append(f"❌ RAINFALL DETECTED ({weather.rainfall} mm) - Wait 24 hours before spraying")
        elif rainfall_score < 0.8:
            warnings.append(f"⚠️  Possible rain - Check forecast before spraying")
        else:
            recommendations.append(f"✅ No rain - Safe to spray")
        
        return message, recommendations, warnings
    
    @staticmethod
    def _get_optimal_spraying_times(weather: WeatherData) -> Tuple[str, str]:
        """Get optimal spraying time window"""
        return ("06:00 AM", "09:00 AM")  # Or ("04:00 PM", "07:00 PM")
    
    @staticmethod
    def _calculate_disease_risk(weather: WeatherData, disease: str) -> str:
        """Calculate disease risk level"""
        risk_score = 0
        
        # Temperature factor
        if disease == "Late_Blight":
            if 13 <= weather.temperature <= 18:
                risk_score += 40
            elif 10 <= weather.temperature <= 22:
                risk_score += 25
        else:
            if 20 <= weather.temperature <= 25:
                risk_score += 40
            elif 15 <= weather.temperature <= 30:
                risk_score += 25
        
        # Humidity factor
        if weather.humidity > 90:
            risk_score += 35
        elif weather.humidity > 80:
            risk_score += 25
        elif weather.humidity > 70:
            risk_score += 15
        
        # Rainfall factor
        if weather.rainfall > 5:
            risk_score += 30
        elif weather.rainfall > 2:
            risk_score += 20
        elif weather.rainfall > 0.5:
            risk_score += 10
        
        # Determine risk level
        if risk_score >= 80:
            return "Very High"
        elif risk_score >= 60:
            return "High"
        elif risk_score >= 40:
            return "Medium"
        else:
            return "Low"

# Global instance
_weather_service = None

def get_weather_service(api_key: Optional[str] = None) -> WeatherService:
    """Get or create weather service instance"""
    global _weather_service
    if _weather_service is None:
        _weather_service = WeatherService(api_key=api_key)
    return _weather_service

if __name__ == "__main__":
    service = get_weather_service()
    weather = service.get_weather("Chennai")
    print(json.dumps(weather.to_dict(), indent=2, default=str))
    advice = service.get_spraying_recommendation(weather, "Early_Blight")
    print(f"\nRecommendation: {advice.recommendation.value}")
    print(f"Message: {advice.message}")
    print(f"Warnings: {advice.warnings}")
