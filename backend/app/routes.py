import base64
import time

from flask import Blueprint, request, send_file, jsonify, current_app
from io import BytesIO

# Define the blueprint
api_bp = Blueprint('api', __name__)

DEFAULT_VIEWPOINTS = ["front", "back", "left", "right"]


@api_bp.route('/health')
def health_check():
    return jsonify({'status': 'healthy'}, 200)


@api_bp.route('/generate-image', methods=['POST'])
def generate_image():
    data = request.get_json()
    optimized_prompt = data.get('optimized_prompt')
    service_choice = data.get('service')
    viewpoints = data.get('viewpoints', DEFAULT_VIEWPOINTS)

    if not optimized_prompt:
        return {'error': 'No prompt provided'}, 400

    # Access registries via current_app.extensions
    registry = current_app.extensions['image_registry']
    service = registry.get_service(service_choice)

    if not service:
        return {'error': f'Service {service_choice} not supported'}, 400

    viewpoint_images = {}
    failed_viewpoints = []

    for viewpoint in viewpoints:
        viewpoint_prompt = f"{optimized_prompt}, {viewpoint} view, single view only"
        try:
            images = service.generate(viewpoint_prompt, num_images=1)
            if images and len(images) > 0:
                b64_str = base64.b64encode(images[0]).decode('utf-8')
                viewpoint_images[viewpoint] = f"data:image/png;base64,{b64_str}"
            else:
                viewpoint_images[viewpoint] = None
                failed_viewpoints.append(viewpoint)
        except Exception as e:
            print(f"Image generation failed for {viewpoint} view: {e}")
            viewpoint_images[viewpoint] = None
            failed_viewpoints.append(viewpoint)

    # If all viewpoints failed, return error
    if len(failed_viewpoints) == len(viewpoints):
        return {'error': 'Image generation failed for all viewpoints'}, 500

    response = {
        'status': 'success',
        'viewpoint_images': viewpoint_images,
        'viewpoints': viewpoints,
        'count': len(viewpoints) - len(failed_viewpoints)
    }

    if failed_viewpoints:
        response['failed_viewpoints'] = failed_viewpoints

    return jsonify(response), 200


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
            sheets_manager.update_row(sheets_data, "Sheet1")
        except Exception as e:
            print(f"Warning: Failed to log to Google Sheets: {e}")

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

        # Generate the model
        model_bytes = service.generate(image_bytes_list)

        if not model_bytes:
            return {'error': 'Failed to generate 3D model'}, 500

        sheets_manager = current_app.extensions['sheet_manager']
        sheets_data = {
            "3D Model Generator": service_choice,

            # temp, need to convert bytes to 3d model/link the file
            "Model link": "Pending implementation"
        }
        sheets_manager.update_row(sheets_data, "Sheet1")

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

    # Placeholder for the actual CLIP score module.
    evaluations = []
    for img_str in images_data:
        # Mocking a score for now
        time.sleep(1) # temp sleep to show evaluating state
        mock_score = 0.0
        evaluations.append({'score': mock_score})

    return jsonify({
        'status': 'success',
        'evaluations': evaluations
    }), 200
