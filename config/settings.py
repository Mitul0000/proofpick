# from pydantic_settings import BaseSettings
# import os
# from dotenv import load_dotenv


# load_dotenv()

# class Setting(BaseSettings):
#     groq_api_key: str = os.getenv('GROQ_API_KEY')
#     min_views_for_youtube:int = 10000
#     max_youtube_results:int = 10
#     min_youtube_views:int = 10000
#     min_youtube_subscriber:int = 10000
#     min_duration:int = 600
#     max_google_result:int = 20
#     max_chunk_size:int = 1000
#     overlap_words:int = 10


from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent


class Setting(BaseSettings):
    """
    All tunable values live here. Every field can be overridden from the
    environment or from the .env file (e.g. MAX_YOUTUBE_RESULTS=15).
    """

    model_config = SettingsConfigDict(
        env_file=str(BASE_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # ------------------------------------------------------------------
    # API keys (optional: the server still works without them, with
    # reduced features: no Whisper fallback / no Safe Browsing check)
    # ------------------------------------------------------------------
    groq_api_key: str = ""
    google_safe_browsing_api_key: str = ""

    # ------------------------------------------------------------------
    # YouTube
    # ------------------------------------------------------------------
    max_youtube_results: int = 10          # videos fetched per search string
    min_youtube_views: int = 10000
    min_youtube_subscriber: int = 10000    # only used if subscriber lookup is enabled
    min_duration: int = 600                # seconds
    max_duration: int = 5400               # seconds (skip very long videos)
    youtube_workers: int = 6               # parallel transcript fetches
    transcript_languages: list[str] = ["en", "hi"]
    use_whisper_fallback: bool = True      # download audio + Groq Whisper if no captions
    whisper_model: str = "whisper-large-v3"
    whisper_max_file_mb: int = 24          # Groq upload limit is ~25 MB
    audio_dir: str = str(BASE_DIR / "audio")

    # ------------------------------------------------------------------
    # Web
    # ------------------------------------------------------------------
    max_google_result: int = 20            # results per search string (DDGS)
    web_fetch_timeout: int = 15            # seconds per page
    web_workers: int = 8                   # parallel page fetches
    min_web_content_chars: int = 300       # drop near-empty pages
    max_web_content_chars: int = 60000     # truncate huge pages
    use_safe_browsing: bool = False        # needs GOOGLE_SAFE_BROWSING_API_KEY
    blocked_domains: list[str] = [
        "facebook.com", "instagram.com", "pinterest.com", "tiktok.com",
        "twitter.com", "x.com", "linkedin.com", "youtube.com", "youtu.be",
    ]
    blocked_file_extensions: list[str] = [
        ".pdf", ".zip", ".rar", ".exe", ".apk", ".mp4", ".mp3", ".jpg", ".png",
    ]

    # ------------------------------------------------------------------
    # Chunking
    # ------------------------------------------------------------------
    max_chunk_size: int = 200              # approx tokens per chunk (see note below)
    chars_per_token: int = 4
    overlap_words: int = 30                # words repeated between neighbouring chunks

    # NOTE: all-MiniLM-L6-v2 truncates input at ~256 word pieces, so chunks
    # must stay around 200 tokens (~800 chars). Using 1000 would silently
    # embed only the first quarter of each chunk.

    # ------------------------------------------------------------------
    # Embedding
    # ------------------------------------------------------------------
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    embedding_batch_size: int = 64

    # ------------------------------------------------------------------
    # Retrieval
    # ------------------------------------------------------------------
    top_k_per_document: int = 3            # chunks kept per video/page per chunk_query
    min_similarity: float = 0.25           # drop chunks below this cosine score
    top_k_master: int = 25                 # final chunks sent to the LLM
    max_chunks_per_source_in_master: int = 3   # diversity cap per URL

    # ------------------------------------------------------------------
    # Pipeline / cache
    # ------------------------------------------------------------------
    cache_dir: str = str(BASE_DIR / "cache")
    cache_ttl_hours: int = 72
    max_parallel_queries: int = 4