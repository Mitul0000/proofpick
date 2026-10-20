import logging
import sys
from datetime import date
from config.settings import Setting
from core.llm import askJson
from models.intent import UserIntent
from models.search import SearchQuery

settings = Setting()
logger = logging.getLogger("proofpick.planner")

INTENT_SYSTEM_PROMPT = """You are an expert product research intent analyzer.
Your job is to analyze the user's shopping/product request and conversation history, and extract their structured intent.

Return a JSON object conforming exactly to this shape:
{
  "raw_query": "<exact user message>",
  "product_category": "<category e.g. smartphone, laptop, mechanical keyboard>",
  "budget": {
    "min": <int or null>,
    "max": <int or null>,
    "currency": "<e.g. INR, USD>"
  } or null,
  "use_case": "<string describing user use case or null>",
  "priority_attributes": {
    "<attribute_name>": <weight between 0.0 and 1.0>
  },
  "dealbreakers": ["<dealbreaker1>", ... ] or null,
  "brand_preference": {
    "preferred": ["<brand1>", ...],
    "avoid": ["<brand2>", ...]
  } or null,
  "free_text_notes": "<extra notes or null>",
  "ai_inferred_attributes": {
    "<inferred_attribute>": <weight between 0.0 and 1.0>
  } or null,
  "clarification": {
    "is_ambiguous": <true or false>,
    "missing_info": ["<question 1>", "<question 2>"]
  } or null
}

RULES:
1. Put `clarification.is_ambiguous=true` with specific `missing_info` questions when the conversation is not enough to understand any critical requirement (budget, product category, primary use case).
2. Otherwise, infer sensibly from context and set `clarification.is_ambiguous=false` or null.
3. `priority_attributes` maps specific product attributes to weights 0.0 to 1.0 based on what matters most to the user.
"""

SEARCH_PLAN_SYSTEM_PROMPT = """You are a search query planner for a product research engine.
You will be given the user's intent. Your goal is to design a targeted search strategy across YouTube and Web (Google/DuckDuckGo).

Return a JSON object with this shape:
{{
  "google_search": {{
    "query": ["<web query 1>", ...],
    "chunk_query": ["<chunk query 1>", ...]
  }},
  "youtube_search": {{
    "query": ["<yt query 1>", ...],
    "chunk_query": ["<chunk query 1>", ...]
  }},
  "master_query": "<one sentence capturing full intent and priorities for final evidence ranking>"
}}

RULES:
1. Demand EXACTLY {num_youtube} youtube query strings and {num_web} web query strings.
2. The lists `query` and `chunk_query` must be parallel and equal in length for both google_search and youtube_search.
3. Search strings: short, natural, exploring different angles (best-of, honest review, long-term review, vs comparisons, problems/complaints, specific attributes from priorities, budget/location when known). Include the current year ({current_year}) in review-style strings.
4. chunk_query[i]: ONE descriptive sentence saying what facts to pull from every document found by query[i] (e.g. "battery life, charging speed and heating during gaming on the Poco X6").
5. master_query: one sentence capturing the user's full intent and priorities, used to pick the final evidence.
"""


def _countPriorClarificationRounds(history: list[str] | None) -> int:
    """Counts how many times clarification questions have already been asked in the conversation."""
    if not history:
        return 0
    count = 0
    for h in history:
        hLower = h.lower()
        if "clarification before researching" in hLower or "what is your budget" in hLower or "could you specify your intended use case" in hLower:
            count += 1
    return count


def analyzeIntent(userMessage:str, history:list[str]|None=None)->UserIntent:
    userPrompt = f"User message: {userMessage}"
    if history:
        historyStr = "\n".join(history)
        userPrompt = f"Conversation history:\n{historyStr}\n\nUser message: {userMessage}"

    intent = askJson(
        systemPrompt=INTENT_SYSTEM_PROMPT,
        userPrompt=userPrompt,
        schemaModel=UserIntent,
        model=settings.planner_model,
        temperature=settings.planner_temperature,
    )

    # Cap clarification rounds: if history already has 2 or more clarification rounds, proceed with sensible defaults
    if intent.clarification and intent.clarification.is_ambiguous:
        rounds = _countPriorClarificationRounds(history)
        if rounds >= 2:
            logger.info("Clarification round cap reached (>= 2). Overriding ambiguity to proceed with sensible defaults.")
            intent.clarification.is_ambiguous = False
            intent.clarification.missing_info = []

    return intent


def buildSearchPlan(intent:UserIntent)->SearchQuery:
    currentYear = date.today().year
    systemPrompt = SEARCH_PLAN_SYSTEM_PROMPT.format(
        num_youtube=settings.num_youtube_queries,
        num_web=settings.num_web_queries,
        current_year=currentYear,
    )

    userPrompt = f"User Intent JSON:\n{intent.model_dump_json()}"

    plan = askJson(
        systemPrompt=systemPrompt,
        userPrompt=userPrompt,
        schemaModel=SearchQuery,
        model=settings.planner_model,
        temperature=settings.planner_temperature,
    )

    ytCount = len(plan.youtube_search.query)
    webCount = len(plan.google_search.query)
    if ytCount != settings.num_youtube_queries:
        logger.warning(f"Expected {settings.num_youtube_queries} YouTube queries, got {ytCount}")
    if webCount != settings.num_web_queries:
        logger.warning(f"Expected {settings.num_web_queries} Web queries, got {webCount}")

    return plan
