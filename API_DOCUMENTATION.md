# 📚 Rural Advisory System API Documentation

## Overview

The Rural Advisory System provides a comprehensive REST API for AI-powered crop disease detection and treatment recommendations.

**API Version:** 2.0.0  
**Base URL:** `https://yourdomain.com/api`  
**Documentation:** `https://yourdomain.com/docs` (Swagger UI)  
**Schema:** `https://yourdomain.com/openapi.json`

---

## Authentication

### JWT Token

All protected endpoints require JWT authentication.

#### Registration
```http
POST /auth/register
Content-Type: application/json

{
  "name": "Farmer Name",
  "phone": "+91-1234567890",
  "email": "farmer@example.com",
  "primary_crops": ["tomato", "potato"],
  "language_preference": "ta"
}

Response:
{
  "success": true,
  "user_id": "uuid-here",
  "token": "eyJhbGciOiJIUzI1NiIs...",
  "message": "User registered successfully"
}
```

#### Login
```http
POST /auth/login
Content-Type: application/json

{
  "email": "farmer@example.com",
  "password": "secure_password"
}

Response:
{
  "token": "eyJhbGciOiJIUzI1NiIs...",
  "user_id": "uuid-here"
}
```

#### Using Token
```http
GET /api/predictions
Authorization: Bearer eyJhbGciOiJIUzI1NiIs...
```

---

## Endpoints

### 1. Health & Status

#### Health Check
```http
GET /health

Response:
{
  "status": "healthy",
  "version": "2.0.0",
  "timestamp": "2024-01-15T10:30:00Z",
  "database": "connected",
  "model_manager": "loaded"
}
```

#### API Info
```http
GET /api/info

Response:
{
  "name": "Rural Agricultural Advisory System API",
  "version": "2.0.0",
  "endpoints": {
    "predictions": "/api/predictions",
    "weather": "/api/weather",
    "analytics": "/api/analytics",
    "users": "/api/users",
    "feedback": "/api/feedback"
  }
}
```

---

### 2. Disease Prediction

#### Predict from Image
```http
POST /api/predictions
Authorization: Bearer <token>
Content-Type: multipart/form-data

Body:
- file: <image.jpg>

Query Parameters:
- use_ensemble: boolean (default: true)
- location: string (optional, for weather context)
- crop_type: string (optional)

Response:
{
  "prediction_id": "pred-uuid-123",
  "disease_id": "early_blight",
  "disease_name": "Early Blight",
  "confidence": 0.87,
  "model_name": "ensemble",
  "model_version": "2.0",
  "processing_time": 0.234,
  "ensemble_results": {
    "mobilenetv2": {
      "disease": "Early Blight",
      "confidence": 0.89
    },
    "efficientnet": {
      "disease": "Early Blight",
      "confidence": 0.85
    }
  },
  "treatment": {
    "chemical": "Mancozeb 75% WP",
    "dosage": "2.5-3 gm per liter",
    "organic": "Bordeaux Mixture 1%",
    "precautions": [
      "Wear protective gear",
      "Spray early morning",
      "Do not spray during rain"
    ]
  },
  "image_hash": "abc123def456...",
  "timestamp": "2024-01-15T10:30:00Z"
}
```

#### Get Previous Prediction
```http
GET /api/predictions/{prediction_id}
Authorization: Bearer <token>

Response:
{
  "prediction_id": "pred-uuid-123",
  "disease_id": "early_blight",
  "disease_name": "Early Blight",
  "confidence": 0.87,
  ...
}
```

#### Get User Predictions
```http
GET /api/predictions/user/{user_id}
Authorization: Bearer <token>

Query Parameters:
- limit: integer (default: 100, max: 1000)
- offset: integer (default: 0)

Response:
{
  "user_id": "user-uuid",
  "total": 45,
  "predictions": [...]
}
```

#### Batch Predictions
```http
POST /api/predictions/batch
Authorization: Bearer <token>
Content-Type: application/json

Body:
{
  "predictions": [
    {
      "user_id": "user1",
      "location": "Chennai",
      "crop_type": "tomato"
    },
    {
      "user_id": "user2",
      "location": "Delhi"
    }
  ],
  "callback_url": "https://yourapp.com/webhook"
}

Response:
{
  "batch_id": "batch-uuid",
  "total": 2,
  "processed": 0,
  "status": "queued",
  "results": []
}
```

