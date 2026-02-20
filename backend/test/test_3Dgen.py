import requests
import base64
import os
import json

BASE_URL = "http://127.0.0.1:5055"
PROMPT = "A cute isometric low-poly style cottage with a red roof, white walls, on a floating island"
IMAGE_SERVICE = "imagen"   # Options: imagen, nano-banana, GPT-image
THREED_SERVICE = "trellis" # Options: trellis, hunyuan (Hunyuan requires >3 images)

def run_pipeline():
    print(f"--- Starting Pipeline ---")
    
    # Generate images
    print(f"1. Generating images with prompt: '{PROMPT}'...")
    
    payload = {
        "optimized_prompt": PROMPT, 
        "service": IMAGE_SERVICE,
        "num_images": 3 
    }
    
    try:
        img_response = requests.post(
            f"{BASE_URL}/api/generate-image",
            json=payload
        )
        img_response.raise_for_status() # Raise error for 400/500 codes
    except requests.exceptions.RequestException as e:
        print(f"Error generating image: {e}")
        if img_response: print(img_response.text)
        return

    # Handle JSON response containing list of images
    response_data = img_response.json()
    
    # Extract the list of data URI strings ("data:image/png;base64,...")
    images_data = response_data.get('images', [])
    
    if not images_data:
        print("No images returned from service.")
        return
        
    print(f"   -> Received {len(images_data)} images.")

    # Save intermediate images for verification
    for idx, img_str in enumerate(images_data):
        # Strip the header "data:image/png;base64," to save as file
        if ',' in img_str:
            base64_data = img_str.split(',')[1]
        else:
            base64_data = img_str
            
        with open(f"intermediate_image_{idx}.png", "wb") as f:
            f.write(base64.b64decode(base64_data))
    
    print("   -> Intermediate images saved locally.")

    # Generate 3D Model
    print(f"2. Generating 3D model using {THREED_SERVICE}...")

    payload_3d = {
        "images": images_data, 
        "service": THREED_SERVICE
    }

    try:
        three_d_response = requests.post(
            f"{BASE_URL}/api/generate-3d-model",
            json=payload_3d
        )
        three_d_response.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"Error generating 3D model: {e}")
        if three_d_response: print(three_d_response.text)
        return

    # Save result
    output_filename = f"final_model_{THREED_SERVICE}.glb"
    with open(output_filename, "wb") as f:
        f.write(three_d_response.content)
        
    print(f"   -> Success! 3D Model saved as '{output_filename}'")
    print("--- Pipeline Complete ---")

if __name__ == "__main__":
    run_pipeline()