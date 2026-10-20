# ProofPick

ProofPick is a Model Context Protocol (MCP) server that acts as an autonomous AI product researcher. It evaluates user shopping requests by running live, parallel research across YouTube and the web, extracting factual evidence via a two-stage semantic RAG (Retrieval-Augmented Generation) pipeline, and generating a verified, source-cited recommendation report.

---

## Key Features

- **Ambiguity & Intent Parsing**: Accurately extracts category, budget constraints, user use cases, priorities, and brand preferences. Automatically asks clarifying questions if a request is too vague, with a 2-round cap to prevent infinite loops.
- **MCP Client Model Sampling**: Uses MCP session sampling (`session.create_message`) to query the *same model running the client* (Codex, OpenCode, Claude) for intent analysis and report writing. External Groq LLM is used only as a fallback.
- **YouTube Research Engine**:
  - Searches YouTube via `yt-dlp` with filters for minimum duration and view counts.
  - Fetches captions via `youtube-transcript-api`.
  - Intelligently chunks unpunctuated auto-generated video captions so that embeddings cover the entire video.
  - Falls back to downloading audio and transcribing via Groq Whisper (`whisper-large-v3`) if captions are absent (transcodes to mono 32kbps MP3 allowing up to 90 min of speech under the 24 MB limit).
- **Web Extraction Engine**:
  - DuckDuckGo live web search.
  - SSRF protection: blocks private, loopback, and reserved IP ranges on both initial requests and redirects.
  - Streams web page responses up to a 1 MB byte cap to prevent resource exhaustion.
  - Strips clutter, ads, navigation, and scripts using BeautifulSoup.
  - Filters out blocked domains (social media) and unsupported file extensions.
  - Optional Google Safe Browsing v4 threat detection.
- **2-Stage Semantic RAG Pipeline**:
  - **Stage 1 (Document-Level RAG)**: Chunks raw transcripts and web pages, embeds them with `sentence-transformers/all-MiniLM-L6-v2`, and pulls only the top relevant excerpts per query, eliminating 90% of fluff.
  - **Stage 2 (Master Re-ranking & Source Diversity)**: Reranks the merged candidate pool against the user's master goal and applies a per-source cap so no single website or video dominates.
- **Robustness & Branch Isolation**: If YouTube or web scraping encounters an issue, the surviving branch still provides research evidence. An overall execution budget ensures clients receive partial evidence rather than timing out.
- **Prompt Injection Defense**: Untrusted external third-party chunks and transcripts are isolated in `<evidence>` delimiters with explicit instructions forbidding the LLM from executing commands found within scraped text.
- **Fast Local Caching**: SQLite-backed caching with strict TTL enforcement and empty-result rejection.

---

## System Requirements & Prerequisites

1. **Python 3.10+**
2. **ffmpeg** (Required by `yt-dlp` for Whisper audio extraction and conversion):
   ```bash
   # Ubuntu / Debian
   sudo apt install ffmpeg

   # Fedora / RHEL
   sudo dnf install ffmpeg

   # macOS
   brew install ffmpeg
   ```
3. **PyTorch & SentenceTransformers**: `sentence-transformers` installs PyTorch (~800MB–2GB depending on CUDA support). Model weights for `all-MiniLM-L6-v2` (~90MB) download automatically on first run and are warmed up in a background thread at server startup.
4. **Groq API Key (Optional)**: If your MCP client supports sampling, Groq is **not** required for planning or report generation. It is only needed if you wish to transcribe YouTube videos that lack captions via Whisper fallback.

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
Configure your preferences in `.env`:
```env
# Optional: Only needed for Whisper transcription fallback if sampling is supported
GROQ_API_KEY=your_groq_api_key_here

# Optional: Google Safe Browsing API Key
GOOGLE_SAFE_BROWSING_API_KEY=

# LLM Models (used as fallback when MCP client sampling is unavailable)
PLANNER_MODEL=openai/gpt-oss-120b
REPORT_MODEL=openai/gpt-oss-120b

# Query Limits (defaults to 3 each to stay within client tool timeouts)
NUM_YOUTUBE_QUERIES=3
NUM_WEB_QUERIES=3

# Time Budget in seconds before returning partial evidence (default: 120s)
RUN_TIMEOUT_SECONDS=120
```

---

## MCP Server Tools

ProofPick exposes three primary tools over the Model Context Protocol:

| Tool | Parameters | Description |
| :--- | :--- | :--- |
| `research_product` | `message: str`, `history: list[str] = None` | Runs the full pipeline: intent analysis, planning, web + YouTube RAG research, and returns a fully cited Markdown report. Returns clarifying questions if the prompt is ambiguous. Reports progress percentages to the client. |
| `analyze_intent` | `message: str`, `history: list[str] = None` | Parses the user's intent into structured JSON (`category`, `budget`, `priorities`, `dealbreakers`, `clarifications`). Capped at 2 clarification rounds to prevent repeated prompts. |
| `get_evidence` | `message: str`, `history: list[str] = None` | Gathers and returns the raw research evidence, extracted chunks, sources, and stats without generating a final report. Evidence is explicitly marked as untrusted third-party data. |

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

> **Client Timeout Tip**: End-to-end research includes intent parsing, parallel YouTube and web scraping, transcript processing, master semantic reranking, and comprehensive report generation. In your MCP client configuration, ensure tool call timeouts are set to at least 300 seconds.

---

## Testing

Run the automated test suite (chunking unpunctuated text tests and sampling smoke tests):
```bash
python -m unittest discover tests
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
