import base64
import io
from abc import ABC, abstractmethod

from PIL import Image
from google import genai
from google.genai import types
from openai import OpenAI


class ImageServiceRegistry:
    """Registry of available image generation services, keyed by model name."""

    def __init__(self, app_config: dict) -> None:
        google_key: str | None = app_config.get('GOOGLE_KEY')
        openai_key: str | None = app_config.get('OPENAI_KEY')

        self._services: dict[str, 'BaseImageGenerator'] = {
            "imagen": Imagen(google_key) if google_key else MockImageGenerator(),
            "nano-banana": NanoBanana(google_key) if google_key else MockImageGenerator(),
            "gpt-image": GPT_image(openai_key) if openai_key else MockImageGenerator(),
        }

    def get_service(self, service_name: str) -> 'BaseImageGenerator':
        return self._services.get(service_name.lower(), self._services["imagen"])

    def get_services(self) -> dict[str, 'BaseImageGenerator']:
        return self._services


class BaseImageGenerator(ABC):
    @abstractmethod
    def generate(self, prompt: str, num_images: int = 1) -> list[bytes]:
        """Generate images from a prompt and return raw PNG bytes for each."""
        pass


class Imagen(BaseImageGenerator):
    """Google Imagen 4.0 image generator."""

    def __init__(self, api_key: str) -> None:
        self.client = genai.Client(
            api_key=api_key,
            http_options={'api_version': 'v1beta'}
        )
        self.model_name = 'imagen-4.0-generate-001'

    def generate(self, prompt: str, num_images: int = 1) -> list[bytes]:
        try:
            response = self.client.models.generate_images(
                model=self.model_name,
                prompt=prompt,
                config=types.GenerateImagesConfig(number_of_images=num_images)
            )
            if response.generated_images:
                return [img.image.image_bytes for img in response.generated_images]
        except Exception as e:
            print(f"Imagen error: {e}")
        return []


class NanoBanana(BaseImageGenerator):
    """Gemini 3 Pro image generator (multi-modal content generation)."""

    def __init__(self, api_key: str) -> None:
        self.client = genai.Client(
            api_key=api_key,
            http_options={'api_version': 'v1beta'}
        )
        self.model_name = 'gemini-3-pro-image-preview'

    def generate(self, prompt: str, num_images: int = 1) -> list[bytes]:
        try:
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=prompt,
                config=types.GenerateContentConfig(response_modalities=['IMAGE'])
            )
            images: list[bytes] = []

            if not response.candidates:
                raise Exception("No images found")

            for candidate in response.candidates:
                for part in candidate.content.parts:
                    if part.inline_data:
                        images.append(part.inline_data.data)
            return images
        except Exception as e:
            print(f"NanoBanana error: {e}")
        return []


class GPT_image(BaseImageGenerator):
    """OpenAI GPT-Image 1.5 generator."""

    def __init__(self, api_key: str) -> None:
        self.client = OpenAI(api_key=api_key)
        self.model_name = "gpt-image-1.5"

    def generate(self, prompt: str, num_images: int = 1) -> list[bytes]:
        try:
            response = self.client.images.generate(
                model=self.model_name,
                prompt=prompt,
                n=num_images
            )
            return [base64.b64decode(item.b64_json) for item in response.data if item.b64_json]
        except Exception as e:
            print(f"GPT-image error: {e}")
        return []


class MockImageGenerator(BaseImageGenerator):
    """Fallback generator used when no API key is available. Returns a solid blue square."""

    def generate(self, prompt: str, num_images: int = 1) -> list[bytes]:
        # Creates a 100x100 solid blue square
        img = Image.new('RGB', (100, 100), color='blue')
        img_byte_arr = io.BytesIO()
        img.save(img_byte_arr, format='PNG')
        print(f"MockImageGenerator called for: {prompt}")
        return [img_byte_arr.getvalue()] * num_images
