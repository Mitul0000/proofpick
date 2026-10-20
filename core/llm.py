import asyncio
import json
import re
from typing import Any
import sys
from groq import Groq
from pydantic import BaseModel
from config.settings import Setting

settings = Setting()
client = None


def getClient():
    global client
    if client is None:
        client = Groq(api_key=settings.groq_api_key, timeout=settings.llm_timeout)
    return client


# Global context reference set during active MCP tool calls
samplingContext: Any = None


def setSamplingContext(ctx: Any):
    """Sets the active MCP FastMCP Context for the duration of the tool execution."""
    global samplingContext
    samplingContext = ctx


def clearSamplingContext():
    """Clears the active MCP FastMCP Context."""
    global samplingContext
    samplingContext = None


def _cleanJsonMarkdown(rawText: str) -> str:
    cleaned = rawText.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```[a-zA-Z]*\n?", "", cleaned)
        cleaned = re.sub(r"\n?```$", "", cleaned)
    return cleaned.strip()


async def _sampleFromCallerModel(systemPrompt: str, userPrompt: str, maxTokens: int = 4000) -> str:
    """Uses MCP session sampling to ask the SAME model in which the MCP client is running."""
    import mcp.types as types
    session = getattr(samplingContext, "session", None)
    if session is None:
        raise RuntimeError("No active MCP session found for sampling")

    result = await session.create_message(
        messages=[
            types.SamplingMessage(
                role="user",
                content=types.TextContent(type="text", text=userPrompt)
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


def askJson(systemPrompt:str, userPrompt:str, schemaModel:type[BaseModel], model:str|None=None, temperature:float|None=None):
    # If an MCP session sampling context is available, ask the host model running the MCP
    if samplingContext is not None:
        try:
            promptWithSchema = (
                f"{userPrompt}\n\nIMPORTANT: Respond ONLY with a valid JSON object matching this schema:\n"
                f"{json.dumps(schemaModel.model_json_schema())}"
            )
            # Run async sampling call in current event loop or new loop
            try:
                loop = asyncio.get_running_loop()
            except RuntimeError:
                loop = None

            if loop and loop.is_running():
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    rawText = executor.submit(
                        asyncio.run,
                        _sampleFromCallerModel(systemPrompt, promptWithSchema)
                    ).result()
            else:
                rawText = asyncio.run(_sampleFromCallerModel(systemPrompt, promptWithSchema))

            cleaned = _cleanJsonMarkdown(rawText)
            return schemaModel.model_validate_json(cleaned)
        except Exception as e:
            print(f"Sampling from caller model failed ({e}), falling back to client...", file=sys.stderr)

    c = getClient()
    llmModel = model or settings.planner_model
    temp = temperature if temperature is not None else settings.planner_temperature

    currentPrompt = userPrompt
    lastError = None

    for attempt in range(settings.llm_max_retries + 1):
        try:
            response = c.chat.completions.create(
                model=llmModel,
                temperature=temp,
                response_format={"type": "json_object"},
                messages=[
                    {"role": "system", "content": systemPrompt},
                    {"role": "user", "content": currentPrompt},
                ],
            )
            rawText = response.choices[0].message.content
            return schemaModel.model_validate_json(rawText)
        except Exception as e:
            lastError = e
            print(f"askJson attempt {attempt + 1} failed: {e}", file=sys.stderr)
            currentPrompt = f"{userPrompt}\n\nPrevious attempt failed with error: {e}. Please fix and return ONLY valid JSON matching the schema."

    raise ValueError(f"Failed to get valid JSON from LLM after {settings.llm_max_retries + 1} attempts: {lastError}")


def askText(systemPrompt:str, userPrompt:str, model:str|None=None, temperature:float|None=None, max_tokens:int|None=None)->str:
    if samplingContext is not None:
        try:
            try:
                loop = asyncio.get_running_loop()
            except RuntimeError:
                loop = None

            if loop and loop.is_running():
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    rawText = executor.submit(
                        asyncio.run,
                        _sampleFromCallerModel(systemPrompt, userPrompt, maxTokens=max_tokens or settings.report_max_tokens)
                    ).result()
            else:
                rawText = asyncio.run(_sampleFromCallerModel(systemPrompt, userPrompt, maxTokens=max_tokens or settings.report_max_tokens))

            return rawText or ""
        except Exception as e:
            print(f"Sampling from caller model failed ({e}), falling back to client...", file=sys.stderr)

    c = getClient()
    llmModel = model or settings.report_model
    temp = temperature if temperature is not None else settings.report_temperature
    maxTokens = max_tokens or settings.report_max_tokens

    response = c.chat.completions.create(
        model=llmModel,
        temperature=temp,
        max_tokens=maxTokens,
        messages=[
            {"role": "system", "content": systemPrompt},
            {"role": "user", "content": userPrompt},
        ],
    )
    return response.choices[0].message.content or ""
