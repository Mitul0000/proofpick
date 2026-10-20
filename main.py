import asyncio
import logging
import sys
from mcp.server.fastmcp import FastMCP
from config.settings import Setting
from pipeline.planner import analyzeIntent, buildSearchPlan
from pipeline.research import runResearch
from pipeline.report import buildReport
from mcp.server.fastmcp import Context
from core.llm import setSamplingContext, clearSamplingContext

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
async def analyze_intent(message:str, history:list[str]|None=None, ctx:Context=None)->dict:
    """
    Analyzes the user's shopping or product research intent from their query and conversation history.
    Uses the same model in which the MCP is running via session sampling.
    """
    if ctx:
        setSamplingContext(ctx)
    try:
        intent = await asyncio.to_thread(analyzeIntent, message, history)
        return intent.model_dump()
    finally:
        clearSamplingContext()


@mcp.tool()
async def research_product(message:str, history:list[str]|None=None, ctx:Context=None)->str:
    """
    Runs an end-to-end product research and recommendation report.
    First checks if the user's requirements have missing/ambiguous details; if so, returns the specific questions to ask the user.
    When details are complete, runs web and YouTube RAG research and generates the report using the same model.
    """
    if ctx:
        setSamplingContext(ctx)
    try:
        # Step 1: Analyze intent using the same model running the MCP
        intent = await asyncio.to_thread(analyzeIntent, message, history)

        # Step 2: If there are missing details, ask those questions to the user and stop
        if intent.clarification and intent.clarification.is_ambiguous:
            questions = intent.clarification.missing_info or [
                "Could you specify your intended use case or primary purpose?",
                "What is your budget or price range?",
                "Do you have any preferred or avoided brands?",
            ]
            questionsList = "\n".join(f"- {q}" for q in questions)
            return (
                "I need a little more clarification before researching this product:\n\n"
                f"{questionsList}\n\n"
                "Please provide these details so we can run the research accurately."
            )

        # Step 3: Complete details exist -> build search plan and run research
        plan = await asyncio.to_thread(buildSearchPlan, intent)
        evidencePack = await asyncio.to_thread(runResearch, plan)

        # Step 4: Generate report using the same model running the MCP
        report = await asyncio.to_thread(buildReport, intent, evidencePack)
        return report
    finally:
        clearSamplingContext()


@mcp.tool()
async def get_evidence(message:str, history:list[str]|None=None, ctx:Context=None)->dict:
    """
    Gathers raw grounded research evidence from YouTube transcripts and web pages
    based on the user's intent, returning extracted chunks, sources, and stats without generating a final report.
    """
    if ctx:
        setSamplingContext(ctx)
    try:
        intent = await asyncio.to_thread(analyzeIntent, message, history)
        plan = await asyncio.to_thread(buildSearchPlan, intent)
        evidencePack = await asyncio.to_thread(runResearch, plan)
        return evidencePack.model_dump(exclude={"pool"})
    finally:
        clearSamplingContext()
# <<< ARCHITECTURAL CHANGE END: Pass Context to enable sampling the same model running the MCP <<<


if __name__ == "__main__":
    mcp.run()
