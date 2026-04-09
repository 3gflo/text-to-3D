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
    def __init__(self, app_config):
        google_key = app_config.get('GOOGLE_KEY')
        openai_key = app_config.get('OPENAI_KEY')
        fal_key = app_config.get('FALAI_KEY')

        if fal_key:
            os.environ['FAL_KEY'] = fal_key

        self._services = {
            "imagen": Imagen(google_key) if google_key else MockImageGenerator(),
            "nano-banana": NanoBanana(google_key) if google_key else MockImageGenerator(),
            "gpt-image": GPT_image(openai_key) if openai_key else MockImageGenerator(),
        }

        # Internal reference-based generator used for side views only (not user-selectable)
        self._reference_generator = Flux2ProEdit() if fal_key else None

    def get_service(self, service_name):
        # Return requested service or Imagen as default
        return self._services.get(service_name.lower(), self._services["imagen"])

    def get_reference_generator(self):
        """Returns the Flux 2 Pro Edit instance used for generating side views from a front reference."""
        return self._reference_generator

    def get_services(self):
        return self._services

class BaseImageGenerator(ABC):
    @abstractmethod
    def generate(self, prompt: str, num_images: int = 1) -> list[bytes]:
        pass

    @property
    def supports_reference(self) -> bool:
        return False

    def generate_with_reference(self, prompt: str, reference_image: bytes) -> list[bytes]:
        """Generate an image using a text prompt and a reference image.
        Falls back to text-only generation by default."""
        return self.generate(prompt, num_images=1)

# Imagen-4.0
class Imagen(BaseImageGenerator):
    def __init__(self, api_key):
        self.client = genai.Client(
            api_key=api_key,
            http_options={'api_version': 'v1beta'}
        )
        self.model_name = 'imagen-4.0-generate-001'

    def generate(self, prompt: str, num_images: int = 1):
        try:
            response = self.client.models.generate_images(
                model='imagen-4.0-generate-001',
                prompt=prompt,
                config=types.GenerateImagesConfig(number_of_images=num_images)
                )
            if response.generated_images:
                return [img.image.image_bytes for img in response.generated_images]
        except Exception as e:
            print(f"imagen-4.0-generate-001 Error: {e}")
        return []

# Flux 2 Pro Edit (fal.ai)
class Flux2ProEdit(BaseImageGenerator):
    def __init__(self):
        self.model_endpoint = "fal-ai/flux-2-pro/edit"

    def generate(self, prompt: str, num_images: int = 1) -> list[bytes]:
        # Flux 2 Pro Edit requires input images — text-only generation not supported
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

# Nano-Banana-pro
class NanoBanana(BaseImageGenerator):
    def __init__(self, api_key):
        self.client = genai.Client(
            api_key = api_key,
            http_options={'api_version': 'v1beta'}
        )

        self.model_name = 'gemini-3-pro-image-preview'

    def generate(self, prompt: str, num_images: int = 1):
        try:
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_modalities=['IMAGE']
                )
            )
            images = []
            if response.candidates:
                for candidate in response.candidates:
                    for part in candidate.content.parts:
                        if part.inline_data:
                            images.append(part.inline_data.data)
            return images

        except Exception as e:
            print(f"Nano Banana Pro Error: {e}")
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
                config=types.GenerateContentConfig(
                    response_modalities=['IMAGE']
                )
            )
            images = []
            if response.candidates:
                for candidate in response.candidates:
                    for part in candidate.content.parts:
                        if part.inline_data:
                            images.append(part.inline_data.data)
            return images
        except Exception as e:
            print(f"Nano Banana Pro (with reference) Error: {e}")
        return []

# GPT-image-1.5
class GPT_image(BaseImageGenerator):
    def __init__(self, api_key):
        self.client = OpenAI(api_key=api_key)
        self.model_name = "gpt-image-1.5"

    def generate(self, prompt: str, num_images: int = 1):
        try:
            response = self.client.images.generate(
                model=self.model_name,
                prompt=prompt,
                n = num_images
                # size and quality omitted
            )
            images = []
            for item in response.data:
                if item.b64_json:
                    images.append(base64.b64decode(item.b64_json))

            return images

        except Exception as e:
            print(f"GPT-image-1.5 Error: {e}")
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
            images = []
            for item in response.data:
                if item.b64_json:
                    images.append(base64.b64decode(item.b64_json))
            return images
        except Exception as e:
            print(f"GPT-image-1.5 (with reference) Error: {e}")
        return []

# Used for testing in case an API key fails
class MockImageGenerator(BaseImageGenerator):
    def generate(self, prompt: str, num_images: int = 1):
        # Creates a 100x100 solid blue square
        img = Image.new('RGB', (100, 100), color='blue')
        img_byte_arr = io.BytesIO()
        img.save(img_byte_arr, format='PNG')
        bytes_data = img_byte_arr.getvalue()
        
        print(f"DEBUG: Mock Generator used for prompt: {prompt}")
        return [bytes_data] * num_images