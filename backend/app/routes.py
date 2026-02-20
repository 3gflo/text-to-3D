import base64

from flask import Blueprint, request, send_file, jsonify, current_app
from io import BytesIO

# Define the blueprint
api_bp = Blueprint('api', __name__)


@api_bp.route('/health')
def health_check():
    return jsonify({'status': 'healthy'}, 200)


@api_bp.route('/generate-image', methods=['POST'])
def generate_image():
    data = request.get_json()
    optimized_prompt = data.get('optimized_prompt')
    service_choice = data.get('service', 'imagen')

    if not optimized_prompt:
        return {'error': 'No prompt provided'}, 400

    # Access registries via current_app.extensions
    registry = current_app.extensions['image_registry']
    service = registry.get_service(service_choice)

    if not service:
        return {'error': f'Service {service_choice} not supported'}, 400

    image_bytes = service.generate(optimized_prompt)
    if image_bytes:
        sheets_manager = current_app.extensions['sheet_manager']
        sheets_data = {
            "Image Generator": service_choice,

            # temp, need to convert bytes to image/link the file
            "Image 1": image_bytes
        }
        sheets_manager.update_row(sheets_data, "Sheet 1")

        return send_file(BytesIO(image_bytes), mimetype='image/png')

    return {'error': 'Generation failed'}, 500


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
        from .services.generation.prompt_generator import SYSTEM_INSTRUCTION

        # Try to log to Google Sheets, but don't fail if it errors
        try:
            sheets_manager = current_app.extensions['sheet_manager']
            sheets_data = {
                "Image Prompt": prompt,
                "LLM Used": service_choice,
                "Optimized Image Prompt": optimized_prompt,
                "System Prompt": SYSTEM_INSTRUCTION,
            }
            sheets_manager.update_row(sheets_data, "Sheet 1")
        except Exception as e:
            print(f"Warning: Failed to log to Google Sheets: {e}")

        return {
            'success': True,
            'original_prompt': prompt,
            'optimized_prompt': optimized_prompt,
            'service': service_choice
        }, 200

    return {'error': 'Prompt optimization failed'}, 500

@api_bp.route('/api/generate-3d-model', methods=['POST'])
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
            # Strip metadata header (e.g., "data:image/png;base64,") if present
            if ',' in img_str:
                img_str = img_str.split(',')[1]
            image_bytes_list.append(base64.b64decode(img_str))

        # Generate the model
        model_bytes = service.generate(image_bytes_list)

        if not model_bytes:
            return {'error': 'Failed to generate 3D model'}, 500

        sheets_manager = current_app.extensions['sheet_manager']
        sheets_data = {
            "3D Model Generator": service_choice,

            # temp, need to convert bytes to 3d model/link the file
            "Model link": model_bytes
        }
        sheets_manager.update_row(sheets_data, "Sheet 1")

        # Return the GLB file
        return send_file(
            BytesIO(model_bytes),
            mimetype='model/gltf-binary',
            as_attachment=True,
            download_name=f'generated_model_{service_choice}.glb'
        )

    except Exception as e:
        print(f"3D Generation Error: {e}")
        return {'error': str(e)}, 500

@api_bp.route('/available-models', methods=['GET'])
def available_models():
    data = request.get_json()
    asset_type = data.get('asset_type')

    match asset_type:
        case "text":
            registry = current_app.extensions['prompt_registry']
        case "image":
            registry = current_app.extensions['image_registry']
        case "3D":
            registry = current_app.extensions['3D_registry']
        case _:
            return {'error': 'Invalid asset type'}, 400

    services = registry.get_services().keys()


    return jsonify({'services': services}, 200)