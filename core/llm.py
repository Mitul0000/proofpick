import asyncio
import contextvars
import json
import logging
import re
import sys
from typing import Any
from groq import Groq
from pydantic import BaseModel
from config.settings import Setting

settings = Setting()
logger = logging.getLogger("proofpick.llm")

client = None

# ContextVar storing a tuple of (FastMCP Context, active asyncio event loop)
samplingContextVar: contextvars.ContextVar[tuple[Any, Any] | None] = contextvars.ContextVar(
    "samplingContextVar", default=None
)


def getClient():
    global client
    if client is None and settings.groq_api_key:
        client = Groq(api_key=settings.groq_api_key, timeout=settings.llm_timeout)
    return client


def setSamplingContext(ctx: Any, loop: Any = None):
    """Stores the active MCP FastMCP Context and event loop in a ContextVar."""
    if loop is None:
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None
    samplingContextVar.set((ctx, loop))


def clearSamplingContext():
    """Clears the active MCP FastMCP Context."""
    samplingContextVar.set(None)


def _extractJsonBlock(rawText: str) -> str:
    """Extracts JSON from text, matching outermost { to } and stripping markdown fences."""
    cleaned = rawText.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```[a-zA-Z]*\n?", "", cleaned)
        cleaned = re.sub(r"\n?```$", "", cleaned).strip()

    startIdx = cleaned.find("{")
    endIdx = cleaned.rfind("}")
    if startIdx != -1 and endIdx != -1 and endIdx > startIdx:
        return cleaned[startIdx : endIdx + 1]
    return cleaned


def _checkSamplingCapability(session: Any) -> bool:
    """Checks whether the connected MCP client supports sampling."""
    try:
        import mcp.types as types
        if hasattr(session, "check_client_capability"):
            cap = types.ClientCapabilities(sampling=types.SamplingCapability())
            return session.check_client_capability(cap)
    except Exception as e:
        logger.debug(f"Client capability check failed: {e}")
    return True


def _sampleViaEventLoop(session: Any, loop: Any, systemPrompt: str, userPrompt: str, maxTokens: int = 4000) -> str:
    """Dispatches create_message onto the server's main event loop using run_coroutine_threadsafe or direct call."""
    import mcp.types as types

    async def _call():
        result = await session.create_message(
            messages=[
                types.SamplingMessage(
                    role="user",
                    content=types.TextContent(type="text", text=userPrompt),
                )
            ],
            system_prompt=systemPrompt,
            max_tokens=maxTokens,
        )
        content = result.content
        if hasattr(content, "text"):
            return content.text
        if isinstance(content, list) and len(content) > 0 and hasattr(content[0], "text"):
            return content[0].text
        return str(content)

    timeout = getattr(settings, "sampling_timeout", 180)
    if loop.is_running():
        # Invoked from a worker thread (asyncio.to_thread)
        future = asyncio.run_coroutine_threadsafe(_call(), loop)
        try:
            return future.result(timeout=timeout)
        except (TimeoutError, asyncio.TimeoutError):
            future.cancel()
            raise TimeoutError(f"MCP sampling timed out after {timeout}s")
    else:
        # Loop is not currently running (e.g. sync unit test thread)
        return loop.run_until_complete(_call())


