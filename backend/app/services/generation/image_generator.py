import base64
import io
import os
from abc import ABC, abstractmethod

import fal_client
import requests
from PIL import Image
from google import genai
from google.genai import types
from openai import OpenAI


class ImageServiceRegistry:
    """Registry of available image generation services, keyed by model name."""

    def __init__(self, app_config: dict) -> None:
        google_key: str | None = app_config.get('GOOGLE_KEY')
        openai_key: str | None = app_config.get('OPENAI_KEY')
        fal_key: str | None = app_config.get('FALAI_KEY')

        if fal_key:
            os.environ['FAL_KEY'] = fal_key

        self._services: dict[str, 'BaseImageGenerator'] = {
            "imagen": Imagen(google_key) if google_key else MockImageGenerator(),
            "nano-banana": NanoBanana(google_key) if google_key else MockImageGenerator(),
            "gpt-image": GPT_image(openai_key) if openai_key else MockImageGenerator(),
        }

        # Internal reference-based generator used for side views only (not user-selectable)
        self._reference_generator = Flux2ProEdit() if fal_key else None

    def get_service(self, service_name: str) -> 'BaseImageGenerator':
        return self._services.get(service_name.lower(), self._services["imagen"])

    def get_reference_generator(self) -> 'Flux2ProEdit | None':
        """Returns the Flux 2 Pro Edit instance used for generating side views from a front reference."""
        return self._reference_generator

    def get_services(self) -> dict[str, 'BaseImageGenerator']:
        return self._services


class BaseImageGenerator(ABC):
    @abstractmethod
    def generate(self, prompt: str, num_images: int = 1) -> list[bytes]:
        """Generate images from a prompt and return raw PNG bytes for each."""
        pass

    @property
    def supports_reference(self) -> bool:
        return False

    def generate_with_reference(self, prompt: str, reference_image: bytes) -> list[bytes]:
        """Generate an image using a text prompt and a reference image.
        Falls back to text-only generation by default."""
        return self.generate(prompt, num_images=1)


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


class Flux2ProEdit(BaseImageGenerator):
    """Flux 2 Pro Edit (fal.ai) - reference-based image editing model."""

    def __init__(self) -> None:
        self.model_endpoint = "fal-ai/flux-2-pro/edit"

    def generate(self, prompt: str, num_images: int = 1) -> list[bytes]:
        # Flux 2 Pro Edit requires input images -- text-only generation not supported
        print("Flux 2 Pro Edit requires a reference image. Use generate_with_reference() instead.")
        return []

    @property
    def supports_reference(self) -> bool:
        return True

    def generate_with_reference(self, prompt: str, reference_image: bytes) -> list[bytes]:
        try:
            b64_str = base64.b64encode(reference_image).decode('utf-8')
            data_uri = f"data:image/png;base64,{b64_str}"

            result = fal_client.subscribe(
                self.model_endpoint,
                arguments={
                    "prompt": prompt,
                    "image_urls": [data_uri],
                    "output_format": "png"
                }
            )

            images = []
            if result and 'images' in result:
                for img_info in result['images']:
                    url = img_info.get('url')
                    if url:
                        resp = requests.get(url)
                        resp.raise_for_status()
                        images.append(resp.content)
            return images

        except Exception as e:
            print(f"Flux 2 Pro Edit Error: {e}")
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

    @property
    def supports_reference(self) -> bool:
        return True

    def generate_with_reference(self, prompt: str, reference_image: bytes) -> list[bytes]:
        try:
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=[
                    types.Part.from_bytes(data=reference_image, mime_type='image/png'),
                    prompt
                ],
                config=types.GenerateContentConfig(response_modalities=['IMAGE'])
            )
            images = []
            if response.candidates:
                for candidate in response.candidates:
                    for part in candidate.content.parts:
                        if part.inline_data:
                            images.append(part.inline_data.data)
            return images
        except Exception as e:
            print(f"NanoBanana (with reference) Error: {e}")
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

    @property
    def supports_reference(self) -> bool:
        return True

    def generate_with_reference(self, prompt: str, reference_image: bytes) -> list[bytes]:
        try:
            image_file = io.BytesIO(reference_image)
            image_file.name = "reference.png"
            response = self.client.images.edit(
                model=self.model_name,
                image=image_file,
                prompt=prompt,
            )
            return [base64.b64decode(item.b64_json) for item in response.data if item.b64_json]
        except Exception as e:
            print(f"GPT-image (with reference) Error: {e}")
        return []


class MockImageGenerator(BaseImageGenerator):
    """Fallback generator used when no API key is available. Returns a solid blue square."""

    def generate(self, prompt: str, num_images: int = 1) -> list[bytes]:
        img = Image.new('RGB', (100, 100), color='blue')
        img_byte_arr = io.BytesIO()
        img.save(img_byte_arr, format='PNG')
        print(f"MockImageGenerator called for: {prompt}")
        return [img_byte_arr.getvalue()] * num_images
