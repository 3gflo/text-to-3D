import io
import os
import base64
import fal_client
import requests
from abc import ABC, abstractmethod
from PIL import Image


class ThreeDServiceRegistry:
    """Registry of available 3D generation services, keyed by model name."""

    def __init__(self, app_config: dict) -> None:
        fal_key: str | None = app_config.get('FALAI_KEY')

        if fal_key:
            os.environ['FAL_KEY'] = fal_key

        self._services: dict[str, 'Base3DGenerator'] = {
            "trellis": Trellis() if fal_key else Mock3DGenerator(),
            "trellis-2": Trellis2() if fal_key else Mock3DGenerator(),
            "hunyuan": Hunyuan() if fal_key else Mock3DGenerator(),
            "hunyuan-pro": HunyuanPro() if fal_key else Mock3DGenerator()
        }

    def get_service(self, service_name: str) -> 'Base3DGenerator':
        return self._services.get(service_name.lower(), self._services["trellis"])

    def get_services(self) -> dict[str, 'Base3DGenerator']:
        return self._services


class Base3DGenerator(ABC):
    @abstractmethod
    def generate(self, images: list[bytes]) -> bytes | None:
        """Accept a list of view images and return the generated GLB file as bytes."""
        pass

    def _bytes_to_data_uri(self, image_bytes: bytes, mime_type: str = "image/png") -> str:
        """Encode raw image bytes as a base64 data URI for fal.ai API calls."""
        base64_str = base64.b64encode(image_bytes).decode('utf-8')
        return f"data:{mime_type};base64,{base64_str}"

    def _extract_url(self, result: dict, service_name: str) -> str:
        """
        Extract the GLB download URL from a fal.ai response.

        Different fal.ai endpoints return the model URL under different keys,
        so this checks the known variants.
        """
        if 'model_mesh' in result:
            return result['model_mesh']['url']
        if 'model_glb' in result: # Often used in Trellis 2
            return result['model_glb']['url']
        if 'results' in result and isinstance(result['results'], list):
            for item in result['results']:
                if item.get('file_name', '').endswith('.glb'):
                    return item['url']
        raise ValueError(f"Could not find model URL in {service_name} response. Keys: {list(result.keys())}")

    def _download_file(self, url: str) -> bytes:
        """Download a file from a URL and return its raw bytes."""
        response = requests.get(url)
        response.raise_for_status()
        return response.content


class Trellis(Base3DGenerator):
    def __init__(self) -> None:
        self.model_endpoint = "fal-ai/trellis/multi"

    def generate(self, images: list[bytes]) -> bytes | None:
        if not images:
            return None

        image_urls = [self._bytes_to_data_uri(img) for img in images]

        try:
            result = fal_client.subscribe(
                self.model_endpoint,
                arguments={"image_urls": image_urls}
            )
            model_url = self._extract_url(result, "Trellis")
            return self._download_file(model_url)
        except Exception as e:
            print(f"Trellis error: {str(e)[:200]}")
            return None


class Trellis2(Base3DGenerator):
    def __init__(self) -> None:
        self.model_endpoint = "fal-ai/trellis-2"

    def generate(self, images: list[bytes]) -> bytes | None:
        if not images:
            print("Trellis 2 requires at least 1 image.")
            return None

        image_uris = [self._bytes_to_data_uri(img) for img in images]

        # The Trellis-2 API requires both a primary 'image_url' and the full 'image_urls' list
        arguments = {
            "image_url": image_uris[0],
            "image_urls": image_uris
        }

        try:
            print(f"Calling Trellis-2 with {len(image_uris)} views...")
            result = fal_client.subscribe(self.model_endpoint, arguments=arguments)
            model_url = self._extract_url(result, "Trellis2")
            return self._download_file(model_url)
        except Exception as e:
            print(f"Trellis2 error: {str(e)[:500]}")
            return None


class Hunyuan(Base3DGenerator):
    def __init__(self) -> None:
        self.model_endpoint = "fal-ai/hunyuan3d/v2/multi-view"

    def generate(self, images: list[bytes]) -> bytes | None:
        if not images or len(images) < 3:
            print("Hunyuan3D requires at least 3 images (front, back, left).")
            return None

        arguments = {
            "front_image_url": self._bytes_to_data_uri(images[0]),
            "back_image_url": self._bytes_to_data_uri(images[1]),
            "left_image_url": self._bytes_to_data_uri(images[2])
        }
        if len(images) > 3:
            arguments["right_image_url"] = self._bytes_to_data_uri(images[3])

        try:
            result = fal_client.subscribe(self.model_endpoint, arguments=arguments)
            model_url = self._extract_url(result, "Hunyuan")
            return self._download_file(model_url)
        except Exception as e:
            print(f"Hunyuan3D error: {e}")
            return None


class HunyuanPro(Base3DGenerator):
    def __init__(self) -> None:
        self.model_endpoint = "fal-ai/hunyuan-3d/v3.1/pro/image-to-3d"

    def generate(self, images: list[bytes]) -> bytes | None:
        if not images:
            print("Hunyuan3D Pro requires at least 1 image (front view).")
            return None

        arguments: dict[str, str] = {
            "input_image_url": self._bytes_to_data_uri(images[0])
        }

        if len(images) > 1:
            arguments["back_image_url"] = self._bytes_to_data_uri(images[1])

        try:
            print(f"Calling Hunyuan Pro with {len(images)} views...")
            result = fal_client.subscribe(self.model_endpoint, arguments=arguments)
            model_url = self._extract_url(result, "HunyuanPro")
            return self._download_file(model_url)
        except Exception as e:
            print(f"HunyuanPro error: {e}")
            return None


class Mock3DGenerator(Base3DGenerator):
    """Fallback generator used when no FAL API key is available. Returns a minimal GLB header."""

    def generate(self, images: list[bytes]) -> bytes | None:
        print("Mock3DGenerator: returning dummy GLB bytes.")
        return b"glTF" + b"\x00" * 20


def split_orthographic_sheet(sheet_bytes: bytes) -> list[bytes]:
    """
    Split a 4-view orthographic sheet into individual view images.

    Assumes a 2x2 grid layout: top-left = front, top-right = back,
    bottom-left = left side, bottom-right = right side.
    """
    img = Image.open(io.BytesIO(sheet_bytes))
    width, height = img.size
    mid_x = width // 2
    mid_y = height // 2

    boxes = [
        (0, 0, mid_x, mid_y),          # Top-Left (Front)
        (mid_x, 0, width, mid_y),      # Top-Right (Back)
        (0, mid_y, mid_x, height),     # Bottom-Left
        (mid_x, mid_y, width, height)  # Bottom-Right
    ]

    separated_images: list[bytes] = []
    for box in boxes:
        cropped_img = img.crop(box)
        img_byte_arr = io.BytesIO()
        cropped_img.save(img_byte_arr, format='PNG')
        separated_images.append(img_byte_arr.getvalue())

    return separated_images
