import os
from flask import Flask
from config import config
from services.generation.image_generator import ImageServiceRegistry
from services.generation.prompt_generator import PromptServiceRegistry


def create_app(config_name=None):
    if config_name is None:
        config_name = os.getenv('FLASK_ENV', 'default')

    app = Flask(__name__)
    app.config.from_object(config[config_name])

    # Store registries in app.extensions for Blueprint access
    app.extensions['image_registry'] = ImageServiceRegistry(app.config)
    app.extensions['prompt_registry'] = PromptServiceRegistry(app.config)
    app.extensions['3d_registery'] = ThreeDServiceRegistry(app.config)

    from services.google_sheets_integration.sheets_manager import SheetManager
    app.extensions['sheet_manager'] = SheetManager(
        credentials=app.config['GOOGLE_SHEETS_CREDENTIALS_PATH'],
        spreadsheet_id=app.config['GOOGLE_SHEET_ID']
    )

    # Register the Blueprint
    from .routes import api_bp
    app.register_blueprint(api_bp, url_prefix='/api')

    @app.route('/api/generate-3d-model', methods=['POST'])
    def generate_3d_model():
        data = request.get_json()

        # Expecting a list of base64 image strings from the client
        # Example: { "images": ["data:image/png;base64,iVBORw...", ...], "service": "hunyuan" }
        images_data = data.get('images', [])
        service_choice = data.get('service', 'trellis') # Default to Trellis

        if not images_data:
            return {'error': 'No images provided. Please provide at least one image.'}, 400

        # Retrieve the selected service (Trellis or Hunyuan)
        service = threeD_registry.get_service(service_choice)

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

    return app