import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-fallback-key')
    GOOGLE_SHEETS_CREDENTIALS_PATH = os.getenv('GOOGLE_SHEETS_CREDENTIALS_PATH')
    GOOGLE_SHEET_ID = os.getenv('GOOGLE_SHEET_ID')
    GOOGLE_KEY = os.getenv('GOOGLE_KEY')
    OPENAI_KEY = os.getenv('OPENAI_KEY')
    FALAI_KEY = os.getenv('FALAI_KEY')
    HF_TOKEN = os.getenv('HF_TOKEN')


class DevelopmentConfig(Config):
    DEBUG = False

class ProductionConfig(Config):
    DEBUG = False

config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}
