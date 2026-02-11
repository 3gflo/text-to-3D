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

            # temp, need to convert bytes to image
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
        from services.generation.prompt_generator import SYSTEM_INSTRUCTION

        sheets_manager = current_app.extensions['sheet_manager']
        sheets_data = {
            "Image Prompt": prompt,
            "LLM Used": service_choice,
            "Optimized Image Prompt": optimized_prompt,
            "System Prompt": SYSTEM_INSTRUCTION,
        }
        sheets_manager.update_row(sheets_data, "Sheet 1")

        return {
            'success': True,
            'original_prompt': prompt,
            'optimized_prompt': optimized_prompt,
            'service': service_choice
        }, 200

    return {'error': 'Prompt optimization failed'}, 500