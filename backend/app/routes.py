import base64
import json

from flask import Blueprint, request, send_file, jsonify, current_app
from .services.generation.threeD_generator import split_orthographic_sheet
from io import BytesIO

from .services.generation.prompt_generator import SYSTEM_INSTRUCTION

# Define the blueprint
api_bp = Blueprint('api', __name__)


@api_bp.route('/health')
def health_check():
    return jsonify({'status': 'healthy'}, 200)


@api_bp.route('/generate-image', methods=['POST'])
def generate_image():
    data = request.get_json()
    optimized_prompt = data.get('optimized_prompt')
    service_choice = data.get('service')

    if not optimized_prompt:
        return {'error': 'No prompt provided'}, 400

    # Access registries via current_app.extensions
    registry = current_app.extensions['image_registry']
    service = registry.get_service(service_choice)

    if not service:
        return {'error': f'Service {service_choice} not supported'}, 400

    images = service.generate(optimized_prompt, num_images = 3)
    if images and len(images) > 0:
        b64_images = []
        for img_bytes in images:
             # Encode to base64 string
            b64_str = base64.b64encode(img_bytes).decode('utf-8')
            # Add data URI prefix
            b64_images.append(f"data:image/png;base64,{b64_str}")

        return jsonify({
            'status': 'success',
            'images': b64_images,
            'count': len(b64_images)
        }), 200

    return {'error': 'Image Generation failed'}, 500


@api_bp.route('/optimize-prompt', methods=['POST'])
def optimize_prompt():
    data = request.get_json()
    prompt = data.get('prompt')
    service_choice = data.get('service', 'gemini-2.5-flash')

    if not prompt:
        return {'error': 'No prompt provided'}, 400

    registry = current_app.extensions['prompt_registry']
    service = registry.get_service(service_choice)

    if not service:
        return {'error': f'Service {service_choice} not supported'}, 400

    optimized_prompt = service.generate(prompt)
    if optimized_prompt:

        return {
            'success': True,
            'original_prompt': prompt,
            'optimized_prompt': optimized_prompt,
            'service': service_choice
        }, 200

    return {'error': 'Prompt optimization failed'}, 500

@api_bp.route('/generate-3d-model', methods=['POST'])
def generate_3d_model():
    data = request.get_json()

    # Expecting a list of base64 image strings from the client
    # Example: { "images": ["data:image/png;base64,iVBORw...", ...], "service": "hunyuan" }
    images_data = data.get('images', [])
    service_choice = data.get('service', 'trellis')  # Default to Trellis

    if not images_data:
        return {'error': 'No images provided. Please provide at least one image.'}, 400

    # Retrieve the selected service (Trellis or Hunyuan)
    registry = current_app.extensions['3d_registry']
    service = registry.get_service(service_choice)

    if not service:
        return {'error': f'Service {service_choice} not supported'}, 400

    try:
        # Decode base64 strings to bytes
        image_bytes_list = []
        for img_str in images_data:
            # Strip metadata header (e.g., "data:image/png;base64,")
            if ',' in img_str:
                img_str = img_str.split(',')[1]
            image_bytes_list.append(base64.b64decode(img_str))

        if len(image_bytes_list) == 1:
            try:
                image_bytes_list = split_orthographic_sheet(image_bytes_list[0])

                '''
                for index, img_bytes in enumerate(image_bytes_list):
                    filename = f"debug_split_view_{index}.png"
                    with open(filename, "wb") as f:
                        f.write(img_bytes)
                    print(f"Saved debug image: {filename}")
                '''

            except Exception as e:
                print(f"Image splitting failed: {e}")
                return {'error': 'Failed to split image'}
        
        
        # Generate the model
        model_bytes = service.generate(image_bytes_list)

        if not model_bytes:
            return {'error': 'Failed to generate 3D model'}, 500

        # Return the GLB file
        return send_file(
            BytesIO(model_bytes),
            mimetype='model/gltf-binary',
            as_attachment=True,
            download_name=f'generated_model_{service_choice}.glb'
        )

    except Exception as e:
        print(f"3D Generation Error Type: {type(e).__name__}")
        return {'error': 'Internal server error during 3D generation'}, 500

@api_bp.route('/available-models', methods=['POST'])
def available_models():
    data = request.get_json()
    asset_type = data.get('asset_type')

    match asset_type:
        case "text":
            registry = current_app.extensions['prompt_registry']
        case "image":
            registry = current_app.extensions['image_registry']
        case "3D":
            registry = current_app.extensions['3d_registry']
        case _:
            return {'error': 'Invalid asset type'}, 400

    services = list(registry.get_services().keys())


    return jsonify({'services': services}), 200