---

### 3. Weather

#### Get Current Weather
```http
POST /api/weather
Authorization: Bearer <token>
Content-Type: application/json

Body:
{
  "location": "Chennai",
  "disease": "Early_Blight"
}

Response:
{
  "location": "Chennai",
  "temperature": 32.5,
  "humidity": 75,
  "rainfall": 2.5,
  "wind_speed": 12.0,
  "weather_condition": "Partly Cloudy",
  "recommendation": "optimal",
  "recommendation_level": "RECOMMENDED",
  "spraying_advice": [
    "Current conditions are favorable",
    "No rain expected",
    "Temperature is optimal"
  ],
  "warnings": [],
  "disease_risk_level": "High",
  "optimal_spraying_times": ["06:00 AM", "09:00 AM"]
}
```

#### Get Weather Forecast
```http
GET /api/weather/forecast
Authorization: Bearer <token>

Query Parameters:
- location: string (required)
- days: integer (1-14, default: 5)

Response:
{
  "location": "Chennai",
  "forecast_days": 5,
  "forecast": [
    {
      "date": "2024-01-16",
      "temperature_high": 34,
      "temperature_low": 26,
      "humidity": 75,
      "rainfall": 0,
      "condition": "Clear"
    },
    ...
  ]
}
```

---

### 4. Treatments

#### Get Treatment for Disease
```http
GET /api/treatments/{disease}
Authorization: Bearer <token>

Response:
{
  "disease": "Early_Blight",
  "tamil_name": "ஆரம்ப புல்லி நோய்",
  "chemical_treatment": [
    {
      "name": "Mancozeb 75% WP",
      "dosage": "2.5-3 gm per liter",
      "frequency": "Every 7-10 days"
    }
  ],
  "organic_treatment": [
    {
      "name": "Bordeaux Mixture 1%",
      "dosage": "10 ml per liter",
      "frequency": "Every 7-10 days"
    }
  ],
  "precautions": [...],
  "prevention": [...]
}
```

#### Submit Feedback
```http
POST /api/feedback
Authorization: Bearer <token>
Content-Type: application/json

Body:
{
  "prediction_id": "pred-uuid-123",
  "feedback": "correct",
  "actual_disease": "Early_Blight",
  "comments": "Prediction was accurate"
}

Response:
{
  "success": true,
  "message": "Feedback received",
  "feedback_id": "feedback-uuid"
}
```

---

### 5. Analytics

#### Get System Analytics
```http
POST /api/analytics
Authorization: Bearer <token>
Content-Type: application/json

Body:
{
  "days": 30,
  "disease_filter": ["Early_Blight", "Late_Blight"],
  "location_filter": ["Chennai", "Delhi"]
}

Response:
{
  "total_predictions": 487,
  "average_confidence": 0.856,
  "accuracy_by_disease": {
    "Early_Blight": 0.92,
    "Late_Blight": 0.89,
    "Healthy": 0.95
  },
  "disease_distribution": {
    "Early_Blight": 150,
    "Late_Blight": 120,
    "Healthy": 180,
    "Powdery_Mildew": 37
  },
  "trends": [
    {
      "date": "2024-01-15",
      "disease": "Early_Blight",
      "count": 12
    }
  ],
  "treatment_outcomes": {
    "improved": 156,
    "no_change": 45,
    "worsened": 12
  },
  "period_days": 30
}
```

---

### 6. User Profile

#### Get Profile
```http
GET /api/users/profile
Authorization: Bearer <token>

Response:
{
  "user_id": "user-uuid",
  "name": "Farmer Name",
  "phone": "+91-1234567890",
  "email": "farmer@example.com",
  "district": "Chennai",
  "farm_size_acres": 10,
  "primary_crops": ["tomato", "potato"],
  "created_at": "2024-01-01T00:00:00Z",
  "total_predictions": 45,
  "accuracy_feedback": 0.89
}
```

#### Update Profile
```http
PUT /api/users/profile
Authorization: Bearer <token>
Content-Type: application/json

Body:
{
  "name": "Updated Name",
  "phone": "+91-9876543210",
  "farm_size_acres": 15,
  "primary_crops": ["tomato", "potato", "rice"]
}

Response:
{
  "success": true,
  "message": "Profile updated",
  "user_id": "user-uuid"
}
```

