# Backend

Flask REST API that drives the text-to-3D generation pipeline. All AI service calls, quality control logic, and data persistence are handled here. The frontend communicates with this server exclusively through the `/api` endpoints.

---

## Structure

```
backend/
├── app/
│   ├── __init__.py             # App factory — initializes services and registers blueprints
│   ├── config.py               # Config classes that load environment variables
│   ├── routes.py               # All API endpoint definitions
│   └── services/
│       ├── generation/         # Prompt, image, and 3D generation
│       │   ├── prompt_generator.py
│       │   ├── image_generator.py
│       │   └── threeD_generator.py
│       ├── quality_control/    # CLIP image scoring
│       │   └── clip_scorer.py
│       └── google_sheets_integration/  # Job logging to Google Sheets
│           ├── sheets_client.py
│           └── sheets_manager.py
├── test/
│   ├── test_3Dgen.py
│   └── test_sheets.py
├── run.py                      # Entry point — starts Flask on port 5055
└── requirements.txt
```

---

## Setup

### 1. Create and activate a virtual environment

```bash
python -m venv .venv
source .venv/bin/activate     # Windows: .venv\Scripts\activate
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure environment variables

Create a `.env` file in this directory:

```env
GOOGLE_KEY=your_google_ai_api_key
OPENAI_KEY=your_openai_api_key
FALAI_KEY=your_fal_ai_api_key
HF_TOKEN=your_huggingface_token
GOOGLE_SHEETS_CREDENTIALS_PATH=/path/to/credentials.json
GOOGLE_SHEET_ID=your_google_sheet_id
```

> If `GOOGLE_SHEETS_CREDENTIALS_PATH` is not set, the server starts a no-op `MockSheetManager` instead and logs a warning. All other features remain fully functional.

### 4. Start the server

```bash
python run.py
```

The API is served at `http://0.0.0.0:5055`. The frontend Vite dev server proxies `/api` requests here automatically.

---

## API Reference

### `GET /api/health`
Returns `{ "status": "healthy" }`. Used to verify the server is reachable.

---

### `POST /api/available-models`
Returns the registered service names for a given pipeline stage.

**Request**
```json
{ "asset_type": "text" | "image" | "3D" }
```

**Response**
```json
{ "services": ["gemini-2.5-flash", "gpt-oss"] }
```

---

### `POST /api/optimize-prompt`
Passes a short user description through an LLM prompt engineer to produce a detailed, multi-view image generation prompt.

**Request**
```json
{
  "prompt": "a dining chair",
  "service": "gemini-2.5-flash"
}
```

**Response**
```json
{
  "success": true,
  "original_prompt": "a dining chair",
  "optimized_prompt": "A hyperrealistic CG render of ...",
  "service": "gemini-2.5-flash"
}
```

---

### `POST /api/generate-image`
Generates 3 images from the provided prompt using the selected image model.

**Request**
```json
{
  "optimized_prompt": "A hyperrealistic CG render of ...",
  "service": "imagen"
}
```

**Response**
```json
{
  "status": "success",
  "images": ["data:image/png;base64,...", "..."],
  "count": 3
}
```

---

### `POST /api/evaluate-image`
Scores each image against the prompt using CLIP cosine similarity. Returns values in `[0.0, 1.0]`.

**Request**
```json
{
  "images": ["data:image/png;base64,..."],
  "prompt": "a dining chair"
}
```

**Response**
```json
{
  "status": "success",
  "evaluations": [{ "score": 0.2843 }, { "score": 0.3012 }, { "score": 0.2201 }]
}
```

---

### `POST /api/generate-3d-model`
Converts one or more images into a GLB 3D model. A single image is automatically split into 4 orthographic views before being sent to the generator.

**Request**
```json
{
  "images": ["data:image/png;base64,..."],
  "service": "trellis"
}
```

**Response**: Binary GLB file (`model/gltf-binary`)

---

### `POST /api/convert-model`
Converts a GLB file to OBJ format. Textured models are returned as a ZIP archive.

**Request**: `multipart/form-data` with fields `model_file` (GLB binary) and `format` (`"obj"`).

**Response**: ZIP archive or plain OBJ file.

---

### `POST /api/analyze-discrepancies`
Uses Gemini to visually compare the 2D concept image against a snapshot of the generated 3D model. Returns a short analysis and a re-optimized prompt for the next run.

**Request**
```json
{
  "original_prompt": "a dining chair",
  "input_images": ["data:image/png;base64,..."],
  "model_snapshots": ["data:image/png;base64,..."]
}
```

**Response**
```json
{
  "status": "success",
  "analysis": "The 3D model is missing the armrests present in the concept image...",
  "suggested_prompt": "A dining chair with clearly defined wooden armrests..."
}
```

---

### `POST /api/save-job`
Persists the metadata from a completed generation run to Google Sheets.

**Request**
```json
{
  "user": "Jesse",
  "description": "Testing Trellis with Imagen",
  "input_prompt": "a dining chair",
  "text_model": "gemini-2.5-flash",
  "optimized_prompt": "...",
  "image_model": "imagen",
  "three_d_model": "trellis",
  "analysis": "..."
}
```

**Response**
```json
{ "status": "success" }
```

---

## Service Architecture

Each pipeline stage follows the same **Registry + ABC** pattern:

```
ServiceRegistry
    └── get_service(name) → ConcreteService | MockService
            └── generate(...) → output bytes
```

The registry reads available API keys at startup and swaps in a mock implementation for any service whose key is missing. This means the application always starts without errors regardless of which credentials are configured.

See the individual service READMEs for details:
- [`services/generation/`](app/services/generation/README.md)
- [`services/quality_control/`](app/services/quality_control/README.md)
- [`services/google_sheets_integration/`](app/services/google_sheets_integration/README.md)
