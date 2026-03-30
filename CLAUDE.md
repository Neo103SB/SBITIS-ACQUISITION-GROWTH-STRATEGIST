# SBITIS Acquisition Growth Strategist — Claude Code Context

## What This Is

A fully automated weekly intelligence platform for SBITIS Acquisition (Moroccan digital marketing agency).
LangGraph pipeline — fetches live data, analyzes Fireflies call recordings, generates strategic reports + content plans.

**Branch:** `claude/sbitis-growth-platform-GrgFb`

---

## Quick Start

```bash
git checkout claude/sbitis-growth-platform-GrgFb
bash setup.sh                  # prompts for credentials → creates .env + credentials/
pip install -r requirements.txt
python main.py --dry-run        # test without writing to Sheets
python main.py                  # full live run
```

---

## Architecture (8 LangGraph nodes, ~3 min runtime)

```
START
  → kb_ingestion          # Loads Drive docs → ChromaDB (Agency Brain)
  → fireflies_reader      # Fetches + classifies calls (past 7 days)
  → call_analysts    ┐    # 6 parallel LLM analysts
  → data_aggregator  ┘    # Meta Ads + WAR Sheet + GHL — concurrent
  → langsmith_storage     # Persists analyses for long-term memory
  → strategist       ┐    # CEO-level strategic report
  → content_intel    ┘    # Content ideas, WhatsApp tweaks, ad angles
  → output_writer    ┐    # Writes to Google Sheets "AI Intelligence" tab
  → content_writer   ┘    # Writes content plan to Sheets
END
```

---

## Key Files

| File | Purpose |
|------|---------|
| `main.py` | Entry point |
| `sbitis_platform/graph.py` | LangGraph pipeline |
| `sbitis_platform/state.py` | Shared state TypedDicts |
| `sbitis_platform/nodes/strategist.py` | Strategic report LLM |
| `sbitis_platform/nodes/fireflies_reader.py` | Call fetching + classification |
| `sbitis_platform/nodes/call_analysts/` | Per-call-type LLM analysts |
| `sbitis_platform/knowledge_base/` | ChromaDB + Drive loader + Agency Brain |
| `sbitis_platform/integrations/` | Meta Ads, Sheets, GHL, Fireflies clients |
| `tests/` | 64 tests — `python -m pytest tests/` |

---

## Credentials Needed

Run `bash setup.sh` — it will prompt for each value.
All values are in the team's secure credential store.

Required:
- `FIREFLIES_API_KEY`
- `GEMINI_API_KEY`
- `LANGCHAIN_API_KEY`
- `META_APP_ID`, `META_APP_SECRET`, `META_ACCESS_TOKEN`, `META_AD_ACCOUNT_ID`
- `GHL_API_KEY`, `GHL_LOCATION_ID`
- `WAR_SHEET_ID`, `KB_FOLDER_IDS`
- `credentials/google_service_account.json` (Google service account for Sheets + Drive)

---

## Agency Brain

Upload docs to Drive folder KB — tagged by filename keywords:
`brain`, `vision`, `positioning`, `philosophy`, `manifesto`, `coach transcript`
→ Always injected into every strategic LLM call.

---

## VPS Deployment (Hostinger srv1306635)

```bash
scp -r . root@VPS_IP:/opt/sbitis-platform/
ssh root@VPS_IP
cd /opt/sbitis-platform && bash setup.sh && pip install -r requirements.txt
python main.py --dry-run
```

Cron (weekly Monday 7am):
```
0 7 * * 1 cd /opt/sbitis-platform && source venv/bin/activate && python main.py
```

---

## Tests

```bash
python -m pytest tests/ -v        # 64 tests, all passing
```
