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


def askJson(systemPrompt:str, userPrompt:str, schemaModel:type[BaseModel], model:str|None=None, temperature:float|None=None):
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
