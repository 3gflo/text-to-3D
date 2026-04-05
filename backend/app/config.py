import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    SECRET_KEY: str = os.getenv('SECRET_KEY', 'dev-fallback-key')
    GOOGLE_SHEETS_CREDENTIALS_PATH: str | None = os.getenv('GOOGLE_SHEETS_CREDENTIALS_PATH')
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
