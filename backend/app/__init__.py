import os
from flask import Flask, request, send_file
from io import BytesIO
from app.config import config
from app.services.generation.image_generator import ImageServiceRegistry

def create_app(config_name=None):
    if config_name is None:
        config_name = os.getenv('FLASK_ENV', 'default')
    
    app = Flask(__name__)
    app.config.from_object(config[config_name])

    image_registry = ImageServiceRegistry(app.config) # Image generation model registry
    
    from app.services.google_sheets_integration.sheets_manager import SheetManager
    sheet_manager = SheetManager(
        credentials=app.config['GOOGLE_SHEETS_CREDENTIALS_PATH'],
        spreadsheet_id=app.config['GOOGLE_SHEET_ID']
    )
    print(f"SheetManager instance created: {sheet_manager is not None}")

    @app.route('/api/health')
    def health_check():
        return {'status': 'healthy'}   
    
    @app.route('/api/generate-image', methods=['POST'])
    def generate_image():
        data = request.get_json()
        prompt = data.get('prompt')
        service_choice = data.get('service', 'imagen') # Default to imagen if empty

        if not prompt:
            return {'error': 'No prompt provided'}, 400

        service = image_registry.get_service(service_choice)
        
        if not service:
            return {'error': f'Service {service_choice} not supported'}, 400
        
        image_bytes = service.generate(prompt)

        if image_bytes:
            # Correctly creates virtual file in memory
            return send_file(BytesIO(image_bytes), mimetype='image/png')
        
        return {'error': 'Generation failed'}, 500
    

    return app
