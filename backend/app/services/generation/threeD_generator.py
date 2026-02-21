import os
import base64
import fal_client
from abc import ABC, abstractmethod
import requests

class ThreeDServiceRegistry:
    def __init__(self, app_config):
        fal_key = app_config.get('FALAI_KEY')

        if fal_key:
            os.environ['FAL_KEY'] = fal_key
        
        self._services = {
            "trellis": Trellis() if fal_key else Mock3DGenerator(),
            "hunyuan": Hunyuan() if fal_key else Mock3DGenerator(),
        }
    
    def get_service(self, service_name):
        # Return requested service or Trellis as default
        return self._services.get(service_name.lower(), self._services["trellis"])

    def get_services(self):
        return self._services

class Base3DGenerator(ABC):
    @abstractmethod
    def generate(self, images: list[bytes]) -> bytes:
        """
        Accepts a list of image bytes (from the image_generator service)
        and returns the 3D model file as bytes (usually .glb).
        """
        pass
    
    # Helper to convert raw bytes to a base64 data URI for fal.ai.
    def _bytes_to_data_uri(self, image_bytes: bytes, mime_type: str = "image/png") -> str:
        base64_str = base64.b64encode(image_bytes).decode('utf-8')
        return f"data:{mime_type};base64,{base64_str}"
    
    # Robustly extracts the GLB URL from various fal.ai response formats.
    def _extract_url(self, result, service_name):
        # Handle different response structures
        if 'model_mesh' in result:
             return result['model_mesh']['url']
        if 'model_glb' in result: # Trellis 2 often uses this key
             return result['model_glb']['url']
        
        if 'results' in result and isinstance(result['results'], list):
            for item in result['results']:
                if item.get('file_name', '').endswith('.glb'):
                    return item['url']
        raise ValueError(f"Could not find model URL in {service_name} response. Keys found: {list(result.keys())}")
    
    # Helper to download the generated 3D model file.
    def _download_file(self, url: str) -> bytes:
        response = requests.get(url)
        response.raise_for_status()
        return response.content

class Trellis(Base3DGenerator):
    def __init__(self):
        self.model_endpoint = "fal-ai/trellis/multi"

    def generate(self, images: list[bytes]) -> bytes:
        if not images:
            return None
        
        image_urls = [self._bytes_to_data_uri(img) for img in images]
        
        try:
            result = fal_client.subscribe(
                self.model_endpoint,
                # Update later for multiview support
                arguments={"image_urls": image_urls}
            )
            
            model_url = self._extract_url(result, "Trellis")
            return self._download_file(model_url)
        except Exception as e:
            print(f"Trellis3D Error: {str(e)[:200]}...")
            return None

class Hunyuan(Base3DGenerator):
    def __init__(self):
        self.model_endpoint = "fal-ai/hunyuan3d/v2/multi-view"

    def generate(self, images: list[bytes]) -> bytes:
        if not images or len(images) < 3:
            print("Hunyuan3D requires at least 3 images (Front, Back, Left)")
            return None

        try:
            arguments = {
                "front_image_url": self._bytes_to_data_uri(images[0]),
                "back_image_url": self._bytes_to_data_uri(images[1]),
                "left_image_url": self._bytes_to_data_uri(images[2])
                
            }
            if len(images) == 4:
                arguments["right_image_url"] = self._bytes_to_data_uri(images[3])
            
            result = fal_client.subscribe(
                self.model_endpoint,
                arguments=arguments
            )
            
            model_url = self._extract_url(result, "Hunyuan")
            return self._download_file(model_url)
        except Exception as e:
            print(f"Hunyuan3D Error: {e}")
            return None

class Mock3DGenerator(Base3DGenerator):
    def generate(self, images: list[bytes]) -> bytes:
        print("Mock 3D Generator: Returning dummy GLB bytes.")
        return b"glTF" + b"\x00" * 20  # Minimum fake GLB header