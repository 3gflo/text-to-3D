import os
import base64
import fal_client
import requests
import io
from abc import ABC, abstractmethod
from PIL import Image


class ThreeDServiceRegistry:
    def __init__(self, app_config):
        fal_key = app_config.get('FALAI_KEY')

        if fal_key:
            os.environ['FAL_KEY'] = fal_key
        
        self._services = {
            "trellis": Trellis() if fal_key else Mock3DGenerator(),
            "trellis-2": Trellis2() if fal_key else Mock3DGenerator(),
            "hunyuan": Hunyuan() if fal_key else Mock3DGenerator(),
            "hunyuan-pro": HunyuanPro() if fal_key else Mock3DGenerator()
        }
    
    def get_service(self, service_name):
        # Return requested service or Trellis as default
        return self._services.get(service_name.lower(), self._services["trellis"])

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
            print(f"Trellis Error: {str(e)[:200]}...")
            return None

class Trellis2(Base3DGenerator):
    def __init__(self):
        
        self.model_endpoint = "fal-ai/trellis-2"

    def generate(self, images: list[bytes]) -> bytes:
        if not images:
            print("Trellis 2 requires at least 1 image.")
            return None
        
        try:
            # Convert all images to Data URIs
            image_urls = [self._bytes_to_data_uri(img) for img in images]
            
            # Accepts list of strings as image urls
            arguments = {
                "image_urls": image_urls
                # "resolution": "1024",
                # "texture_size": 2048,
                # "remesh": True
            }
            
            result = fal_client.subscribe(
                self.model_endpoint,
                arguments=arguments
            )
            
            model_url = self._extract_url(result, "Trellis2")
            return self._download_file(model_url)
            
        except Exception as e:
            print(f"Trellis2 Error: {str(e)[:200]}...")
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
            if len(images) > 3:
                arguments["right_image_url"] = self._bytes_to_data_uri(images[3])
            if len(images) > 4:
                arguments["top_image_url"] = self._bytes_to_data_uri(images[4])
            if len(images) > 5:
                arguments["bottom_image_url"] = self._bytes_to_data_uri(images[5])
            
            result = fal_client.subscribe(
                self.model_endpoint,
                arguments=arguments
            )
            
            model_url = self._extract_url(result, "Hunyuan")
            return self._download_file(model_url)
        except Exception as e:
            print(f"Hunyuan3D Error: {e}")
            return None
        
class HunyuanPro(Base3DGenerator):
    def __init__(self):
        # Specific endpoint for v3.1 Pro
        self.model_endpoint = "fal-ai/hunyuan-3d/v3.1/pro/image-to-3d"

    def generate(self, images: list[bytes]) -> bytes:
        if not images:
            print("Hunyuan3D Pro requires at least 1 image (Front view).")
            return None

        try:
            # Front view is 'input_image_url'
            arguments = {
                "input_image_url": self._bytes_to_data_uri(images[0])
            }
            
            # Map additional views if provided by the client
            if len(images) > 1:
                arguments["back_image_url"] = self._bytes_to_data_uri(images[1])
            '''
            if len(images) > 2:
                arguments["left_image_url"] = self._bytes_to_data_uri(images[2])
            if len(images) > 3:
                arguments["right_image_url"] = self._bytes_to_data_uri(images[3])
            if len(images) > 4:
                arguments["top_image_url"] = self._bytes_to_data_uri(images[4])
            if len(images) > 5:
                arguments["bottom_image_url"] = self._bytes_to_data_uri(images[5])
            '''
            
            result = fal_client.subscribe(
                self.model_endpoint,
                arguments=arguments
            )
            
            # v3.1 Pro returns the URL in a 'model_glb' dict, which your _extract_url already handles!
            model_url = self._extract_url(result, "HunyuanPro")
            return self._download_file(model_url)
            
        except Exception as e:
            print(f"HunyuanPro Error: {e}")
            return None

class Mock3DGenerator(Base3DGenerator):
    def generate(self, images: list[bytes]) -> bytes:
        print("Mock 3D Generator: Returning dummy GLB bytes.")
        return b"glTF" + b"\x00" * 20  # Minimum fake GLB header
    

# Helper to split ortographic sheet generated by image_generator into a list of views
def split_orthographic_sheet(sheet_bytes: bytes) -> list[bytes]:
    """
    Takes a single image containing a 2x2 grid of views and splits it into 4 separate images.
    Expected order: Top-Left (Front), Top-Right (Back), Bottom-Left (Left), Bottom-Right (Right).
    """
    img = Image.open(io.BytesIO(sheet_bytes))
    width, height = img.size
    
    # Calculate the exact center of the image
    mid_x = width // 2
    mid_y = height // 2
    
    # Define the 4 quadrants (left, upper, right, lower)
    boxes = [
        (0, 0, mid_x, mid_y),            # 1. Top-Left (Front)
        (mid_x, 0, width, mid_y),        # 2. Top-Right (Back)
        (0, mid_y, mid_x, height),       # 3. Bottom-Left (Left)
        (mid_x, mid_y, width, height)    # 4. Bottom-Right (Right)
    ]
    
    separated_images = []
    
    # Crop each quadrant and convert back to bytes
    for box in boxes:
        cropped_img = img.crop(box)
        
        img_byte_arr = io.BytesIO()
        cropped_img.save(img_byte_arr, format=img.format or 'PNG')
        separated_images.append(img_byte_arr.getvalue())
        
    return separated_images