from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent


class Setting(BaseSettings):

    model_config = SettingsConfigDict(
        env_file=str(BASE_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # api keys optional.
    # reduced features like no Whisper fallback or no Safe Browsing check

    groq_api_key: str = ""
    google_safe_browsing_api_key: str = ""

   
    # YouTube
    max_youtube_results: int = 10       
    min_youtube_views: int = 10000
    min_youtube_subscriber: int = 10000    # currenrly not setup
    min_duration: int = 600                # seconds
    max_duration: int = 5400               # seconds skip very long videos
    youtube_workers: int = 6               
    transcript_languages: list[str] = ["en", "hi"]
    use_whisper_fallback: bool = True      # download audio + Groq Whisper if no captions
    whisper_model: str = "whisper-large-v3"
    whisper_max_file_mb: int = 24          # Groq upload max limit is 25 mb
    audio_dir: str = str(BASE_DIR / "audio")

    # Web
    max_google_result: int = 20            
    web_fetch_timeout: int = 15            # seconds per page wait
    web_workers: int = 8                   
    min_web_content_chars: int = 300       # minimum content to consider the page content
    max_web_content_chars: int = 60000     # If content of the page is too long then reduce it to 60000 chars
    use_safe_browsing: bool = False        # needs google safe browsing api
    blocked_domains: list[str] = [
        "facebook.com", "instagram.com", "pinterest.com", "tiktok.com",
        "twitter.com", "x.com", "linkedin.com", "youtube.com", "youtu.be",
    ]
    blocked_file_extensions: list[str] = [
        ".pdf", ".zip", ".rar", ".exe", ".apk", ".mp4", ".mp3", ".jpg", ".png",
    ]
    # this two helps to filter the links in the web search

    
    # Chunking
    max_chunk_size: int = 200             
    chars_per_token: int = 4
    overlap_words: int = 30         

    # NOTE: all-MiniLM-L6-v2 truncates input at 256 word pieces, so chunks
    # must stay around 200 tokens (~800 chars). Using 1000 would silently
    # embed only the first quarter of each chunk.

    
    # Embedding
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    embedding_batch_size: int = 64


    # Retrieval
    top_k_per_document: int = 3            # chunks kept per video/page per chunk_query
    min_similarity: float = 0.25           # drop chunks below this cosine score
    top_k_master: int = 25                 # final chunks sent to the llm
    max_chunks_per_source_in_master: int = 3   # diversity cap per URL


    # LLM / Planner / Report
    planner_model: str = "llama-3.3-70b-versatile"
    report_model: str = "llama-3.3-70b-versatile"
    planner_temperature: float = 0.2
    report_temperature: float = 0.3
    report_max_tokens: int = 4000
    llm_max_retries: int = 2
    llm_timeout: int = 60
    num_youtube_queries: int = 10
    num_web_queries: int = 10
    whisper_translate: bool = True
    report_chunk_max_chars: int = 1200
    mcp_server_name: str = "proofpick"
    log_level: str = "INFO"
    log_file: str = str(BASE_DIR / "proofpick.log")


    # Pipeline / cache
    cache_dir: str = str(BASE_DIR / "cache")
    cache_ttl_hours: int = 72
    max_parallel_queries: int = 4