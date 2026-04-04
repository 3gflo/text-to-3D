import torch
from PIL import Image
from transformers import CLIPProcessor, CLIPModel
import io


class ClipScorerService:
    """
    Evaluates image-prompt alignment using OpenAI's CLIP ViT model.

    Computes cosine similarity between image and text embeddings, returning
    a score in [0.0, 1.0]. Higher scores indicate better semantic alignment.
    """

    def __init__(self) -> None:
        self.model_id = "openai/clip-vit-base-patch32"

        try:
            self.device = "cuda" if torch.cuda.is_available() else "cpu"
            print(f"Loading CLIP model on: {self.device}")
            self.model = CLIPModel.from_pretrained(self.model_id).to(self.device)
            self.processor = CLIPProcessor.from_pretrained(self.model_id)
            print("CLIP model loaded.")
        except Exception as e:
            print(f"Failed to load CLIP model: {e}")
            self.model = None
            self.processor = None

    def calculate_score(self, image_bytes: bytes, prompt: str) -> float:
        """
        Calculate the CLIP cosine similarity between an image and a text prompt.

        The prompt is truncated to 77 tokens to stay within CLIP's context limit.
        Returns 0.0 if the model failed to load or an error occurs during scoring.
        """
        if not self.model or not self.processor:
            print("CLIP model not loaded — returning 0.0.")
            return 0.0

        try:
            image = Image.open(io.BytesIO(image_bytes))
            truncated_prompt = prompt[:77]

            inputs = self.processor(
                text=[truncated_prompt],
                images=image,
                return_tensors="pt",
                padding=True
            ).to(self.device)

            with torch.no_grad():
                outputs = self.model(**inputs)

            image_embeds = outputs.image_embeds / outputs.image_embeds.norm(dim=-1, keepdim=True)
            text_embeds = outputs.text_embeds / outputs.text_embeds.norm(dim=-1, keepdim=True)

            similarity: float = (image_embeds @ text_embeds.T).item()
            return round(similarity, 4)

        except Exception as e:
            print(f"CLIP scoring error: {e}")
            return 0.0
