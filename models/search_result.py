# from pydantic import BaseModel

# class GoogleSearchResult(BaseModel):
#     platform:str = "Google"
#     url:str
#     title:str
#     description:str
#     match_query:str
#     chunk_text:str
#     chunk_match_score:int
#     domain_authority_score:int


# class YoutubeSearchResult(BaseModel):
#     platform:str = "Youtube"
#     url:str
#     channel_name:str
#     title:str
#     description:str
#     match_query:str
#     chunk_text:str
#     chunk_match_score:int
#     view_count:int
#     subscriber_count:int



from pydantic import BaseModel, field_validator


def _none_to_empty(value):
    return "" if value is None else value


class GoogleSearchResult(BaseModel):
    platform: str = "Google"
    url: str
    title: str
    description: str
    match_query: str                 # the search string that found this page
    chunk_query: str = ""            # the query used to extract this chunk
    chunk_text: str
    chunk_index: int = 0             # position of the chunk inside the page
    chunk_match_score: float         # similarity to chunk_query
    master_match_score: float = 0.0  # similarity to master_query (final rerank)
    domain: str = ""
    domain_authority_score: int = 0  # optional, filled only if an SEO API is added

    _clean_title = field_validator("title", "description", mode="before")(_none_to_empty)


class YoutubeSearchResult(BaseModel):
    platform: str = "Youtube"
    url: str
    channel_name: str
    channel_url: str = ""
    title: str
    description: str
    match_query: str                 # the search string that found this video
    chunk_query: str = ""            # the query used to extract this chunk
    chunk_text: str
    chunk_index: int = 0             # position of the chunk inside the transcript
    chunk_match_score: float         # similarity to chunk_query
    master_match_score: float = 0.0  # similarity to master_query (final rerank)
    view_count: int
    subscriber_count: int = 0
    duration: int = 0                # seconds
    transcript_source: str = ""      # "youtube_captions" | "whisper"

    _clean_text = field_validator(
        "title", "description", "channel_name", mode="before"
    )(_none_to_empty)