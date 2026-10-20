import asyncio
import logging
import sys
from mcp.server.fastmcp import FastMCP
from config.settings import Setting
from pipeline.planner import analyzeIntent, buildSearchPlan
from pipeline.research import runResearch
from pipeline.report import buildReport

settings = Setting()

logHandlers = [logging.StreamHandler(sys.stderr)]
if settings.log_file:
    logHandlers.append(logging.FileHandler(settings.log_file, encoding="utf-8"))

logging.basicConfig(
    level=getattr(logging, settings.log_level.upper(), logging.INFO),
    handlers=logHandlers,
    format="%(asctime)s [%(levelname)s] %(message)s"
)

mcp = FastMCP(settings.mcp_server_name)


@mcp.tool()
async def analyze_intent(message:str, history:list[str]|None=None)->dict:
    intent = await asyncio.to_thread(analyzeIntent, message, history)
    return intent.model_dump()


@mcp.tool()
async def research_product(message:str, history:list[str]|None=None)->str:
    intent = await asyncio.to_thread(analyzeIntent, message, history)

    if intent.clarification and intent.clarification.is_ambiguous:
        questions = intent.clarification.missing_info or [
            "Could you specify your intended use case?",
            "What is your budget or price range?",
        ]
        questionsList = "\n".join(f"- {q}" for q in questions)
        return (
            "I need a little more clarification before researching this product:\n\n"
            f"{questionsList}\n\n"
            "Please provide more details so I can find the best recommendation for you."
        )

    plan = await asyncio.to_thread(buildSearchPlan, intent)
    evidencePack = await asyncio.to_thread(runResearch, plan)
    report = await asyncio.to_thread(buildReport, intent, evidencePack)
    return report


@mcp.tool()
async def get_evidence(message:str, history:list[str]|None=None)->dict:
    """
    Gathers raw grounded research evidence from YouTube transcripts and web pages
    based on the user's intent, returning extracted chunks, sources, and stats without generating a final report.
    """
    intent = await asyncio.to_thread(analyzeIntent, message, history)
    plan = await asyncio.to_thread(buildSearchPlan, intent)
    evidencePack = await asyncio.to_thread(runResearch, plan)
    return evidencePack.model_dump(exclude={"pool"})


if __name__ == "__main__":
    mcp.run()
