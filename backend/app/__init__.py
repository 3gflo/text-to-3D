import os
from flask import Flask
from .config import config
from .services.generation.image_generator import ImageServiceRegistry
from .services.generation.prompt_generator import PromptServiceRegistry
from .services.generation.threeD_generator import ThreeDServiceRegistry
from .services.quality_control.clip_scorer import ClipScorerService


def create_app(config_name: str | None = None) -> Flask:
    if config_name is None:
        config_name = os.getenv('FLASK_ENV', 'default')

    app = Flask(__name__)
    app.config.from_object(config[config_name])

    app.extensions['image_registry'] = ImageServiceRegistry(app.config)
    app.extensions['prompt_registry'] = PromptServiceRegistry(app.config)
    app.extensions['3d_registry'] = ThreeDServiceRegistry(app.config)
    app.extensions['clip_scorer'] = ClipScorerService()

    from .services.google_sheets_integration.sheets_manager import SheetManager, MockSheetManager

    if app.config.get('GOOGLE_SHEETS_CREDENTIALS_PATH'):
        app.extensions['sheet_manager'] = SheetManager(
            credentials=app.config['GOOGLE_SHEETS_CREDENTIALS_PATH'],
            spreadsheet_id=app.config['GOOGLE_SHEET_ID']
        )
    else:
        print("No Google Sheets credentials found — using MockSheetManager.")
        app.extensions['sheet_manager'] = MockSheetManager()

    from .routes import api_bp
    app.register_blueprint(api_bp, url_prefix='/api')

    return app
