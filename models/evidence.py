from pydantic import BaseModel
from models.search_result import GoogleSearchResult, YoutubeSearchResult


class SourceSummary(BaseModel):
    source_id:str = ""
    platform:str
    url:str
    title:str
    author:str = ""
    views:int = 0
    chunks_used:int = 0
    matched_queries:list[str] = []
    best_score:float = 0.0


class QueryStats(BaseModel):
    platform:str
    query:str
    chunk_query:str
    documents_found:int = 0
    documents_read:int = 0
    chunks_kept:int = 0


class ResearchStats(BaseModel):
    videos_found:int = 0
    videos_read:int = 0
    articles_found:int = 0
    articles_read:int = 0
    transcripts_from_captions:int = 0
    transcripts_from_whisper:int = 0
    chunks_before_master:int = 0
    chunks_final:int = 0
    query_stats:list[QueryStats] = []


class EvidencePack(BaseModel):
    master_query:str
    stats:ResearchStats
    sources:list[SourceSummary]
    chunks:list[GoogleSearchResult | YoutubeSearchResult]
    pool:list[GoogleSearchResult | YoutubeSearchResult] = []