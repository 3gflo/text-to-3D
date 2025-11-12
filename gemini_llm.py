from google.genai import types
from google import genai
from llm_interface import LLMInterface

class GeminiAdaptor(LLMInterface):
    def __init__(self,api_key: str):
        self.client = genai.Client(api_key=api_key)
        
    def generate_prompt(self, prompt: str,model: str, system_instruction: str) -> str:
        try:
            response = self.client.models.generate_content(
                model=model,
                config=types.GenerateContentConfig(
                    system_instruction=system_instruction),
                    contents=prompt
                )
            return response.text
        except Exception as e:
            print(f"An error has occured: {e}")
            return None
            