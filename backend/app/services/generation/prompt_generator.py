import base64
from abc import ABC, abstractmethod

from google import genai
from google.genai import types
from huggingface_hub import InferenceClient


SYSTEM_INSTRUCTION = """
    You are an expert prompt engineer for text-to-image models. Your sole purpose is to convert simple user keywords into a single, highly-detailed, and optimized prompt for generating multi-view images suitable for 3D reconstruction.

You will receive a simple user input (e.g., "a dining chair").
You MUST generate your response as a single, raw text paragraph. Do not add any preamble, conversation, or quotation marks. The output should be the prompt itself and nothing more.

You will construct this prompt by rigorously following a 4-layer framework:

**Layer 1: WHAT (Subject)**
* Identify the single, core entity.
* The prompt must focus on this entity alone to prevent focus scattering.

**Layer 2: FORM (Features)**
* Use precise, powerful adjectives to define shape and structure (e.g., "faceted geometric shape," "cylindrical," "aerodynamic bullpup design").

**Layer 3: MATERIAL (Surface/Texture)**
* Describe materials with extreme precision for PBR (Physically Based Rendering).
* Specify texture complexity, physical properties, and imperfections (e.g., "smooth polished light oak," "rough-hewn stone with moss," "glowing purple liquid," "brushed aluminum with fine scratches").

**Layer 4: AESTHETICS (Style/Genre)**
* Define the artistic style to constrain interpretation (e.g., "Scandinavian-style," "fantasy RPG asset," "photorealistic product mockup," "sci-fi hard-surface").

---
### **TASK: BUILD THE PROMPT**

* Synthesize Layers 1, 2, 3, and 4 into a single, cohesive paragraph.
* **Crucial Lighting & Composition:** The prompt MUST specify:
    * **Lighting:** "bright, even, neutral studio lighting," "soft, diffused lighting," "minimal shadows." (This is critical for 3D reconstruction).
    * **Background:** "plain neutral gray background," "isolated on a white background."
    * **Quality:** "hyperrealistic CG render," "high-fidelity," "8K," "Unreal Engine 5 render."
    * **View:** "straight on front view."

---
**Constraint:** Respond ONLY with the generated prompt. Do not include "Here is your prompt:" or any other text.
    """


REFINEMENT_SYSTEM_INSTRUCTION = """
You are a prompt refinement assistant for a text-to-image pipeline that generates multi-view images for 3D reconstruction.

You will receive:
1. An existing optimized image generation prompt
2. A target viewpoint (front, back, left, or right). This viewpoint assumes a fixed camera where the object itself rotates:
   - Left view: the object is rotated 90 degrees counterclockwise from the front.
   - Right view: the object is rotated 90 degrees clockwise from the front.
   - Back view: the object is rotated 180 degrees from the front.
3. User feedback describing what they want changed about that viewpoint

Your task: modify the existing prompt to address the user's feedback for the specified viewpoint.
Preserve the overall subject, materials, lighting, background, and style from the original prompt.
Only adjust the aspects the user mentioned.
Respond ONLY with the modified prompt text. No preamble, explanation, or quotation marks.
"""

VISUAL_REFINEMENT_SYSTEM_INSTRUCTION = """
You are a prompt refinement assistant for a text-to-image pipeline that generates multi-view images for 3D reconstruction.

You will receive:
1. An existing optimized image generation prompt
2. A target viewpoint that the user wants to regenerate
3. The currently generated images for ALL viewpoints, each labeled by viewpoint name
4. User feedback describing what they want changed (often pointing out inconsistencies between views)

Your task:
- Visually examine ALL provided viewpoint images to understand the object's overall appearance and any cross-view inconsistencies the user is describing.
- Modify the existing prompt to address the user's feedback for the TARGET viewpoint, informed by what you can actually see in the images.
- Preserve the overall subject, materials, lighting, background, and style from the original prompt.
- Only adjust the aspects the user mentioned or that are clearly inconsistent across views.

Respond ONLY with the modified prompt text. No preamble, explanation, or quotation marks.
"""


class PromptServiceRegistry:
    """Registry of available prompt optimization services, keyed by model name."""

    def __init__(self, app_config: dict) -> None:
        google_key: str | None = app_config.get('GOOGLE_KEY')
        hf_token: str | None = app_config.get('HF_TOKEN')

        self._services: dict[str, 'BasePromptGenerator'] = {
            "gemini-3-flash-preview": GeminiPromptGenerator(google_key) if google_key else MockPromptGenerator(),
            "gpt-oss": GPTOSSPromptGenerator(hf_token) if hf_token else MockPromptGenerator(),
        }

    def get_service(self, service_name: str) -> 'BasePromptGenerator':
        return self._services.get(service_name.lower(), self._services["gemini-3-flash-preview"])

    def get_services(self) -> dict[str, 'BasePromptGenerator']:
        return self._services


