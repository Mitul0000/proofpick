from pydantic import BaseModel
from typing import Optional


class SourceSearch(BaseModel):
    query:list[str]
    chunk_query:list[str]


    
class SearchQuery(BaseModel):
    google_search:SourceSearch
    youtube_search:SourceSearch