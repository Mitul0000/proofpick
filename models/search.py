# from pydantic import BaseModel
# from typing import Optional


# class SourceSearch(BaseModel):
#     query:list[str]
#     chunk_query:list[str]


    
# class SearchQuery(BaseModel):
#     google_search:SourceSearch
#     youtube_search:SourceSearch


from pydantic import BaseModel, model_validator


class SourceSearch(BaseModel):
    """
    `query` and `chunk_query` are PARALLEL lists:
        query[i]        -> the string searched on the platform
        chunk_query[i]  -> the query used to pull relevant chunks out of
                           every document found by query[i]
    """

    query: list[str]
    chunk_query: list[str]

    @model_validator(mode="after")
    def _validate_pairs(self):
        if len(self.query) != len(self.chunk_query):
            raise ValueError(
                "query and chunk_query must have the same length "
                f"(got {len(self.query)} and {len(self.chunk_query)})"
            )

        cleaned_queries: list[str] = []
        cleaned_chunk_queries: list[str] = []
        seen: set[str] = set()

        for q, cq in zip(self.query, self.chunk_query):
            q = (q or "").strip()
            cq = (cq or "").strip()
            if not q or q.lower() in seen:
                continue
            seen.add(q.lower())
            cleaned_queries.append(q)
            cleaned_chunk_queries.append(cq or q)  # fall back to the search string

        self.query = cleaned_queries
        self.chunk_query = cleaned_chunk_queries
        return self

    def pairs(self) -> list[tuple[str, str]]:
        """[(search_string, chunk_query), ...]"""
        return list(zip(self.query, self.chunk_query))


class SearchQuery(BaseModel):
    """The full search plan produced by the LLM after it understands the intent."""

    google_search: SourceSearch
    youtube_search: SourceSearch
    master_query: str

    @model_validator(mode="after")
    def _validate_master(self):
        self.master_query = (self.master_query or "").strip()
        if not self.master_query:
            raise ValueError("master_query must not be empty")
        return self