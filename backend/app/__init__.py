import os
from flask import Flask
from app.config import config

def create_app(config_name=None):
    if config_name is None:
        config_name = os.getenv('FLASK_ENV', 'default')
    
    app = Flask(__name__)
    app.config.from_object(config[config_name])
    
    from app.services.google_sheets_integration.sheets_manager import SheetManager
    sheet_manager = SheetManager(
        credentials=app.config['GOOGLE_SHEETS_CREDENTIALS_PATH'],
        spreadsheet_id=app.config['GOOGLE_SHEET_ID']
    )
    print(f"SheetManager instance created: {sheet_manager is not None}")

    
    
    
    
    @app.route('/api/health')
    def health_check():
        return {'status': 'healthy'}
    
    return app
