# Image Realism Enhancement Engine

A FastAPI service that analyzes images for AI-generated artifacts and produces structured JSON instructions for enhancing perceived realism via downstream image models.

## Architecture

```
API Gateway
 |
 |-- Image Upload
 |
 |-- Scene Classifier (Vision)
 |
 |-- LLM Orchestrator
 |      |
 |      |-- RAG (Real Photo Knowledge)
 |      |-- Strategy Generator
 |
 |-- Image Enhancement Pipeline
 |      |
 |      |-- Lighting Module
 |      |-- Texture Module
 |      |-- Noise Module
 |
 |-- Realism Scorer
 |
Result JSON
```

## Pipeline Stages

1. **Scene Classifier**: Analyzes the image to classify scene type and estimate AI-generation likelihood
2. **Fake Signal Detector**: Identifies common AI artifacts (over-uniformity, symmetry, clean edges, etc.)
3. **RAG Module**: Retrieves realism constraints based on scene type
4. **Strategy Generator**: Creates enhancement strategy with specific operations
5. **Execution Planner**: Translates strategy into module-specific instructions
6. **Realism Scorer**: Estimates realism improvement

## Installation

1. Clone the repository and navigate to the project directory:

```bash
cd realism
```

2. Create a virtual environment:

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:

```bash
pip install -r requirements.txt
```

4. Configure environment variables:

```bash
cp .env.example .env
# Edit .env with your API credentials
```

## Configuration

Edit the `.env` file with your settings:

```env
# Meitu Model Router Configuration
LLM_BASE_URL=https://model-router.meitu.com/v1
LLM_API_KEY=your_api_key_here
LLM_MODEL=qwen-turbo
LLM_VISION_MODEL=qwen-vl-plus

# MHC 生图/改图（与 test_minimal 方式一致：runAsync + queryResult）
MHC_APP=
MHC_BIZ=
MHC_REGION=
MHC_ENV=
MHC_API_PATH=


# Application Settings
MAX_IMAGE_SIZE=10485760
STORAGE_PATH=./storage
```

## Running the Service

Start the server:

```bash
python -m app.main
```

Or with uvicorn directly:

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

The API will be available at `http://localhost:8000`.

## API Endpoints

### Health Check

```http
GET /health
```

Returns service health status.

### Upload Image

```http
POST /upload
Content-Type: multipart/form-data

file: <image_file>
```

Returns:
```json
{
  "job_id": "uuid",
  "message": "Image uploaded successfully"
}
```

### Process Image

```http
POST /process/{job_id}
```

Starts processing the uploaded image. Returns immediately with status.

### Get Result

```http
GET /result/{job_id}
```

Returns the processing result:

```json
{
  "job_id": "uuid",
  "status": "completed",
  "result": {
    "scene_classification": {...},
    "fake_signals": [...],
    "realism_constraints": {...},
    "strategy": {...},
    "execution_plan": {...},
    "realism_score": {...}
  }
}
```

### Synchronous Analysis

```http
POST /analyze
Content-Type: multipart/form-data

file: <image_file>
```

Combines upload and processing in a single call. Returns the full pipeline result.

## Output Format

The pipeline returns a structured JSON with all analysis stages:

```json
{
  "scene_classification": {
    "primary_scene": "portrait",
    "secondary_attributes": ["studio lighting", "shallow depth of field"],
    "ai_likelihood": 0.75
  },
  "fake_signals": [
    {
      "signal": "Over-smooth skin texture lacking pores",
      "severity": "medium"
    }
  ],
  "realism_constraints": {
    "scene_rules": ["Skin should have subtle texture variations"],
    "avoid_patterns": ["Perfectly smooth skin without pores"]
  },
  "strategy": {
    "goal": "Reduce synthetic skin appearance",
    "priority": "low",
    "operations": [
      {
        "module": "texture",
        "action": "Add subtle skin pore detail",
        "strength": "low",
        "locality": "local"
      }
    ],
    "constraints": ["Preserve facial identity", "Maintain overall composition"]
  },
  "execution_plan": {
    "lighting_module": [],
    "texture_module": [
      {
        "action": "Add subtle skin pore detail",
        "parameters": {...},
        "target_region": "auto_detect"
      }
    ],
    "noise_module": []
  },
  "realism_score": {
    "before": 0.45,
    "after": 0.58,
    "confidence": 0.8,
    "notes": "Image shows moderate AI-generated characteristics..."
  }
}
```

## Global Principles

The engine enforces these principles:

1. **Preserve identity**: Never alter the identity, composition, or intent of the original image
2. **Reduce AI perfection**: Introduce real-world imperfections to reduce synthetic appearance
3. **Avoid stylization**: No cinematic, stylized, or aesthetic exaggeration
4. **Subtle changes**: Prefer subtle, local, and physically plausible modifications
5. **No person imitation**: Never imitate a specific real person
6. **No identity inference**: Never describe or infer identity

## Project Structure

```
realism/
├── app/
│   ├── __init__.py
│   ├── main.py                 # FastAPI entry point
│   ├── config.py               # Settings management
│   ├── models/
│   │   └── schemas.py          # Pydantic models
│   ├── api/
│   │   └── routes.py           # API endpoints
│   ├── pipeline/
│   │   ├── orchestrator.py     # Pipeline coordinator
│   │   ├── scene_classifier.py # Stage 1
│   │   ├── fake_detector.py    # Stage 2
│   │   ├── rag_module.py       # Stage 3
│   │   ├── strategy_gen.py     # Stage 4
│   │   ├── execution_plan.py   # Stage 5
│   │   └── realism_scorer.py   # Stage 6
│   └── services/
│       ├── llm_client.py       # LLM API client
│       └── image_model.py      # Image model client
├── knowledge/
│   └── scene_rules.json        # RAG knowledge base
├── requirements.txt
├── .env.example
└── README.md
```

## Extending the Knowledge Base

Edit `knowledge/scene_rules.json` to add or modify realism rules for different scene types:

```json
{
  "new_scene_type": {
    "scene_rules": [
      "Rule 1 for realistic appearance",
      "Rule 2 for realistic appearance"
    ],
    "avoid_patterns": [
      "Pattern to avoid 1",
      "Pattern to avoid 2"
    ]
  }
}
```

## License

MIT License
