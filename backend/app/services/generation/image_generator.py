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
            #"imagen": ImagenGenerator(google_key) if google_key else MockImageGenerator(),
            #"nano-banana": NanoBananaGenerator(google_key) if google_key else MockImageGenerator(),
            #"openai": OpenAIGenerator(openai_key) if openai_key else MockImageGenerator(),
        }
    
    def get_service(self, service_name):
        # Return requested service or Imagen as default
        return self._services.get(service_name.lower(), self._services["imagen"])

class BaseImageGenerator(ABC):
    @abstractmethod
    def generate(self, prompt: str):
        pass

# Used for testing in case an API key fails
class MockImageGenerator(BaseImageGenerator):
    def generate(self, prompt: str):
        # Create a simple 100x100 solid blue square in memory
        img = Image.new('RGB', (100, 100), color='blue')
        img_byte_arr = io.BytesIO()
        img.save(img_byte_arr, format='PNG')
        
        print(f"DEBUG: Mock Generator used for prompt: {prompt}")
        return img_byte_arr.getvalue()