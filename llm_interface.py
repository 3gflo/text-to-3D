from abc import ABC, abstractmethod

class LLMInterface(ABC):

    @abstractmethod
    def generate_prompt(self, prompt: str, model: str, system_instruction: str) -> str | None: 
        '''
        generates prompts for text-to-image part
        '''
        pass