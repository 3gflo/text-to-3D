from abc import ABC, abstractmethod
import io
import requests
from PIL import Image
from app.config import config
from google import genai
from google.genai import types
import base64
from openai import OpenAI

class ImageServiceRegistry:
    def __init__(self, app_config):
        google_key = app_config.get('GOOGLE_API_KEY')
        openai_key = app_config.get('OPENAI_API_KEY')

        self._services = {
            "imagen": ImagenGenerator(google_key) if google_key else MockImageGenerator(),
            "nano-banana": NanoBananaGenerator(google_key) if google_key else MockImageGenerator(),
            "openai": OpenAIGenerator(openai_key) if openai_key else MockImageGenerator(),
        }
    
    def get_service(self, service_name):
        # Return requested service or Imagen as default
        return self._services.get(service_name.lower(), self._services["imagen"])

class BaseImageGenerator(ABC):
    @abstractmethod
    def generate(self, prompt: str):
        pass

class ImagenGenerator(BaseImageGenerator):
    def __init__(self, api_key):
        self.client = genai.Client(
            api_key=api_key,
            http_options={'api_version': 'v1beta'}
        )
        self.model_name = 'imagen-4.0-generate-001'

    def generate(self, prompt: str):
        try:
            response = self.client.models.generate_images(
                model='imagen-4.0-generate-001',
                prompt=prompt,
                config=types.GenerateImagesConfig(number_of_images=1)
            )
            if response.generated_images:
                return response.generated_images[0].image.image_bytes
        except Exception as e:
            print(f"Imagen Error: {e}")
        return None


class NanoBananaGenerator(BaseImageGenerator):
    def __init__(self, api_key):
        self.client = genai.Client(
            api_key = api_key,
            http_options={'api_version': 'v1beta'}
        )

        self.model_name = 'gemini-2.5-flash-image'

    def generate(self, prompt: str):
        try:
            response = self.client.models.generate_images(
                model='imagen-4.0-generate-001',
                prompt=prompt,
                config=types.GenerateImagesConfig(number_of_images=1)
            )
            if response.generated_images:
                return response.generated_images[0].image.image_bytes
        except Exception as e:
            print(f"Nano Banana Error: {e}")
        return None

# GPT-image-1.5
class OpenAIGenerator(BaseImageGenerator):
    def __init__(self, api_key):
        self.client = OpenAI(api_key=api_key)
        self.model_name = "gpt-image-1.5"

    def generate(self, prompt: str):
        try:
            # 1. Request generation
            response = self.client.images.generate(
                model=self.model_name,
                prompt=prompt,
                n=1
                # size and quality omitted
            )
            
            # 2. Extract the temporary URL from the response
            image_base64 = response.data[0].b64_json
            
            # 3. Download the image into memory using BytesIO
            image_bytes = base64.b64decode(image_base64)
            
            return image_bytes
            
        except Exception as e:
            print(f"OpenAI Error: {e}")
        return None

# Used for testing in case an API key fails
class MockImageGenerator(BaseImageGenerator):
    def generate(self, prompt: str):
        # Create a simple 100x100 solid blue square in memory
        img = Image.new('RGB', (100, 100), color='blue')
        img_byte_arr = io.BytesIO()
        img.save(img_byte_arr, format='PNG')
        
        print(f"DEBUG: Mock Generator used for prompt: {prompt}")
        return img_byte_arr.getvalue()