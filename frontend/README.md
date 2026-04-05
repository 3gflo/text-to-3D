# Frontend

React + Vite single-page application for the text-to-3D generation pipeline. The UI is a three-column dashboard that walks a user through prompt engineering, image selection, and 3D model generation. All AI work is handled by the Flask backend; the frontend communicates with it via fetch calls proxied through Vite.

---

## Structure

```
frontend/
├── src/
│   ├── main.jsx                # React root — mounts <App /> into #root
│   ├── App.jsx                 # Page router (landing ↔ dashboard)
│   └── components/
│       ├── LandingPage.jsx     # Welcome page with pipeline overview
│       ├── LandingPage.css
│       ├── Dashboard.jsx       # Main application (prompt → image → 3D)
│       └── Dashboard.css
├── index.html
├── vite.config.js              # Dev server + /api proxy to Flask on port 5055
├── eslint.config.js
└── package.json
```

---

## Setup

### Prerequisites

Node.js 18+ and npm.

### Install dependencies

```bash
npm install
```

### Start the dev server

```bash
npm run dev
```

Open `http://localhost:5173`. The Vite dev server automatically proxies any request beginning with `/api` to the Flask backend at `http://127.0.0.1:5055`, so no CORS configuration is needed during development.

> Start the backend before the frontend. The frontend fetches the available model list on mount, and will log warnings to the console if the backend is unreachable.

### Other scripts

| Command | Description |
|---------|-------------|
| `npm run dev` | Start Vite dev server with hot reload |
| `npm run build` | Production build to `dist/` |
| `npm run preview` | Serve the production build locally |
| `npm run lint` | Run ESLint |

---

## Component Overview

### `App.jsx`

Minimal router that conditionally renders either `LandingPage` or `Dashboard` based on a `currentPage` state string. Passing `onStart` down to `LandingPage` is the only way to transition between pages.

### `LandingPage.jsx`

Static welcome screen. Shows the four-step pipeline diagram (Text → Image → CLIP → 3D) and a "Start Generating Now" button that triggers the `onStart` callback from `App`.

### `Dashboard.jsx`

The core of the application. Renders three columns and manages the full generation workflow through a set of `useState` hooks and `fetch`-based handler functions.

**Columns:**

| Column | Purpose |
|--------|---------|
| Input | Prompt entry, LLM model selection, prompt optimization, image model selection, batch image generation |
| Processing | CLIP-scored image grid (or manual upload in manual mode) — click to select an image for 3D generation |
| Output | 3D model selector, generation trigger, `<model-viewer>` preview, discrepancy analysis, format download, job save |

**Key handlers:**

| Handler | Description |
|---------|-------------|
| `handleOptimizePrompt` | Sends the input prompt to `/api/optimize-prompt` |
| `handleGenerateImages` | Calls `/api/generate-image`, then `/api/evaluate-image` for CLIP scoring; sorts results by score |
| `handleGenerate3DAsset` | Calls `/api/generate-3d-model` and loads the GLB into `<model-viewer>` |
| `handleDownloadModel` | GLB: direct blob download. OBJ: sends to `/api/convert-model` and downloads the returned ZIP |
| `handleAnalyzeDiscrepancies` | Captures a `<model-viewer>` snapshot and sends it with the 2D image to `/api/analyze-discrepancies` |
| `handleSaveJob` | Posts job metadata to `/api/save-job` and resets 3D state for the next run |

**Modes:**

- **Text to Image mode** (default): Full pipeline — optimize prompt → generate images → select → generate 3D.
- **Manual Upload mode**: Skip prompt optimization and image generation; upload a local image directly to the 3D generator.

**CLIP score labels** (calibrated for `clip-vit-base-patch32`):

| Score range | Label |
|-------------|-------|
| < 0.24 | Low |
| 0.24 – 0.29 | Medium |
| ≥ 0.29 | High |

---

## Dependencies

| Package | Version | Purpose |
|---------|---------|---------|
| `react` | ^19.2 | UI framework |
| `react-dom` | ^19.2 | DOM renderer |
| `@google/model-viewer` | ^4.1 | Web component for interactive 3D GLB preview |
| `vite` | ^7.2 | Build tool and dev server |
| `@vitejs/plugin-react` | ^5.1 | Vite plugin for React JSX transform |