---

### 7. Disease Database

#### List All Diseases
```http
GET /api/diseases

Response:
{
  "total": 6,
  "diseases": [
    {
      "id": "Early_Blight",
      "name": "Early Blight",
      "severity": "medium",
      "crops": ["tomato", "potato"]
    },
    ...
  ]
}
```

#### Get Disease Details
```http
GET /api/diseases/{disease_id}

Response:
{
  "id": "Early_Blight",
  "name": "Early Blight",
  "tamil_name": "ஆரம்ப புல்லி நோய்",
  "scientific_name": "Alternaria solani",
  "crops": ["tomato", "potato"],
  "severity": "medium",
  "cause": "Fungal infection...",
  "symptoms": [...],
  "optimal_conditions": {...},
  "treatment": {...},
  "precautions": [...],
  "prevention": [...]
}
```

---

## Error Handling

### Standard Error Response

```json
{
  "error": "400",
  "detail": "Invalid image format",
  "timestamp": "2024-01-15T10:30:00Z",
  "request_id": "req-uuid-123"
}
```

### Common Status Codes

| Code | Meaning |
|------|---------|
| 200 | Success |
| 201 | Created |
| 400 | Bad Request |
| 401 | Unauthorized |
| 403 | Forbidden |
| 404 | Not Found |
| 422 | Validation Error |
| 429 | Rate Limited |
| 500 | Server Error |
| 503 | Service Unavailable |

---

## Rate Limiting

- **API Rate Limit:** 100 requests per minute
- **Burst Limit:** 20 additional requests
- **Header:** `X-RateLimit-Remaining`

Example:
```
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
X-RateLimit-Reset: 1234567890
```

---

## Pagination

### Query Parameters

```
GET /api/predictions/user/{user_id}?limit=50&offset=0
```

### Response

```json
{
  "total": 487,
  "limit": 50,
  "offset": 0,
  "data": [...]
}
```

---

## Webhooks

### Batch Processing Callbacks

When batch processing completes, a POST request is sent to your callback URL:

```json
{
  "batch_id": "batch-uuid",
  "status": "completed",
  "total": 100,
  "processed": 100,
  "successful": 98,
  "failed": 2,
  "results": [...]
}
```

---

## SDKs & Libraries

### Python
```python
pip install rural-advisory-sdk

from rural_advisory import Client

client = Client(token="your-token")
prediction = client.predict_disease(image_path="path/to/image.jpg")
print(prediction.disease_name, prediction.confidence)
```

### JavaScript/Node.js
```javascript
npm install rural-advisory-sdk

const { RuralAdvisory } = require('rural-advisory-sdk');

const client = new RuralAdvisory({ token: 'your-token' });
const prediction = await client.predictDisease('./image.jpg');
console.log(prediction.diseaseName, prediction.confidence);
```

### cURL Examples

```bash
# Predict disease
curl -X POST https://yourdomain.com/api/predictions \
  -H "Authorization: Bearer your-token" \
  -F "file=@leaf.jpg"

# Get weather
curl -X POST https://yourdomain.com/api/weather \
  -H "Authorization: Bearer your-token" \
  -H "Content-Type: application/json" \
  -d '{"location":"Chennai","disease":"Early_Blight"}'

# Get analytics
curl -X POST https://yourdomain.com/api/analytics \
  -H "Authorization: Bearer your-token" \
  -H "Content-Type: application/json" \
  -d '{"days":30}'
```

---

## Changelog

### v2.0.0 (Current)
- ✅ Ensemble model predictions
- ✅ Advanced weather integration
- ✅ Full analytics dashboard
- ✅ Batch processing
- ✅ JWT authentication
- ✅ Comprehensive testing

### v1.0.0
- Initial release
- Single model prediction
- Basic weather integration
- Simple database

---

## Support & Contact

- **Documentation:** https://docs.ruralavisory.com
- **Issues:** https://github.com/yourorg/rural_advisory/issues
- **Email:** api-support@ruralavisory.com
- **Slack:** https://ruralavisory.slack.com

---

**API Version 2.0.0 | Last Updated: 2024-01-15**
