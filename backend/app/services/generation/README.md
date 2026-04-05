# Generation Services

Three separate services that handle each stage of the AI generation pipeline: prompt optimization, 2D image generation, and 3D model generation. All three follow the same **Registry + Abstract Base Class** pattern for consistency and extensibility.

---

## Architecture Pattern

```
XServiceRegistry(app_config)
    ├── Reads API keys from config at startup
    ├── Initializes concrete service instances (or mocks if keys are missing)
    └── get_service(name) → service instance

BaseXGenerator (ABC)
    └── generate(...) → output          # enforced interface

ConcreteGenerator(BaseXGenerator)
    └── generate(...) → output          # API-specific implementation

MockXGenerator(BaseXGenerator)
    └── generate(...) → placeholder     # used when key is absent
```

Adding a new model means creating a new subclass of the relevant ABC and registering it in the registry's `_services` dict.

---

## Prompt Generation — `prompt_generator.py`

Converts a short user description into a structured, detailed prompt optimized for multi-view image generation and 3D reconstruction.

### System Instruction

The `SYSTEM_INSTRUCTION` constant defines a 4-layer prompt engineering framework used as the system prompt for every LLM call:

| Layer | Focus |
|-------|-------|
| WHAT | Single core subject |
| FORM | Shape and structural adjectives |
| MATERIAL | PBR surface descriptions (texture, reflectance, imperfections) |
| AESTHETICS | Artistic style and rendering genre |

The instruction also mandates specific lighting, background, quality markers, and a 4-view orthographic layout — all critical for downstream 3D reconstruction quality.

### Services

| Name | Class | Model |
|------|-------|-------|
| `gemini-2.5-flash` | `GeminiPromptGenerator` | Gemini 2.5 Flash (Google AI) |
| `gpt-oss` | `GPTOSSPromptGenerator` | GPT-OSS 20B via Hugging Face Inference API |
| *(fallback)* | `MockPromptGenerator` | Returns a hardcoded template prompt |

### Interface

```python
# Get a service by name (falls back to gemini-2.5-flash if name is unknown)
service = registry.get_service("gemini-2.5-flash")

# Generate an optimized prompt
optimized: str | None = service.generate("a dining chair")
```

---

## Image Generation — `image_generator.py`

Generates 2D concept images from a prompt. Always returns raw PNG bytes, regardless of the underlying provider.

### Services

| Name | Class | Model |
|------|-------|-------|
| `imagen` | `Imagen` | Imagen 4.0 (Google AI) |
| `nano-banana` | `NanoBanana` | Gemini 3 Pro (multi-modal content generation) |
| `gpt-image` | `GPT_image` | GPT-Image 1.5 (OpenAI) |
| *(fallback)* | `MockImageGenerator` | Returns a 100×100 solid blue PNG |

### Interface

```python
service = registry.get_service("imagen")

# Returns a list of raw PNG bytes, one per image
images: list[bytes] = service.generate(prompt, num_images=3)
```

The `/api/generate-image` route always requests 3 images and encodes each as a base64 data URI before sending to the frontend.

---

## 3D Model Generation — `threeD_generator.py`

Converts one or more 2D images into a `.glb` 3D mesh. All generators use the [fal.ai](https://fal.ai) platform as the inference backend.

### Services

| Name | Class | Model | Min. Images |
|------|-------|-------|-------------|
| `trellis` | `Trellis` | fal-ai/trellis/multi | 1 (auto-split) |
| `trellis-2` | `Trellis2` | fal-ai/trellis-2 | 1 (auto-split) |
| `hunyuan` | `Hunyuan` | fal-ai/hunyuan3d/v2/multi-view | 3 |
| `hunyuan-pro` | `HunyuanPro` | fal-ai/hunyuan-3d/v3.1/pro/image-to-3d | 1 |
| *(fallback)* | `Mock3DGenerator` | — | Returns a minimal GLB header |

### Orthographic Sheet Splitting

The image generation models produce a single 2×2 orthographic sheet (front, back, left, right). The `split_orthographic_sheet(sheet_bytes)` utility splits this into four individual view images, which are then passed to the 3D generator.

```
┌────────┬────────┐
│  Front │  Back  │
├────────┼────────┤
│  Left  │  Right │
└────────┴────────┘
```

This splitting happens automatically in the `/api/generate-3d-model` route when only one image is provided.

### Interface

```python
service = registry.get_service("trellis")

# Accepts a list of view images as raw bytes, returns GLB bytes
model_bytes: bytes | None = service.generate(image_bytes_list)
```

### Base Class Helpers

All generators inherit from `Base3DGenerator`, which provides:

| Method | Description |
|--------|-------------|
| `_bytes_to_data_uri(image_bytes)` | Encodes raw bytes as a `data:image/png;base64,...` URI for fal.ai |
| `_extract_url(result, service_name)` | Extracts the GLB download URL from varied fal.ai response shapes |
| `_download_file(url)` | Downloads the model file from a remote URL and returns raw bytes |
