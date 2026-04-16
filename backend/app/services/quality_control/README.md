# Quality Control Service

CLIP-based image scoring used to evaluate how well a generated image matches the original text prompt. This score drives the quality labels shown in the dashboard and is used to rank images before presenting them to the user.

---

## How It Works

[CLIP (Contrastive Language-Image Pretraining)](https://openai.com/research/clip) from OpenAI learns a shared embedding space for images and text. A higher cosine similarity between the two embeddings indicates stronger semantic alignment — i.e., the image looks like what the prompt described.

```
Image bytes  →  CLIP image encoder  →  image embedding (normalized)
                                                        ↘
                                              cosine similarity  →  score [0.0, 1.0]
                                                        ↗
Prompt text  →  CLIP text encoder   →  text embedding  (normalized)
```

The model used is `openai/clip-vit-base-patch32`, loaded from Hugging Face Transformers. It runs on GPU if available, otherwise CPU.

---

## File

`clip_scorer.py` — `ClipScorerService`

### `ClipScorerService`

Initialized once at app startup by the Flask app factory and stored in `app.extensions['clip_scorer']`.

#### `__init__()`

Loads the CLIP model and processor from Hugging Face. If loading fails (e.g., network or memory issue), the service sets `self.model = None` and degrades gracefully by returning `0.0` for all scores.

#### `calculate_score(image_bytes, prompt) → float`

| Argument | Type | Description |
|----------|------|-------------|
| `image_bytes` | `bytes` | Raw PNG/JPEG image data |
| `prompt` | `str` | The text prompt the image was generated from |

Returns a float in `[0.0, 1.0]`. Returns `0.0` if the model is not loaded or an error occurs.

> **Truncation**: CLIP's text encoder has a 77-token context limit. Prompts are truncated to 77 characters as a conservative safeguard.

---

## Score Interpretation

The frontend maps raw scores to quality labels using fixed thresholds calibrated for `clip-vit-base-patch32`:

| Score | Label | Meaning |
|-------|-------|---------|
| 0.0 or error | N/A | Scoring unavailable |
| < 0.24 | Low | Image likely missed the prompt |
| 0.24 – 0.29 | Medium | Acceptable alignment |
| ≥ 0.29 | High | Strong semantic match |

These thresholds are tighter than general CLIP guidance because the prompts in this pipeline are long and highly specific — scores tend to be lower than for short, simple captions.

---

## Integration

The `/api/evaluate-image` route calls `ClipScorerService.calculate_score()` for each generated image. The frontend then sorts the image grid by score descending so the best candidate appears first.
