# Gulfstream Text to 3D Model Generator

An end-to-end AI pipeline that converts a plain-text description into a 3D model asset. The system chains prompt optimization, 2D image generation, CLIP-based quality control, and 3D reconstruction into a single browser-driven workflow.

Built as a senior capstone project for the University of Georgia in partnership with Gulfstream Aerospace.

---

## Pipeline Overview

```
User Text Input
      │
      ▼
 LLM Prompt Optimizer  (Gemini 2.5 Flash / GPT-OSS)
      │  Structured multi-view prompt
      ▼
 2D Image Generator    (Imagen 4.0 / NanaBanana / GPT-Image 1.5)
      │  3 candidate images
      ▼
 CLIP Quality Filter   (ViT-B/32 cosine similarity)
      │  Scored & ranked images
      ▼
 3D Model Generator    (Trellis / Trellis-2 / Hunyuan / HunyuanPro via fal.ai)
      │  GLB file
      ▼
 Discrepancy Analyzer  (Gemini 2.5 Flash VLM comparison)
      │  Suggested re-prompt
      ▼
 Google Sheets Logger  (Job metadata persistence)
```

---

## Repository Structure

```
text-to-3D-generation/
├── backend/                        # Flask API server
│   ├── app/
│   │   ├── __init__.py             # App factory & service initialization
│   │   ├── config.py               # Environment variable configuration
│   │   ├── routes.py               # REST API endpoints
│   │   └── services/
│   │       ├── generation/         # Prompt, image, and 3D generation services
│   │       ├── quality_control/    # CLIP scoring service
│   │       └── google_sheets_integration/  # Sheets persistence layer
│   ├── test/                       # Backend unit tests
│   ├── run.py                      # Flask entry point (port 5055)
│   └── requirements.txt
│
├── frontend/                       # React + Vite application
│   ├── src/
│   │   ├── App.jsx                 # Page router (Landing ↔ Dashboard)
│   │   ├── main.jsx                # React root
│   │   └── components/
│   │       ├── Dashboard.jsx       # Main application UI
│   │       └── LandingPage.jsx     # Welcome/intro page
│   ├── vite.config.js              # Vite config + /api proxy to Flask
│   └── package.json
│
├── legacy/                         # Pre-refactor scripts (reference only)
└── docs/                           # UML and architecture diagrams
```

---

## Quickstart

### Prerequisites

- Python 3.11+
- Node.js 18+ and npm

### 1. Configure environment variables

Create `backend/.env`:

```env
GOOGLE_KEY=your_google_ai_api_key
OPENAI_KEY=your_openai_api_key
FALAI_KEY=your_fal_ai_api_key
HF_TOKEN=your_huggingface_token
GOOGLE_SHEETS_CREDENTIALS_PATH=/path/to/credentials.json
GOOGLE_SHEET_ID=your_google_sheet_id
```

> Google Sheets logging is optional. The server falls back to a no-op mock if credentials are absent.

### 2. Start the backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python run.py
```

The API will be available at `http://localhost:5055`.

### 3. Start the frontend

In a separate terminal:

```bash
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173` in your browser. The Vite dev server proxies all `/api` requests to the Flask backend automatically.

---

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/health` | Server health check |
| `POST` | `/api/available-models` | List registered services for a given asset type |
| `POST` | `/api/optimize-prompt` | Optimize a user prompt via LLM |
| `POST` | `/api/generate-image` | Generate 2D images from an optimized prompt |
| `POST` | `/api/evaluate-image` | Score images against a prompt using CLIP |
| `POST` | `/api/generate-3d-model` | Convert images to a GLB 3D model |
| `POST` | `/api/convert-model` | Convert a GLB to OBJ (returned as ZIP with textures) |
| `POST` | `/api/analyze-discrepancies` | Compare 2D concept to 3D output via Gemini VLM |
| `POST` | `/api/save-job` | Persist job metadata to Google Sheets |

---

## External Services & API Keys

| Key | Service | Used For |
|-----|---------|----------|
| `GOOGLE_KEY` | Google AI (Gemini, Imagen) | Prompt optimization, image generation, discrepancy analysis |
| `OPENAI_KEY` | OpenAI | GPT-Image 1.5 image generation |
| `FALAI_KEY` | fal.ai | Trellis and Hunyuan 3D model generation |
| `HF_TOKEN` | Hugging Face | GPT-OSS prompt optimization |
| `GOOGLE_SHEETS_CREDENTIALS_PATH` | Google Cloud | Sheets API service account |

All services degrade gracefully to mocks when their key is missing, so the application remains runnable for development without a full set of credentials.
