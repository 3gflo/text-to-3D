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
    * **View:** "multi-view orthographic sheet," "front, back, left, right, and top views."

---
**Constraint:** Respond ONLY with the generated prompt. Do not include "Here is your prompt:" or any other text.
    """


class PromptServiceRegistry:
    def __init__(self, app_config):
        google_key = app_config.get('GOOGLE_KEY')
        hf_token = app_config.get('HF_TOKEN')

        self._services = {
            "gemini-2.5-flash": GeminiPromptGenerator(google_key) if google_key else MockPromptGenerator(),
            "gpt-oss": GPTOSSPromptGenerator(hf_token) if hf_token else MockPromptGenerator(),
        }

    def get_service(self, service_name):
        return self._services.get(service_name.lower(), self._services["gemini-2.5-flash"])

    def get_services(self):
        return self._services


class BasePromptGenerator(ABC):
    @abstractmethod
    def generate(self, prompt: str) -> str | None:
        pass


class GeminiPromptGenerator(BasePromptGenerator):
    def __init__(self, api_key):
        self.client = genai.Client(api_key=api_key)
        self.model_name = 'gemini-2.5-flash'

    def generate(self, prompt: str) -> str | None:
        print("Trying gemini prompt...")
        try:
            response = self.client.models.generate_content(
                model=self.model_name,
                config=types.GenerateContentConfig(
                    system_instruction=SYSTEM_INSTRUCTION
                ),
                contents=prompt
            )
            return response.text
        except Exception as e:
            print(f"Gemini Prompt Error: {e}")
            return None


class GPTOSSPromptGenerator(BasePromptGenerator):
    def __init__(self, api_key):
        self.client = InferenceClient(api_key=api_key)
        self.model_name = 'openai/gpt-oss-20b:groq'

    def generate(self, prompt: str) -> str | None:
        print("Trying OpenAI prompt...")
        try:
            completion = self.client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {
                        "role": "system",
                        "content": SYSTEM_INSTRUCTION
                    },
                    {
                        "role": "user",
                        "content": prompt
                    },
                ],
            )
            return completion.choices[0].message.content
        except Exception as e:
            print(f"HuggingFace Prompt Error: {e}")
            return None


class MockPromptGenerator(BasePromptGenerator):
    def generate(self, prompt: str) -> str | None:
        print(f"DEBUG: Mock Prompt Generator used for prompt: {prompt}")
        return (
            f"A hyperrealistic CG render of {prompt}, featuring precise geometric forms "
            "with smooth polished surfaces and subtle material imperfections, presented in "
            "a photorealistic product mockup style, illuminated by bright, even, neutral "
            "studio lighting with soft, diffused lighting and minimal shadows, isolated on "
            "a plain neutral gray background, rendered as a multi-view orthographic sheet "
            "showing front, back, left, right, and top views, high-fidelity 8K quality, "
            "Unreal Engine 5 render."
        )
