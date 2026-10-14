import re
import sys
from pydantic import BaseModel
from config.settings import Setting
from core.llm import askJson
from models.evidence import EvidencePack
from models.intent import UserIntent

settings = Setting()


class ReportProduct(BaseModel):
    name: str
    role: str  # "best" | "alternative"


class ReportOutput(BaseModel):
    markdown: str
    products: list[ReportProduct]


REPORT_SYSTEM_PROMPT = """You are a senior product evaluation expert.
You will receive:
1. The user intent summary
2. A research statistics summary
3. A table of indexed sources with their citations [S1], [S2], ...
4. Extracted evidence chunks tagged with their source IDs

YOUR MANDATE:
- Rely ONLY on the supplied evidence. Never invent specs, prices, links, features or counts.
- Every factual sentence MUST end with citations like [S1] or [S2], [S3].
- Separate verified facts from interpretations.
- Mention conflicts, differing opinions, and uncertainty honestly.
- Do not treat popularity or high view counts as proof of quality.
- Do NOT generate the research coverage statistics or the list of sources; python will append those automatically.

Return a JSON object conforming strictly to this format:
{
  "products": [
    {"name": "<exact product name>", "role": "best"},
    {"name": "<alternative product 1>", "role": "alternative"},
    {"name": "<alternative product 2>", "role": "alternative"}
  ],
  "markdown": "<Structured Markdown report according to the format below>"
}

The markdown MUST follow this exact section structure:
# Product Recommendation Report

## 1. Best Product for Your Intent
Explain why it is the best match for the specific requirements and constraints, with citations.

## 2. Alternatives
For each of the two alternatives, include:
- **Where it is weaker**: specific compromises compared to the best choice.
- **Where it is better**: specific areas where it outperforms the best choice.

## 3. Comparison Table
Markdown table comparing key attributes across the recommended products.

## 4. Conflicts & Uncertainty
Highlight conflicting opinions, gaps in testing, or long-term concerns found across the sources.

## 5. Final Advice
Actionable buying guidance and what to verify before purchase.
"""


def buildReport(intent:UserIntent, evidencePack:EvidencePack)->str:
    if not evidencePack.chunks:
        return (
            f"No usable evidence was found for your request.\n\n"
            f"- Videos found: {evidencePack.stats.videos_found} (read: {evidencePack.stats.videos_read})\n"
            f"- Articles found: {evidencePack.stats.articles_found} (read: {evidencePack.stats.articles_read})\n"
            f"- Usable chunks: 0\n"
        )

    # url to source_id mapping
    urlToSourceId = {s.url: s.source_id for s in evidencePack.sources}
    validSourceIds = {s.source_id for s in evidencePack.sources}

    # build context: (a) intent summary
    intentSummary = (
        f"Product Category: {intent.product_category}\n"
        f"Use Case: {intent.use_case}\n"
        f"Budget: {intent.budget.model_dump_json() if intent.budget else 'None'}\n"
        f"Priority Attributes: {intent.priority_attributes}\n"
        f"Dealbreakers: {intent.dealbreakers}\n"
        f"Brand Preferences: {intent.brand_preference.model_dump_json() if intent.brand_preference else 'None'}"
    )

    # build context: (b) stats block
    statsBlock = (
        f"Videos found: {evidencePack.stats.videos_found}, read: {evidencePack.stats.videos_read}\n"
        f"Articles found: {evidencePack.stats.articles_found}, read: {evidencePack.stats.articles_read}\n"
        f"Chunks evaluated: {evidencePack.stats.chunks_before_master}, final chunks: {evidencePack.stats.chunks_final}"
    )

    # build context: (c) source table
    sourceTableLines = ["[S#] | Title | Platform | Channel/Domain | Views | URL"]
    for s in evidencePack.sources:
        sourceTableLines.append(f"[{s.source_id}] | {s.title} | {s.platform} | {s.author} | {s.views} | {s.url}")
    sourceTable = "\n".join(sourceTableLines)

    # build context: (d) evidence chunks
    chunkLines = []
    for c in evidencePack.chunks:
        sId = urlToSourceId.get(c.url, "S?")
        textCut = c.chunk_text[:settings.report_chunk_max_chars]
        chunkLines.append(f"[{sId}] {textCut}")
    evidenceText = "\n\n".join(chunkLines)

    userPrompt = (
        f"### USER INTENT:\n{intentSummary}\n\n"
        f"### RESEARCH STATS:\n{statsBlock}\n\n"
        f"### SOURCE TABLE:\n{sourceTable}\n\n"
        f"### EVIDENCE CHUNKS:\n{evidenceText}\n"
    )

    reportOutput = askJson(
        systemPrompt=REPORT_SYSTEM_PROMPT,
        userPrompt=userPrompt,
        schemaModel=ReportOutput,
        model=settings.report_model,
        temperature=settings.report_temperature,
    )

    markdown = reportOutput.markdown

    # normalize full-width brackets to standard brackets
    markdown = markdown.replace("【", "[").replace("】", "]")

    # post-processing: remove invalid [S#] tags that do not exist in source table
    def sanitizeCitation(match):
        tag = match.group(0)
        sId = match.group(1)
        if sId in validSourceIds:
            return tag
        return ""

    markdown = re.sub(r"\[(S\d+)\]", sanitizeCitation, markdown)

    # count distinct sources in pool where each product name appears
    mentionCounts = []
    for p in reportOutput.products:
        pName = p.name.strip().lower()
        if not pName:
            continue
        vSources = set()
        aSources = set()

        for item in evidencePack.pool:
            text = (item.chunk_text + " " + item.title).lower()
            if pName in text:
                if item.platform == "Youtube":
                    vSources.add(item.url)
                else:
                    aSources.add(item.url)

        mentionCounts.append({
            "name": p.name,
            "videos": len(vSources),
            "articles": len(aSources),
            "total": len(vSources) + len(aSources),
        })

    # append "Research coverage" section
    coverageLines = [
        "\n\n## Research coverage",
        f"- **Videos found**: {evidencePack.stats.videos_found} (read: {evidencePack.stats.videos_read})",
        f"- **Articles found**: {evidencePack.stats.articles_found} (read: {evidencePack.stats.articles_read})",
        f"- **Transcripts**: {evidencePack.stats.transcripts_from_captions} from captions, {evidencePack.stats.transcripts_from_whisper} from Whisper",
        f"- **Chunks**: {evidencePack.stats.chunks_before_master} before master filter, {evidencePack.stats.chunks_final} in final evidence",
        "",
        "### Mention Count by Product",
        "| Product | Video Sources | Article Sources | Total Sources |",
        "| :--- | :--- | :--- | :--- |",
    ]
    for mc in mentionCounts:
        coverageLines.append(f"| {mc['name']} | {mc['videos']} | {mc['articles']} | {mc['total']} |")

    markdown += "\n".join(coverageLines)

    # append "Sources" section
    sourcesLines = ["\n\n## Sources"]
    for s in evidencePack.sources:
        sourcesLines.append(f"- [{s.source_id}] {s.title} - {s.author} - {s.views} views - {s.url}")

    markdown += "\n".join(sourcesLines)

    return markdown
