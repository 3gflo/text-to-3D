from gemini_llm import GeminiAdaptor
from openai_llm import OpenaiAdaptor
from dotenv import load_dotenv
import os
import fal_client
import requests
import open3d as o3d  # 

from huggingface_hub import InferenceClient
from gradio_client import Client, handle_file

load_dotenv()
gemini_key = os.getenv("GEMINI_API_KEY")
huggingface_key = os.getenv("HF_TOKEN")
client = InferenceClient(api_key=huggingface_key)
trellis_key = os.getenv("FAL_KEY")

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
    * **View:** "multi-view orthographic sheet," "front, back, left, right, and top views."

---
**Constraint:** Respond ONLY with the generated prompt. Do not include "Here is your prompt:" or any other text.
    """

print("Choose an LLM to generate prompts:")
print("1. Gemini (gemini-2.5-flash)")
print("2. OpenAI (gpt-4o-mini via HuggingFace)")
llm_choice = input("Enter your choice (1 or 2): ").strip()

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
feedback = ""
current_instruction = system_instruction
request = input("What object would you like to be generated? ")

while not satisfied:
    try:
        if feedback:
            current_instruction += "\n\n**User Feedback to incorporate:** " + feedback
        system_instruction += feedback

        response = llm.generate_prompt(request, model, current_instruction)
        print("\n--- GENERATED PROMPT ---")
        print(response)
        print("------------------------\n")
        satisfied = True if input("Are you satisfied with the prompt? (y/n): ").lower() == "y" else False
    except Exception as e:
        print(f"An error has occured: {e}")

    if(not satisfied):
        feedback = input("What feedback do you want to give to optimize prompt: ")

fal_urls = []
viewpoints = ["front","back","top","left","right"]

print("\n--- GENERATING VIEWPOINTS ---")
for i in viewpoints:
    req = f"{i} viewpoint of "
    print(f"Generating {i} viewpoint...")
    image = client.text_to_image(
        prompt=req + response,
        model="black-forest-labs/FLUX.1-dev"
    )
    filename = f"{i}.png"
    image.save(filename)
    url = fal_client.upload_file(filename)
    fal_urls.append(url)

def on_queue_update(update):
    if isinstance(update, fal_client.InProgress):
        for log in update.logs:
           print(log["message"])

# --- FINAL SUBMISSION BLOCK ---
try:
    print("\n--- SUBMITTING TO TRELLIS (SINGLE VIEW OPTIMIZED) ---")
    result = fal_client.subscribe(
        "fal-ai/trellis",
        arguments={
            "image_url": fal_urls[0] # Uses the Front view
        },
        with_logs=True,
        on_queue_update=on_queue_update,
    )
    
    print("\n--- GENERATION COMPLETE ---")
    print(result)
    
    # Check if we got a valid 3D model URL
    if 'model_mesh' in result:
        glb_url = result['model_mesh']['url']
        print(f"\n3D Model URL found: {glb_url}")
        
        # --- DOWNLOAD AND VIEW ---
        local_filename = "output_model.glb"
        print(f"Downloading to {local_filename}...")
        
        # 1. Download the file
        response = requests.get(glb_url)
        if response.status_code == 200:
            with open(local_filename, 'wb') as f:
                f.write(response.content)
            print("Download successful!")
            
            # 2. Open the Open3D Viewer
            print("Opening Open3D Viewer... (Close window to exit script)")
            try:
                # Read the mesh
                mesh = o3d.io.read_triangle_mesh(local_filename)
                
                # Check if mesh loaded correctly
                if mesh.is_empty():
                    print("Warning: Mesh appears empty. Trying to load as 'scene'...")
                    # Sometimes GLBs are scenes, not single meshes
                    # But Open3D visualization works best with geometries
                    # Note: Open3D IO is sometimes picky with GLB. 
                
                # Compute normals for better shading (makes it look 3D instead of flat)
                mesh.compute_vertex_normals()
                
                # Draw
                o3d.visualization.draw_geometries([mesh], window_name="3D Model Viewer")
                
            except Exception as e:
                print(f"Could not open viewer: {e}")
                print("You can manually open 'output_model.glb' in https://gltf-viewer.donmccurdy.com/")
        else:
            print("Failed to download the file.")

except Exception as e:
    print(f"Error: {e}")