def askJson(systemPrompt:str, userPrompt:str, schemaModel:type[BaseModel], model:str|None=None, temperature:float|None=None):
    contextData = samplingContextVar.get()

    # 1. Try MCP Sampling if client session is active and supports sampling
    if contextData is not None:
        ctx, loop = contextData
        session = getattr(ctx, "session", None)
        if session is not None and loop is not None:
            if not _checkSamplingCapability(session):
                logger.info("MCP client does not declare sampling capability; skipping to Groq fallback.")
            else:
                promptWithSchema = (
                    f"{userPrompt}\n\nIMPORTANT: Respond ONLY with a valid JSON object matching this schema:\n"
                    f"{json.dumps(schemaModel.model_json_schema())}"
                )
                currentPrompt = promptWithSchema
                for attempt in range(settings.llm_max_retries + 1):
                    try:
                        logger.info(f"Attempting MCP sampling via caller model (attempt {attempt + 1})...")
                        rawText = _sampleViaEventLoop(session, loop, systemPrompt, currentPrompt)
                        jsonCandidate = _extractJsonBlock(rawText)
                        parsed = schemaModel.model_validate_json(jsonCandidate)
                        logger.info("MCP sampling succeeded and validated schema.")
                        return parsed
                    except (json.JSONDecodeError, ValueError) as ve:
                        # Validation or JSON parse error: safe to retry with error feedback
                        logger.warning(f"MCP sampling attempt {attempt + 1} validation error: {ve}")
                        if attempt < settings.llm_max_retries:
                            currentPrompt = (
                                f"{promptWithSchema}\n\nPrevious response failed validation with error: {ve}. "
                                "Please fix and output ONLY the raw JSON object from { to }."
                            )
                        else:
                            logger.warning("MCP sampling retries exhausted, attempting Groq fallback...")
                    except Exception as e:
                        # Permission, transport, or unexpected error: do not retry in sampling, fall straight to Groq
                        logger.warning(f"MCP sampling encountered non-validation error ({e}); falling back immediately to Groq.")
                        break

    # 2. Fallback to Groq API
    c = getClient()
    if c is None:
        raise RuntimeError("No LLM available: MCP sampling failed/unsupported and GROQ_API_KEY is not configured.")

    llmModel = model or settings.planner_model
    temp = temperature if temperature is not None else settings.planner_temperature
    currentPrompt = userPrompt
    lastError = None

    for attempt in range(settings.llm_max_retries + 1):
        try:
            logger.info(f"Calling Groq LLM ({llmModel}) attempt {attempt + 1}...")
            response = c.chat.completions.create(
                model=llmModel,
                temperature=temp,
                response_format={"type": "json_object"},
                messages=[
                    {"role": "system", "content": systemPrompt},
                    {"role": "user", "content": currentPrompt},
                ],
            )
            rawText = response.choices[0].message.content or "{}"
            jsonCandidate = _extractJsonBlock(rawText)
            parsed = schemaModel.model_validate_json(jsonCandidate)
            logger.info(f"Groq LLM ({llmModel}) answered successfully.")
            return parsed
        except Exception as e:
            lastError = e
            logger.warning(f"Groq askJson attempt {attempt + 1} failed: {e}")
            currentPrompt = f"{userPrompt}\n\nPrevious attempt failed with error: {e}. Return ONLY valid JSON matching the schema."

    raise ValueError(f"Failed to get valid JSON from LLM after {settings.llm_max_retries + 1} attempts: {lastError}")


def askText(systemPrompt:str, userPrompt:str, model:str|None=None, temperature:float|None=None, max_tokens:int|None=None)->str:
    contextData = samplingContextVar.get()

    if contextData is not None:
        ctx, loop = contextData
        session = getattr(ctx, "session", None)
        if session is not None and loop is not None:
            if not _checkSamplingCapability(session):
                logger.info("MCP client does not declare sampling capability for askText; skipping to Groq.")
            else:
                try:
                    logger.info("Calling askText via MCP sampling...")
                    text = _sampleViaEventLoop(
                        session, loop, systemPrompt, userPrompt, maxTokens=max_tokens or settings.report_max_tokens
                    )
                    logger.info("MCP sampling askText succeeded.")
                    return text or ""
                except Exception as e:
                    logger.warning(f"MCP sampling askText failed ({e}), falling back to Groq...")

    c = getClient()
    if c is None:
        raise RuntimeError("No LLM available: MCP sampling failed and GROQ_API_KEY is not configured.")

    llmModel = model or settings.report_model
    temp = temperature if temperature is not None else settings.report_temperature
    maxTokens = max_tokens or settings.report_max_tokens

    logger.info(f"Calling Groq askText ({llmModel})...")
    response = c.chat.completions.create(
        model=llmModel,
        temperature=temp,
        max_tokens=maxTokens,
        messages=[
            {"role": "system", "content": systemPrompt},
            {"role": "user", "content": userPrompt},
        ],
    )
    logger.info("Groq askText completed.")
    return response.choices[0].message.content or ""
