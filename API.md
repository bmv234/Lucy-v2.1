# MeloTTS API Documentation

## Authentication

The API uses Bearer token authentication. Include your API key in the Authorization header:

```
Authorization: Bearer your_api_key_here
```

For testing, you can use:
- API Key: `test_key`

## Rate Limits

The API has the following rate limits:
- Voices endpoint: 30 requests per minute
- Synthesis endpoint: 20 requests per minute

## API Endpoints

### List Available Voices

Get a list of all available TTS voices.

**Endpoint:** `GET /api/v1/voices`

**Response:**
```json
{
    "success": true,
    "timestamp": "2023-07-20T12:00:00.000Z",
    "data": {
        "voices": [
            {
                "id": "EN-US",
                "name": "English (American)"
            },
            {
                "id": "EN-BR",
                "name": "English (British)"
            },
            {
                "id": "EN-IN",
                "name": "English (Indian)"
            },
            {
                "id": "EN-AU",
                "name": "English (Australian)"
            },
            {
                "id": "EN",
                "name": "English (Default)"
            },
            {
                "id": "ES",
                "name": "Spanish"
            },
            {
                "id": "FR",
                "name": "French"
            },
            {
                "id": "ZH",
                "name": "Chinese"
            },
            {
                "id": "JP",
                "name": "Japanese"
            },
            {
                "id": "KR",
                "name": "Korean"
            }
        ]
    }
}
```

### Synthesize Text to Speech

Convert text to speech audio.

**Endpoint:** `POST /api/v1/synthesize`

**Request Body:**
```json
{
    "text": "Text to convert to speech",
    "voice": "EN-US",  // Optional, defaults to "EN"
    "speed": 1.0       // Optional, defaults to 1.0
}
```

**Parameters:**
- `text` (required): The text to convert to speech
- `voice` (optional): Voice ID to use. Available options:
  - EN-US: English (American)
  - EN-BR: English (British)
  - EN-IN: English (Indian)
  - EN-AU: English (Australian)
  - EN: English (Default)
  - ES: Spanish
  - FR: French
  - ZH: Chinese
  - JP: Japanese
  - KR: Korean
- `speed` (optional): Speech speed multiplier (default: 1.0, range: 0.1-3.0)

**Response:**
- Content-Type: audio/wav
- The response will be the audio file in WAV format

## Error Responses

Error responses follow this format:
```json
{
    "success": false,
    "timestamp": "2023-07-20T12:00:00.000Z",
    "error": "Error message description"
}
```

## Example Usage

### Using cURL

List voices:
```bash
curl -X GET \
  'http://localhost:5050/api/v1/voices' \
  -H 'Authorization: Bearer test_key'
```

Synthesize speech (English):
```bash
curl -X POST \
  'http://localhost:5050/api/v1/synthesize' \
  -H 'Authorization: Bearer test_key' \
  -H 'Content-Type: application/json' \
  -d '{
    "text": "Hello world",
    "voice": "EN-US",
    "speed": 1.0
  }' \
  --output speech.wav
```

Synthesize speech (Spanish):
```bash
curl -X POST \
  'http://localhost:5050/api/v1/synthesize' \
  -H 'Authorization: Bearer test_key' \
  -H 'Content-Type: application/json' \
  -d '{
    "text": "Hola mundo",
    "voice": "ES",
    "speed": 1.0
  }' \
  --output speech.wav
```

### Using Python

```python
import requests

API_URL = "http://localhost:5050/api/v1"
API_KEY = "test_key"

headers = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json"
}

# List voices
response = requests.get(f"{API_URL}/voices", headers=headers)
voices = response.json()

# Synthesize speech
data = {
    "text": "Hello world",
    "voice": "EN-US",
    "speed": 1.0
}
response = requests.post(f"{API_URL}/synthesize", headers=headers, json=data)

# Save audio file
if response.status_code == 200:
    with open("output.wav", "wb") as f:
        f.write(response.content)
```

## Error Codes

- 400: Bad Request - Missing or invalid parameters
- 401: Unauthorized - Invalid or missing API key
- 429: Too Many Requests - Rate limit exceeded
- 500: Internal Server Error - Server-side error occurred

## Interactive Documentation

For interactive API testing and additional documentation:
- Swagger UI: http://localhost:5050/docs
- OpenAPI Specification: http://localhost:5050/api/swagger.json
