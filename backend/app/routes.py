from flask import Blueprint, request, send_file, jsonify, current_app
from io import BytesIO

# Define the blueprint
api_bp = Blueprint('api', __name__)


@api_bp.route('/health')
def health_check():
    return jsonify({'status': 'healthy'})


@api_bp.route('/generate-image', methods=['POST'])
def generate_image():
    data = request.get_json()
    prompt = data.get('prompt')
    service_choice = data.get('service', 'imagen')

    if not prompt:
        return {'error': 'No prompt provided'}, 400

    # Access registries via current_app.extensions
    registry = current_app.extensions['image_registry']
    service = registry.get_service(service_choice)

    if not service:
        return {'error': f'Service {service_choice} not supported'}, 400

    image_bytes = service.generate(prompt)
    if image_bytes:
        return send_file(BytesIO(image_bytes), mimetype='image/png')

    return {'error': 'Generation failed'}, 500


@api_bp.route('/optimize-prompt', methods=['POST'])
def optimize_prompt():
    data = request.get_json()
    prompt = data.get('prompt')
    service_choice = data.get('service', 'gemini')

    if not prompt:
        return {'error': 'No prompt provided'}, 400

    registry = current_app.extensions['prompt_registry']
    service = registry.get_service(service_choice)

    if not service:
        return {'error': f'Service {service_choice} not supported'}, 400

    optimized = service.generate(prompt)
    if optimized:
        return {
            'success': True,
            'original_prompt': prompt,
            'optimized_prompt': optimized,
            'service': service_choice
        }, 200

    return {'error': 'Prompt optimization failed'}, 500