# ProofPick

ProofPick is a Model Context Protocol (MCP) server that acts as an autonomous AI product researcher. It evaluates user shopping requests by running live, parallel research across YouTube and the web, extracting factual evidence via a two-stage semantic RAG (Retrieval-Augmented Generation) pipeline, and generating a verified, source-cited recommendation report.

---

## Key Features

- **Ambiguity & Intent Parsing**: Accurately extracts category, budget constraints, user use cases, priorities, and brand preferences. Automatically asks clarifying questions if a request is too vague.
- **Multi-Angle Search Planning**: Generates distinct queries exploring best-of picks, long-term durability reviews, honest complaints/problems, and head-to-head comparisons.
- **YouTube Research Engine**:
  - Searches YouTube via `yt-dlp` with filters for minimum duration and view counts.
  - Fetches transcripts using `youtube-transcript-api`.
  - Automatically falls back to downloading audio and transcribing via Groq Whisper (`whisper-large-v3`) if captions are absent.
- **Web Extraction Engine**:
  - DuckDuckGo live search.
  - Strips clutter, ads, navigation, and scripts using BeautifulSoup.
  - Filters out blocked domains (social media) and unsupported file extensions.
  - Optional Google Safe Browsing v4 threat detection.
- **2-Stage Semantic RAG Pipeline**:
  - **Stage 1 (Document-Level RAG)**: Chunks raw transcripts and web pages, embeds them with `sentence-transformers/all-MiniLM-L6-v2`, and pulls only the top relevant excerpts per query, eliminating 90% of fluff.
  - **Stage 2 (Master Re-ranking & Source Diversity)**: Reranks the merged candidate pool against the user's master goal and applies a per-source cap so no single website or video dominates.
- **Grounded Recommendation Reports**:
  - The #1 best product with detailed justification.
  - Two alternatives with clear "where it is better" and "where it is weaker" breakdowns.
  - Feature comparison table.
  - Conflicting claims and reviewer uncertainties.
  - Strict citations (e.g. `[S1]`, `[S2]`) mapping to full source links, view counts, and authors.
  - Real coverage audit statistics.
- **Fast Local Caching**: SQLite-backed caching for web pages, YouTube searches, and transcripts with configurable TTL.
- **Logging**: Configurable logging written directly to standard error (`stderr`) and auto-persisted to `proofpick.log`.

---

## Project Structure

```
ProofPick/
├── config/
│   └── settings.py          # Central pydantic configuration & environment defaults
├── core/
│   ├── Rag/
│   │   ├── chunking.py      # Intelligent sentence-boundary chunking
│   │   ├── embedding.py     # Lazy model loading & batch embeddings
│   │   ├── pipeline.py      # Document builder & source diversity ranking
│   │   └── retrival.py      # NumPy matrix cosine similarity retrieval
│   └── llm.py               # Groq client wrapper with schema validation & retries
├── models/
│   ├── cache.py             # SQLite caching layer
│   ├── evidence.py          # EvidencePack, SourceSummary, and ResearchStats schemas
│   ├── intent.py            # UserIntent and Budget data contracts
│   ├── search.py            # SearchQuery and SourceSearch models
│   └── search_result.py     # GoogleSearchResult and YoutubeSearchResult models
├── pipeline/
│   ├── planner.py           # analyzeIntent & buildSearchPlan logic
│   ├── report.py            # buildReport & citation post-processing
│   └── research.py          # Parallel youtubeBranch, webBranch & master rerank
├── services/
│   ├── web_service.py       # DuckDuckGo search, HTML cleaning & page scraper
│   └── youtube_service.py   # YouTube search, captions fetch & Whisper fallback
├── .env.example             # Template for API keys and configurable limits
├── main.py                  # FastMCP server entry point & tool definitions
├── proofpick.log            # Execution log file
└── requirements.txt         # Project dependencies
```

---

## Setup & Installation

### 1. Clone the Repository
```bash
git clone https://github.com/Mitul0000/proofpick.git
cd proofpick
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Environment Configuration
Create a `.env` file in the root directory:
```bash
cp .env.example .env
```
Fill in your API keys in `.env`:
```env
# Required for LLM planning, report writing, and Whisper fallback
GROQ_API_KEY=your_groq_api_key_here

# Optional: Google Safe Browsing API Key
GOOGLE_SAFE_BROWSING_API_KEY=

# LLM Models
PLANNER_MODEL=openai/gpt-oss-120b
REPORT_MODEL=openai/gpt-oss-120b

# Query Limits
NUM_YOUTUBE_QUERIES=3
NUM_WEB_QUERIES=3
```

---

## MCP Server Tools

ProofPick exposes three primary tools over the Model Context Protocol:

| Tool | Parameters | Description |
| :--- | :--- | :--- |
| `research_product` | `message: str`, `history: list[str] = None` | Runs the full pipeline: intent analysis, planning, web + YouTube RAG research, and returns a fully cited Markdown report. Returns clarifying questions if the prompt is ambiguous. |
| `analyze_intent` | `message: str`, `history: list[str] = None` | Parses the user's intent into structured JSON (`category`, `budget`, `priorities`, `dealbreakers`, `clarifications`). |
| `get_evidence` | `message: str`, `history: list[str] = None` | Gathers and returns the raw research evidence, extracted chunks, sources, and stats without generating a final report. |

---

## Integration with MCP Clients

### 1. OpenAI Codex CLI
Add ProofPick to Codex with local environment permissions:
```bash
codex mcp add proofpick --env "PYTHONPATH=/home/digifello/ProofPick" -- /usr/bin/python /home/digifello/ProofPick/main.py
```
Run interactively:
```bash
codex
```
Or run non-interactively:
```bash
codex exec --sandbox workspace-write "Research best gaming phones under 20000 rupees using proofpick"
```

### 2. OpenCode CLI
Register ProofPick in OpenCode:
```bash
opencode mcp add proofpick --env "PYTHONPATH=/home/digifello/ProofPick" -- /usr/bin/python /home/digifello/ProofPick/main.py
```
Check status:
```bash
opencode mcp list
```
Start OpenCode:
```bash
opencode
```

### 3. Claude Desktop
Add ProofPick to `~/.config/Claude/claude_desktop_config.json`:
```json
{
  "mcpServers": {
    "proofpick": {
      "command": "/usr/bin/python",
      "args": [
        "/home/digifello/ProofPick/main.py"
      ],
      "env": {
        "PYTHONPATH": "/home/digifello/ProofPick",
        "GROQ_API_KEY": "your_groq_api_key_here"
      }
    }
  }
}
```

---

## Running Standalone in the Terminal

You can test the pipeline directly in Python:
```bash
python -c "
import asyncio
from main import research_product

async def run():
    report = await research_product('phone for gaming under 20000 rupees')
    print(report)

asyncio.run(run())
"
```

---

## Monitoring Logs

All logging is written to `stderr` and saved to `proofpick.log`.

- **Live Stream Logs**:
  ```bash
  tail -f proofpick.log
  ```
- **Inspect Recent Errors / Requests**:
  ```bash
  tail -n 50 proofpick.log
  ```
- **Filter API Calls**:
  ```bash
  grep -i "http request" proofpick.log
  ```

---

## License

MIT License. Built for rigorous, transparent product evaluation.
