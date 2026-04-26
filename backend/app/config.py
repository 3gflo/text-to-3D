import os
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

class Config:
    SECRET_KEY: str = os.getenv('SECRET_KEY', 'dev-fallback-key')
    GOOGLE_SHEETS_CREDENTIALS_PATH: str | None = os.path.join(
        BASE_DIR,
        'services',
        'google_sheets_integration',
        'credentials.json'
    )
    GOOGLE_SHEET_ID: str | None = os.getenv('GOOGLE_SHEET_ID')
    GOOGLE_KEY: str | None = os.getenv('GOOGLE_KEY')
    OPENAI_KEY: str | None = os.getenv('OPENAI_KEY')
    FALAI_KEY: str | None = os.getenv('FALAI_KEY')
    HF_TOKEN: str | None = os.getenv('HF_TOKEN')


class DevelopmentConfig(Config):
    DEBUG = False

class ProductionConfig(Config):
    DEBUG = False

config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}