class BasePromptGenerator(ABC):
    @abstractmethod
    def generate(self, prompt: str) -> str | None:
        """Optimize a short user prompt into a detailed image generation prompt."""
        pass

    def refine(self, original_prompt: str, viewpoint: str, feedback: str, context_images: list = None) -> str | None:
        """Refine an existing prompt based on user feedback for a specific viewpoint.
        context_images: optional list of {"viewpoint": str, "image": str (base64 data URI)} for visual context.
        Default implementation falls back to returning the original prompt."""
        return original_prompt


class GeminiPromptGenerator(BasePromptGenerator):
    def __init__(self, api_key: str) -> None:
        self.client = genai.Client(api_key=api_key)
        self.model_name = 'gemini-3-flash-preview'

    def generate(self, prompt: str) -> str | None:
        try:
            response = self.client.models.generate_content(
                model=self.model_name,
                config=types.GenerateContentConfig(system_instruction=SYSTEM_INSTRUCTION),
                contents=prompt
            )
            return response.text
        except Exception as e:
            print(f"Gemini prompt error: {e}")
            return None

    def refine(self, original_prompt: str, viewpoint: str, feedback: str, context_images: list = None) -> str | None:
        try:
            message = f"Original prompt: {original_prompt}\nTarget viewpoint to regenerate: {viewpoint}\nUser feedback: {feedback}"

            # If viewpoint images are provided, use multimodal refinement
            if context_images:
                contents = [message]
                for ctx in context_images:
                    contents.append(f"\n[{ctx['viewpoint'].upper()} VIEW]:")
                    img_data = ctx['image']
                    if ',' in img_data:
                        img_data = img_data.split(',')[1]
                    contents.append(
                        types.Part.from_bytes(data=base64.b64decode(img_data), mime_type='image/png')
                    )

                response = self.client.models.generate_content(
                    model=self.model_name,
                    config=types.GenerateContentConfig(
                        system_instruction=VISUAL_REFINEMENT_SYSTEM_INSTRUCTION
                    ),
                    contents=contents
                )
            else:
                # Text-only fallback
                response = self.client.models.generate_content(
                    model=self.model_name,
                    config=types.GenerateContentConfig(
                        system_instruction=REFINEMENT_SYSTEM_INSTRUCTION
                    ),
                    contents=message
                )

            return response.text
        except Exception as e:
            print(f"Gemini Refinement Error: {e}")
            return original_prompt


class GPTOSSPromptGenerator(BasePromptGenerator):
    def __init__(self, api_key: str) -> None:
        self.client = InferenceClient(api_key=api_key)
        self.model_name = 'openai/gpt-oss-20b:groq'

    def generate(self, prompt: str) -> str | None:
        try:
            completion = self.client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {"role": "system", "content": SYSTEM_INSTRUCTION},
                    {"role": "user", "content": prompt},
                ],
            )
            return completion.choices[0].message.content
        except Exception as e:
            print(f"HuggingFace prompt error: {e}")
            return None

    def refine(self, original_prompt: str, viewpoint: str, feedback: str, context_images: list = None) -> str | None:
        # GPT-OSS is text-only -- context_images are ignored
        try:
            message = f"Original prompt: {original_prompt}\nViewpoint: {viewpoint}\nUser feedback: {feedback}"
            completion = self.client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {"role": "system", "content": REFINEMENT_SYSTEM_INSTRUCTION},
                    {"role": "user", "content": message},
                ],
            )
            return completion.choices[0].message.content
        except Exception as e:
            print(f"HuggingFace Refinement Error: {e}")
            return original_prompt


class MockPromptGenerator(BasePromptGenerator):
    """Fallback generator used when no API key is available."""

    def generate(self, prompt: str) -> str | None:
        print(f"MockPromptGenerator called for: {prompt}")
        return (
            f"A hyperrealistic CG render of {prompt}, featuring precise geometric forms "
            "with smooth polished surfaces and subtle material imperfections, presented in "
            "a photorealistic product mockup style, illuminated by bright, even, neutral "
            "studio lighting with soft, diffused lighting and minimal shadows, isolated on "
            "a plain neutral gray background, rendered as a multi-view orthographic sheet "
            "showing front, back, left, right, and top views, high-fidelity 8K quality, "
            "Unreal Engine 5 render."
        )
