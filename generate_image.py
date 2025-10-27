import os
from huggingface_hub import InferenceClient
from openai import OpenAI
from PIL import Image

def main():
    """
    Generates an image from a text prompt using the Hugging Face Inference API
    and saves it to a file.
    """
    print("--- Hugging Face Image Generator ---")

    # 1. Prompt the user for input instead of using command-line arguments
    prompt = input("Enter an image prompt: ")
    front_filename = 'front.png'
    rear_filename = 'rear.png'

    # 2. Get the API token from an environment variable for security
    try:
        api_key = os.environ["HF_TOKEN"]
    except KeyError:
        print("❌ Error: The environment variable HF_TOKEN is not set.")
        print("Please set it to your Hugging Face User Access Token.")
        return

    # 3. Initialize first Inference Client (prompt engineering)
    client = OpenAI(
        base_url="https://router.huggingface.co/v1",
        api_key=os.environ["HF_TOKEN"],
    )

    completion1 = client.chat.completions.create(
        model="openai/gpt-oss-120b:groq",
        messages=[
            {
                "role": "system",
                "content": 
                    "You are an expert prompt engineer for the FLUX.1-dev text-to-image model. "
                    "Your goal is to create a prompt for a photorealistic 2D image to be used as a technical reference for 3D modeling in Microsoft TRELLIS. "
                    "Your output MUST be a clean list of keywords and short, descriptive phrases separated by commas. "
                    "**RULES:** "
                    "1. **REQUIRE an orthographic front view.** The object must be centered and symmetrical. "
                    "2. **REQUIRE even, diffused studio lighting.** Eliminate all harsh shadows and specular highlights. "
                    "3. **REQUIRE sharp focus across the entire object.** "
                    "4. **DO NOT** use narrative sentences. "
                    "5. **DO NOT** use photographic jargon like 'depth of field', 'aperture', 'ISO', 'lens type', or 'bokeh'. "
                    "6. **DO NOT** describe artistic compositions or backgrounds other than a solid, neutral color."
            },
            {
                "role": "user",
                "content": "Engineer a prompt for this subject: " + prompt
            }
        ]
    )
    front_prompt = completion1.choices[0].message.content

    completion2 = client.chat.completions.create(
        model = "openai/gpt-oss-120b:groq",
        messages = [
            # Original system prompt
            {
                "role": "system",
                "content": 
                    "You are an expert prompt engineer for the FLUX.1-dev text-to-image model. "
                    "Your goal is to create a prompt for a photorealistic 2D image to be used as a technical reference for 3D modeling in Microsoft TRELLIS. "
                    "Your output MUST be a clean list of keywords and short, descriptive phrases separated by commas. "
                    "**RULES:** "
                    "1. **REQUIRE an orthographic front view.** The object must be centered and symmetrical. "
                    "2. **REQUIRE even, diffused studio lighting.** Eliminate all harsh shadows and specular highlights. "
                    "3. **REQUIRE sharp focus across the entire object.** "
                    "4. **DO NOT** use narrative sentences. "
                    "5. **DO NOT** use photographic jargon like 'depth of field', 'aperture', 'ISO', 'lens type', or 'bokeh'. "
                    "6. **DO NOT** describe artistic compositions or backgrounds other than a solid, neutral color."
            },
            # First user request
            {
                "role": "user",
                "content": "Engineer a prompt for this subject: " + prompt
            },
            # Model's first response context
            {
                "role": "assistant",
                "content": front_prompt
            },
            # New user request for reverse side
            {
                "role": "user",
                "content": "Perfect. Now, create a prompt for the reverse side of the same object, maintaining the exact same style, lighting, and background."
            }
        ]
    )
    back_prompt = completion2.choices[0].message.content

    # 5. Initialize the Inference Client
    client = InferenceClient(
        provider="nebius",
        token=api_key,
    )

    # 6. Call the text-to-image endpoint for front view
    try:
        print("Generating frontal view based on this prompt: " + front_prompt)
        image1 = client.text_to_image(
            front_prompt,
            model="black-forest-labs/FLUX.1-dev",
        )
    except Exception as e:
        print(f"❌ An error occurred during front view generation: {e}")
        return
    
    # 7. Call text-to-image endpoint for rear view
    try:
        print("Generating rear view based on this prompt: " + back_prompt)
        image2 = client.text_to_image(
            back_prompt,
            model="black-forest-labs/FLUX.1-dev",
        )
    except Exception as e:
        print(f"❌ An error occurred during front view generation: {e}")
        return

    # 7. Save the image to the specified output file
    if isinstance(image1, Image.Image):
        image1.save(front_filename)
        print(f"✅ Image successfully saved to '{front_filename}'")
    else:
        print("❌ The API did not return a valid image object.")

    if isinstance(image2, Image.Image):
        image2.save(rear_filename)
        print(f"✅ Image successfully saved to '{rear_filename}'")
    else:
        print("❌ The API did not return a valid image object.")

if __name__ == "__main__":
    main()
