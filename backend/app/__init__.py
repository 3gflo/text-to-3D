import os
from flask import Flask
from .config import config
from app.services.generation.image_generator import ImageServiceRegistry
from app.services.generation.prompt_generator import PromptServiceRegistry
from app.services.generation.threeD_generator import ThreeDServiceRegistry


def create_app(config_name=None):
    if config_name is None:
        config_name = os.getenv('FLASK_ENV', 'default')

    app = Flask(__name__)
    app.config.from_object(config[config_name])

    # Store registries in app.extensions for Blueprint access
    app.extensions['image_registry'] = ImageServiceRegistry(app.config)
    app.extensions['prompt_registry'] = PromptServiceRegistry(app.config)
    app.extensions['3d_registry'] = ThreeDServiceRegistry(app.config)

    from app.services.google_sheets_integration.sheets_manager import SheetManager
    from app.services.google_sheets_integration.sheets_manager import MockSheetManager


    credentials_path = app.config.get('GOOGLE_SHEETS_CREDENTIALS_PATH')

    if credentials_path and os.path.exists(credentials_path):
        app.extensions['sheet_manager'] = SheetManager(
            credentials=credentials_path,
            spreadsheet_id=app.config['GOOGLE_SHEET_ID']
        )
    else:
        print("Using MockSheetManager (No credentials found)")
        app.extensions['sheet_manager'] = MockSheetManager()

    # Register the Blueprint
    from .routes import api_bp
    app.register_blueprint(api_bp, url_prefix='/api')

    return app