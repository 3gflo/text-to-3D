# Gulfstream Text to 3D Model Generator

An end-to-end AI pipeline that converts a plain-text description into a 3D model asset. The system chains prompt optimization, multi-view 2D image generation, CLIP-based quality control, and 3D reconstruction into a single browser-driven workflow.

Built as a senior capstone project for the University of Georgia in partnership with Gulfstream Aerospace.

---

## Pipeline Overview

```
User Text Input
      │
      ▼
 LLM Prompt Optimizer  (Gemini / GPT-OSS)
      │  Structured multi-view prompt
      ▼
 2D Image Generator    (Imagen 4.0 / NanoBanana / GPT-Image 1.5)
      │  Front view → back/left/right generated in parallel using front as reference
      ▼
 CLIP Quality Filter   (ViT-B/32 cosine similarity)
      │  Scored & ranked images
      ▼
 3D Model Generator    (Trellis / Trellis-2 / Hunyuan / HunyuanPro via fal.ai)
      │  GLB file
      ▼
 Discrepancy Analyzer  (Gemini VLM comparison)
      │  Suggested re-prompt
      ▼
 Google Sheets + Drive Logger  (Job metadata and asset persistence)
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
│   │       └── google_sheets_integration/  # Sheets & Drive persistence layer
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
GOOGLE_SHEET_ID=your_google_sheet_id
DRIVE_FOLDER_ID=your_drive_folder_id
```

> Google Sheets and Drive integration is optional. The server falls back to no-op mocks if credentials are absent.
>
> `DRIVE_FOLDER_ID` is optional even when credentials are present — uploaded files will land in the root of the Drive if it is unset.

### 2. Start the backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python run.py
```

The API will be available at `http://localhost:5055`.

On the first run with credentials configured, a browser window will open for Google OAuth authorization. The resulting token is cached in `token.json` and reused on subsequent runs.

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
| `POST` | `/api/generate-image` | Generate multi-view 2D images (front first, remaining in parallel) |
| `POST` | `/api/regenerate-view` | Regenerate a single viewpoint image, optionally with user feedback |
| `POST` | `/api/evaluate-image` | Score images against a prompt using CLIP |
| `POST` | `/api/generate-3d-model` | Convert images to a GLB 3D model |
| `POST` | `/api/convert-model` | Convert a GLB to OBJ (returned as ZIP with textures) |
| `POST` | `/api/analyze-discrepancies` | Compare 2D concept to 3D output via Gemini VLM |
| `POST` | `/api/save-job` | Upload assets to Google Drive and persist job metadata to Sheets |

---

## External Services & API Keys

| Key | Service | Used For |
|-----|---------|----------|
| `GOOGLE_KEY` | Google AI (Gemini, Imagen) | Prompt optimization, image generation, discrepancy analysis |
| `OPENAI_KEY` | OpenAI | GPT-Image 1.5 image generation |
| `FALAI_KEY` | fal.ai | Trellis and Hunyuan 3D model generation |
| `HF_TOKEN` | Hugging Face | GPT-OSS prompt optimization |
| `DRIVE_FOLDER_ID` | Google Drive | Target folder for uploaded images and models |

All services degrade gracefully to mocks when their key is missing, so the application remains runnable for development without a full set of credentials.
