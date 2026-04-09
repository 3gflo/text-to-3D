import torch
from PIL import Image
from transformers import CLIPProcessor, CLIPModel
import io

class ClipScorerService:
    def __init__(self):
        print("--- Initializing CLIP Scorer Service ---")
        self.model_id = "openai/clip-vit-base-patch32"
        
        try:
            self.device = "cuda" if torch.cuda.is_available() else "cpu"
            print(f"Loading CLIP model onto: {self.device}")
            self.model = CLIPModel.from_pretrained(self.model_id).to(self.device)
            self.processor = CLIPProcessor.from_pretrained(self.model_id)
            print("CLIP model loaded successfully.")
        except Exception as e:
            print(f"Error loading CLIP model: {e}")
            self.model = None
            self.processor = None

    def calculate_score(self, image_bytes: bytes, prompt: str) -> float:
        if not self.model or not self.processor:
            print("CLIP model not loaded. Returning 0.0.")
            return 0.0

        try:
            image = Image.open(io.BytesIO(image_bytes))
            
            # Truncate prompt if too long to avoid token errors
            processed_prompt = prompt[:77] 

            inputs = self.processor(
                text=[processed_prompt], 
                images=image, 
                return_tensors="pt", 
                padding=True
            ).to(self.device)

            with torch.no_grad():
                outputs = self.model(**inputs)
            
            image_embeds = outputs.image_embeds / outputs.image_embeds.norm(dim=-1, keepdim=True)
            text_embeds = outputs.text_embeds / outputs.text_embeds.norm(dim=-1, keepdim=True)
            
            raw_similarity = (image_embeds @ text_embeds.T).item()

            # Rescale from typical CLIP cosine similarity range (~0.15–0.40)
            # to a more intuitive 0–1 scale
            min_clip = 0.15
            max_clip = 0.40
            scaled = (raw_similarity - min_clip) / (max_clip - min_clip)
            scaled = max(0.0, min(1.0, scaled))

            return round(scaled, 4)
            
        except Exception as e:
            print(f"Error calculating CLIP score: {e}")
            return 0.0