@api_bp.route('/evaluate-image', methods=['POST'])
def evaluate_image():
    data = request.get_json()
    images_data = data.get('images', [])
    prompt = data.get('prompt', '')

    if not images_data or not prompt:
        return {'error': 'Images and prompt are required'}, 400

    # Get the initialized CLIP service
    scorer = current_app.extensions.get('clip_scorer')
    evaluations = []

    for img_str in images_data:
        score = 0.0
        
        if scorer:
            try:
                # The frontend sends "data:image/png;base64,iVBORw..."
                # We need to strip the prefix to decode the raw bytes
                if ',' in img_str:
                    b64_data = img_str.split(',')[1]
                else:
                    b64_data = img_str
                
                # Decode to raw image bytes
                img_bytes = base64.b64decode(b64_data)
                
                # Calculate actual score
                score = scorer.calculate_score(img_bytes, prompt)
                
            except Exception as e:
                print(f"Error decoding or scoring image: {e}")

        evaluations.append({'score': score})

    return jsonify({
        'status': 'success',
        'evaluations': evaluations
    }), 200

@api_bp.route('/save-job', methods=['POST'])
def save_job():
    data = request.get_json()

    try:
        sheets_manager = current_app.extensions['sheet_manager']

        # Consolidate all data into a single row update, gracefully handling missing data
        sheets_data = {
            "User": data.get('user', ''),
            "Description": data.get('description', ''),
            "Image Prompt": data.get('input_prompt', ''),
            "LLM Used": data.get('text_model', ''),
            "System Prompt": SYSTEM_INSTRUCTION,
            "Optimized Image Prompt": data.get('optimized_prompt', ''),
            "Image Generator": data.get('image_model', ''),
            "Image 1": data.get('image_1', ''),
            "Image 2": data.get('image_2', ''),
            "Image 3": data.get('image_3', ''),
            "Image 4": data.get('image_4', ''),
            "3D Model Generator": data.get('three_d_model', ''),
            "Model link": data.get('model_link', ''),
            "Analysis": data.get('analysis', ''),
        }

        sheets_manager.update_row(sheets_data, "Sheet1")

        return jsonify({'status': 'success'}), 200
    except Exception as e:
        print(f"Failed to save job to Sheets: {e}")
        return {'error': 'Failed to save job to Sheets'}, 500

@api_bp.route('/analyze-discrepancies', methods=['POST'])
def analyze_discrepancies():
    data = request.get_json()
    original_prompt = data.get('original_prompt', '')
    input_images = data.get('input_images', [])  # The 2D generated image(s)
    model_snapshots = data.get('model_snapshots', [])  # Screenshots from <model-viewer>

    if not input_images or not model_snapshots:
        return {'error': 'Both input images and model snapshots are required'}, 400

    try:
        from google import genai
        from google.genai import types

        client = genai.Client(api_key=current_app.config['GOOGLE_KEY'])

        prompt_text = f"""
        You are an expert 3D QA engineer. You are evaluating a 3D generation pipeline.
        The user originally prompted the image generator with: "{original_prompt}"

        I am providing you with two sets of images:
        1. The generated 2D concept image(s) (what the 3D model *should* look like).
        2. Snapshots of the final generated 3D model.

        Task:
        1. Analyze the discrepancies between the 2D concept and the 3D model (e.g., missing details, distorted geometry, texture failures).
        2. Based on these failures, write a NEW, optimized image generation prompt. This new prompt should emphasize the problematic areas to force the 2D image generator to create clearer, more distinct features that the 3D generator will have an easier time interpreting.

        Respond STRICTLY in JSON format with the following keys:
        "analysis": "A brief 2-3 sentence analysis of the discrepancies.",
        "suggested_prompt": "The new optimized prompt string."
        """

        contents = [prompt_text]

        # Helper to attach base64 images
        def attach_images(img_list):
            for img_str in img_list:
                if ',' in img_str:
                    img_str = img_str.split(',')[1]
                contents.append(
                    types.Part.from_bytes(data=base64.b64decode(img_str), mime_type='image/png')
                )

        attach_images(input_images)
        attach_images(model_snapshots)

        # Force JSON output
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=contents,
            config=types.GenerateContentConfig(response_mime_type="application/json")
        )

        # Parse the JSON string returned by Gemini
        result_data = json.loads(response.text)

        return jsonify({
            'status': 'success',
            'analysis': result_data.get('analysis', ''),
            'suggested_prompt': result_data.get('suggested_prompt', '')
        }), 200

    except Exception as e:
        print(f"Discrepancy Analysis Error: {e}")
        return {'error': str(e)}, 500