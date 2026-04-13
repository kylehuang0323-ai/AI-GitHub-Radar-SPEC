# AI GitHub Radar

> Daily discovery, classification, summarization and push of high-potential AI GitHub projects.

## Features

- 🔍 **Automated Discovery** – Fetches trending and high-star-growth AI repos from GitHub daily
- 🧹 **Noise Filtering** – Removes inactive, low-quality, or non-AI repositories
- 📊 **Scoring & Ranking** – TrendScore prioritizes *rising* projects over old popular ones
- 🏷️ **Classification** – Categories (LLM/Agent, RAG, Inference, etc.) and multi-dimensional tags
- 🤖 **AI Summarization** – Generates concise, readable project summaries
- 📬 **Teams Push** – Daily digest via Microsoft Teams Workflows webhook
- 🌐 **Summary Page** – GitHub Pages single source of truth

## Quick Start

```bash
# 1. Clone and install
git clone <repo-url>
cd ai-github-radar
pip install -r requirements.txt

# 2. Configure
cp .env.example .env
# Edit .env with your tokens

# 3. Run
python main.py
```

## Configuration

See `.env.example` for all available settings.

| Variable | Required | Description |
|----------|----------|-------------|
| `GITHUB_TOKEN` | ✅ | GitHub personal access token |
| `TEAMS_WORKFLOW_WEBHOOK_URL` | ✅ | Teams Workflows webhook URL |
| `OPENAI_API_KEY` | ❌ | For LLM-based summarization |
| `SUMMARY_PAGE_URL` | ❌ | GitHub Pages URL for summary page |

## Architecture

```
main.py (orchestrator)
  ├─ sources/     → Discover candidates (Trending + Search)
  ├─ pipeline/
  │   ├─ collect  → Enrich repo details
  │   ├─ filter   → Remove noise
  │   ├─ score    → Compute TrendScore
  │   ├─ classify → Assign categories & tags
  │   ├─ summarize→ Generate summary cards
  │   ├─ render   → Produce Markdown/HTML outputs
  │   └─ push     → Send to Teams
  └─ storage/     → Cache & state persistence
```

## License

MIT
