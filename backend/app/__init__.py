import os
from flask import Flask
from .config import config
from .services.generation.image_generator import ImageServiceRegistry
from .services.generation.prompt_generator import PromptServiceRegistry
from .services.generation.threeD_generator import ThreeDServiceRegistry
from .services.quality_control.clip_scorer import ClipScorerService

def create_app(config_name=None):
    if config_name is None:
        config_name = os.getenv('FLASK_ENV', 'default')

    app = Flask(__name__)
    app.config.from_object(config[config_name])

    # Store registries in app.extensions for Blueprint access
    app.extensions['image_registry'] = ImageServiceRegistry(app.config)
    app.extensions['prompt_registry'] = PromptServiceRegistry(app.config)
    app.extensions['3d_registry'] = ThreeDServiceRegistry(app.config)
    app.extensions['clip_scorer'] = ClipScorerService()

    from .services.google_sheets_integration.sheets_manager import SheetManager
    from .services.google_sheets_integration.sheets_manager import MockSheetManager
    from .services.google_sheets_integration.drive_uploader import GoogleDriveUploader
    from .services.google_sheets_integration.drive_uploader import MockDriveUploader

    creds_path = app.config.get('GOOGLE_SHEETS_CREDENTIALS_PATH')

    if creds_path and os.path.exists(creds_path):
        print("🟢 credentials.json found. Initializing real Google APIs...")
        app.extensions['sheet_manager'] = SheetManager(
            credentials=creds_path,
            spreadsheet_id=app.config['GOOGLE_SHEET_ID']
        )
        app.extensions['drive_uploader'] = GoogleDriveUploader(
            credentials_path=creds_path
        )
    else:
        print("🟡 credentials.json NOT FOUND. Falling back to Mock Services.")
        app.extensions['sheet_manager'] = MockSheetManager()
        app.extensions['drive_uploader'] = MockDriveUploader()

    # Register the Blueprint
    from .routes import api_bp
    app.register_blueprint(api_bp, url_prefix='/api')

    return app