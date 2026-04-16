import io
import os
import base64
import fal_client
import requests
import tempfile
from abc import ABC, abstractmethod
from PIL import Image
from gradio_client import Client, handle_file


class ThreeDServiceRegistry:
    """Registry of available 3D generation services, keyed by model name."""

    def __init__(self, app_config: dict) -> None:
        fal_key: str | None = app_config.get('FALAI_KEY')

        if fal_key:
            os.environ['FAL_KEY'] = fal_key

        self._services: dict[str, 'Base3DGenerator'] = {
            "trellis": Trellis() if fal_key else Mock3DGenerator(),
            "trellis-2": Trellis2() if fal_key else Mock3DGenerator(),
            "trellis-2-fast": Trellis2Gradio(),
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
        
class Trellis2Gradio(Base3DGenerator):
    """Integrates with the external Trellis 2 Gradio application."""

    def __init__(self):
        self.api_url = "http://vn.ugavel.com:49335/"

    def generate(self, images: list[bytes]) -> bytes | None:
        if not images:
            print("Trellis 2 requires an image.")
            return None

        # Gradio requires a file path, save the byte array to a temp file
        temp_in_path = None
        try:
            with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as temp_in:
                temp_in.write(images[0])
                temp_in_path = temp_in.name

            # Initialize the Gradio Client
            client = Client(self.api_url)

            print("Starting Trellis 2 Session...")
            client.predict(api_name="/start_session")

            print("Preprocessing Image...")
            client.predict(
                image=handle_file(temp_in_path),
                api_name="/preprocess_image_1"
            )

            print("Generating 3D Asset (This may take ~16-45 seconds)...")
            # Passing all default parameters
            client.predict(
                image=handle_file(temp_in_path),
                seed=0,
                resolution="1024",
                ss_guidance_strength=7.5,
                ss_guidance_rescale=0.7,
                ss_sampling_steps=12,
                ss_rescale_t=5,
                shape_slat_guidance_strength=7.5,
                shape_slat_guidance_rescale=0.5,
                shape_slat_sampling_steps=12,
                shape_slat_rescale_t=3,
                tex_slat_guidance_strength=1,
                tex_slat_guidance_rescale=0,
                tex_slat_sampling_steps=12,
                tex_slat_rescale_t=3,
                api_name="/image_to_3d"
            )

            print("Extracting GLB...")
            glb_result = client.predict(
                decimation_target=500000,
                texture_size=2048,
                api_name="/extract_glb"
            )

            # The /extract_glb endpoint returns a tuple, where [1] is the download filepath
            if not glb_result or len(glb_result) < 2:
                print("Trellis 2 failed to return a GLB tuple.")
                return None

            download_filepath = glb_result[1]

            # Read the generated GLB back into bytes to return to the frontend
            with open(download_filepath, "rb") as f:
                glb_bytes = f.read()

            return glb_bytes

        except Exception as e:
            print(f"Trellis 2 Gradio API error: {e}")
            return None

        finally:
            # Clean up temporary file
            if temp_in_path and os.path.exists(temp_in_path):
                os.remove(temp_in_path)


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
            result = fal_client.subscribe(
                self.model_endpoint,
                arguments=arguments
            )
            
            # v3.1 Pro returns the URL in a 'model_glb' dict
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
