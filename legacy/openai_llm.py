from huggingface_hub import InferenceClient
import os
from llm_interface import LLMInterface


class OpenaiAdaptor(LLMInterface):
    def __init__(self, api_key: str):
        self.client = InferenceClient(api_key=api_key)

    def generate_prompt(self, prompt: str, model:str, system_instruction:str) -> str:
        try:
            completion = self.client.chat.completions.create(
                model=model,
                messages=[
                    {
                        "role": "system",
                        "content": system_instruction
                    },
                    {
                        "role": "user",
                        "content": prompt
                    },
                ],
            )
            return completion.choices[0].message.content
        except Exception as e:
            print(f"An error has occured: {e}")
            return None 