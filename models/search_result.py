from pydantic import BaseModel

class GoogleSearchResult(BaseModel):
    platform:str = "Google"
    url:str
    title:str
    description:str
    match_query:str
    chunk_text:str
    chunk_match_score:int
    domain_authority_score:int


class YoutubeSearchResult(BaseModel):
    platform:str = "Youtube"
    url:str
    channel_name:str
    title:str
    description:str
    match_query:str
    chunk_text:str
    chunk_match_score:int
    view_count:int
    subscriber_count:int
