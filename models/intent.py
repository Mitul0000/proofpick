from pydantic import BaseModel
from typing import Optional

class Budget(BaseModel):
    min:int
    max:int
    currency:str

class BrandPreference(BaseModel):
    preferred:list
    avoid:list

class ClarificationNeeded(BaseModel):
    is_ambiguous:bool
    missing_info:list

class UserIntent(BaseModel):
    raw_query:str
    product_category:str
    budget:Optional[Budget] = None
    use_case:Optional[str] = None
    priority_attributes:dict[str,float] = {}
    dealbreakers:Optional[list[str]]=None
    brand_preference:Optional[BrandPreference]=None
    free_text_notes:Optional[str]=None
    ai_inferred_attributes:Optional[dict[str,float]]=None
    clarification:Optional[ClarificationNeeded]=None

