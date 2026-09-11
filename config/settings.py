from pydantic_settings import BaseSettings
import os
from dotenv import load_dotenv


load_dotenv()

class Setting(BaseSettings):
    groq_api_key: str = os.getenv('GROQ_API_KEY')
    min_views_for_youtube:int = 10000
    max_youtube_results:int = 10
    min_youtube_views:int = 10000
    min_youtube_subscriber:int = 10000
    min_duration:int = 600