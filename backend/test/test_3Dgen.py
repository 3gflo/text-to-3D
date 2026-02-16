import requests
import base64
import os

BASE_URL = "http://127.0.0.1:5055"
PROMPT = "A cute isometric low-poly style cottage with a red roof, white walls, on a floating island"
IMAGE_SERVICE = "imagen"  # Options: imagen, nano-banana, GPT-image
THREED_SERVICE = "trellis" # Options: trellis, hunyuan

def run_pipeline():
    print(f"--- Starting Pipeline ---")
    
    # ---------------------------------------------------------
    # STEP 1: Generate the 2D Image
    # ---------------------------------------------------------
    print(f"1. Generating image with prompt: '{PROMPT}'...")
    
    img_response = requests.post(
        f"{BASE_URL}/api/generate-image",
        json={"prompt": PROMPT, "service": IMAGE_SERVICE}
    )

    if img_response.status_code != 200:
        print(f"Error generating image: {img_response.text}")
        return

    # The image service returns raw binary data (image/png)
    image_bytes = img_response.content
    
    # Save the intermediate image for verification
    with open("intermediate_image.png", "wb") as f:
        f.write(image_bytes)
    print("   -> Image generated and saved as 'intermediate_image.png'")

    # ---------------------------------------------------------
    # STEP 2: Generate the 3D Model
    # ---------------------------------------------------------
    print(f"2. Generating 3D model using {THREED_SERVICE}...")

    # The 3D service expects a JSON list of Base64 strings
    # Encode the binary image data received
    base64_image = base64.b64encode(image_bytes).decode('utf-8')
    
    payload = {
        "images": [base64_image], 
        "service": THREED_SERVICE
    }

    three_d_response = requests.post(
        f"{BASE_URL}/api/generate-3d-model",
        json=payload
    )

    if three_d_response.status_code != 200:
        print(f"Error generating 3D model: {three_d_response.text}")
        return

    # ---------------------------------------------------------
    # STEP 3: Save the Result
    # ---------------------------------------------------------
    output_filename = f"final_model_{THREED_SERVICE}.glb"
    with open(output_filename, "wb") as f:
        f.write(three_d_response.content)
        
    print(f"   -> Success! 3D Model saved as '{output_filename}'")
    print("--- Pipeline Complete ---")

if __name__ == "__main__":
    run_pipeline()