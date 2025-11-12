from gemini_llm import GeminiAdaptor
from openai_llm import OpenaiAdaptor
from dotenv import load_dotenv
import os
from huggingface_hub import InferenceClient
from gradio_client import Client, handle_file
# Load environment variables from .env file
load_dotenv()
gemini_key = os.getenv("GEMINI_API_KEY")
huggingface_key = os.getenv("HF_TOKEN")
client = InferenceClient(api_key=huggingface_key)
"""
gemini_key (API KEY)"""
'''


System Prompt for LLM to use. Play around with it.
'''
system_instruction = """
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
  

---
**Constraint:** Respond ONLY with the generated prompt. Do not include "Here is your prompt:" or any other text. Prompt has to be at a maximum of 2000 characters.
    """
  

###LLM Selection
print("Choose an LLM to generate prompts:")
print("1. Gemini (gemini-2.5-flash)")
print("2. OpenAI (gpt-4o-mini via HuggingFace)")
llm_choice = input("Enter your choice (1 or 2): ").strip()

# Initialize the selected LLM adaptor
if llm_choice == "1":
    llm = GeminiAdaptor(api_key=gemini_key)
    model = "gemini-2.5-flash"
    print("Using Gemini LLM")
elif llm_choice == "2":
    llm = OpenaiAdaptor(api_key=huggingface_key)
    model = "openai/gpt-oss-20b:groq"
    print("Using OpenAI LLM via HuggingFace")
else:
    print("Invalid choice. Defaulting to Gemini.")
    llm = GeminiAdaptor(api_key=gemini_key)
    model = "gemini-2.5-flash"

satisfied = False
###feedback from user if prompt is not sufficient enough
feedback = ""
current_instruction = system_instruction
###feedback loop for getting a valid prompt for input into text-image generation
request = input("What object would you like to be generated? ")
while not satisfied:
    try:
        if feedback:
            current_instruction += "\n\n**User Feedback to incorporate:** " + feedback
        system_instruction += feedback

        response = llm.generate_prompt(request, model, current_instruction)
        print(response)
        satisfied = True if input("Are you satisfied with the prompt? (y/n): ").lower() == "y" else False
    except Exception as e:
        print(f"An error has occured: {e}")

    if(not satisfied):
        feedback = input("What feedback do you want to give to optimize prompt: ")


###loop for generating images of different viewpoints of object requested
viewpoints = ["front","back","top","left","right"]
for i in viewpoints:
    req = f"{i} viewpoint of "
    image = client.text_to_image(
    prompt=req + response,
    model="black-forest-labs/FLUX.1-dev"
    )
    image.save(f"{i}.png")
    """
    
trellis_client = Client("trellis-community/TRELLIS")

print("Preprocessing images...")
viewpoints_paths = [f"{v}.png" for v in viewpoints]
preprocessed_images = []
for img_path in viewpoints_paths:
    print(f"Preprocessing {img_path}...")
    preprocessed = trellis_client.predict(
        image=handle_file(os.path.abspath(img_path)),
        api_name="/preprocess_image"
    )
    preprocessed_images.append(preprocessed)

print("\nGenerating 3D model...")
result = trellis_client.predict(
		image=handle_file(preprocessed_images[0]),
		multiimages=[],
		seed=0,
		ss_guidance_strength=7.5,
		ss_sampling_steps=12,
		slat_guidance_strength=3,
		slat_sampling_steps=12,
		multiimage_algo="stochastic",
		mesh_simplify=0.95,
		texture_size=1024,
		api_name="/generate_and_extract_glb"
)
print("3D Generation complete!")
print(f"Video: {result[0]}")
print(f"GLB file: {result[2]}")
"""