from pydantic_settings import BaseSettings

class Setting(BaseSettings):
    gemini_api_key:str
    min_views_for_youtube:int = 10000
    max_youtube_results:int = 10