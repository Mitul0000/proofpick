from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent


class Setting(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(BASE_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # API keys (optional: Whisper fallback / Google Safe Browsing)
    groq_api_key: str = ""
    google_safe_browsing_api_key: str = ""

    # YouTube
    max_youtube_results: int = 5
    min_youtube_views: int = 5000
    min_duration: int = 180                # 3 minutes
    max_duration: int = 5400               # 90 minutes
    youtube_workers: int = 4
    transcript_languages: list[str] = ["en", "hi"]
    use_whisper_fallback: bool = True
    whisper_model: str = "whisper-large-v3"
    whisper_max_file_mb: int = 24
    audio_dir: str = str(BASE_DIR / "audio")

    # Web
    max_google_result: int = 10
    web_fetch_timeout: int = 10
    web_workers: int = 6
    min_web_content_chars: int = 300
    max_web_content_chars: int = 60000
    web_max_download_bytes: int = 1_000_000  # stream cap ~1MB
    use_safe_browsing: bool = False
    blocked_domains: list[str] = [
        "facebook.com", "instagram.com", "pinterest.com", "tiktok.com",
        "twitter.com", "x.com", "linkedin.com", "youtube.com", "youtu.be",
    ]
    blocked_file_extensions: list[str] = [
        ".pdf", ".zip", ".rar", ".exe", ".apk", ".mp4", ".mp3", ".jpg", ".png",
    ]

    # Chunking
    max_chunk_size: int = 200
    chars_per_token: int = 4
    overlap_words: int = 30

    # Embedding
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    embedding_batch_size: int = 64

    # Retrieval
    top_k_per_document: int = 3
    min_similarity: float = 0.25
    top_k_master: int = 25
    max_chunks_per_source_in_master: int = 3

    # LLM / Planner / Report
    planner_model: str = "openai/gpt-oss-120b"
    report_model: str = "openai/gpt-oss-120b"
    planner_temperature: float = 0.2
    report_temperature: float = 0.3
    report_max_tokens: int = 4000
    llm_max_retries: int = 2
    llm_timeout: int = 45
    num_youtube_queries: int = 3
    num_web_queries: int = 3
    whisper_translate: bool = True
    report_chunk_max_chars: int = 1200
    mcp_server_name: str = "proofpick"
    log_level: str = "INFO"
    log_file: str = str(BASE_DIR / "proofpick.log")

    # Pipeline & Time Budget
    run_timeout_seconds: int = 120          # total budget before returning partial evidence
    cache_dir: str = str(BASE_DIR / "cache")
    cache_ttl_hours: int = 72