# SBITIS Growth Intelligence Platform

An autonomous LangGraph-based AI agent acting as a fractional CEO/CGO for SBITIS ACQUISITION.

Runs daily, ingests Fireflies transcripts + Meta Ads + GoHighLevel + Google Sheets, and outputs a strategic intelligence report.

## Architecture

```
Fireflies.ai  ──►  Classifier (7 types)  ──►  Call Analysts (6 nodes)  ──►  LangSmith Datasets
                                                                                    │
Meta Ads API  ──►  Data Aggregator  ──────────────────────────────────────────────►┤
Google Sheets ──►  (WAR Sheet KPIs)                                                 │
GoHighLevel  ──►  (Pipeline Data)                                                   │
                                                                               Strategist (CEO Node)
                                                                                    │
                                                                          Google Sheets Output
                                                                         (🧠 AI Intelligence tab)
```

## The 7 Call Types

| # | Type | Dataset | Description |
|---|------|---------|-------------|
| 1 | Strategy Call | Dataset 1 | Client-facing closing/sales calls |
| 2 | Appointment Setting | Skipped | Short SDR qualification calls |
| 3 | Sales Training | Dataset 2 | Internal coaching, roleplays, call reviews |
| 4 | Leadership Meeting | Dataset 3 | Board/strategic planning sessions |
| 5 | Team Meeting | Dataset 4 | Back/middle office operational meetings |
| 6 | Client Review | Dataset 5 | Monthly/bi-weekly client coaching — content goldmine |
| 7 | Partnership Meeting | Dataset 6 | External agency/partner meetings |

## Quick Start

### 1. Install dependencies
```bash
pip install -r requirements.txt
```

### 2. Set up credentials
```bash
cp .env.example .env
# Fill in all values in .env

mkdir -p credentials
# Place your Google Service Account JSON at: credentials/google_service_account.json
```

### 3. Run once (test)
```bash
python main.py --dry-run
```

### 4. Run for real
```bash
python main.py
```

### 5. Schedule daily (07:00 AM)
```bash
chmod +x cron_setup.sh
./cron_setup.sh
```

Or use the built-in scheduler:
```bash
python main.py --schedule --schedule-time 07:00
```

## Command Line Options

```
python main.py [OPTIONS]

Options:
  --schedule              Run on daily schedule
  --schedule-time HH:MM   Time for daily run (default: 07:00)
  --dry-run               Skip writes to Sheets and LangSmith
  --date YYYY-MM-DD       Override run date
  --log-level LEVEL       DEBUG, INFO, WARNING, ERROR (default: INFO)
```

## LangSmith Datasets

After the first run, 6 datasets will be auto-created in LangSmith:

- `sbitis-strategy-calls` — Full sales call analyses
- `sbitis-sales-training` — Coaching session analyses
- `sbitis-leadership-meetings` — Board/strategic meeting analyses
- `sbitis-team-meetings` — Ops meeting analyses
- `sbitis-client-reviews` — Client review analyses + content angles
- `sbitis-partnership-meetings` — Partnership meeting analyses

## Google Sheets Setup

### WAR Sheet tabs required:
- `Hamza SBITI - Sales Tracking` (or configured CLOSER_TABS)
- `KPIs - Ads` — Top-of-funnel KPI inputs
- `🧠 AI Intelligence` — Created automatically on first run

### Closer tab format (columns):
| A: Date | B: Prospect | C: Outcome (WON/LOST/PENDING/MAYBE) | D: Revenue | E: Notes |

### KPIs - Ads tab format (key-value):
| Metric Name | Value |
|-------------|-------|
| Leads Generated | 150 |
| Booked Meetings | 45 |
| Showed Meetings | 38 |
| Cash Collected | 120000 |

## Project Structure

```
sbitis_platform/
├── config.py              # All configuration
├── state.py               # LangGraph TypedDict state
├── graph.py               # LangGraph workflow definition
├── schemas/               # Pydantic models for all 6 datasets + Meta Ads
├── nodes/
│   ├── fireflies_reader.py    # Node 1: Fetch + classify transcripts
│   ├── call_analysts/         # Node 2: 6 specialized analyst nodes
│   ├── data_aggregator.py     # Node 3: Meta Ads + Sheets + GHL
│   ├── langsmith_storage.py   # Node 4: Persist to LangSmith
│   ├── strategist.py          # Node 5: CEO intelligence report
│   └── output_writer.py       # Node 6: Write to Google Sheets
└── integrations/
    ├── fireflies.py           # Fireflies GraphQL client
    ├── meta_ads.py            # Meta Ads SDK + campaign classifier
    ├── google_sheets.py       # gspread client
    ├── gohighlevel.py         # GHL REST API client
    └── langsmith_client.py    # LangSmith dataset manager
```

## Meta Ads Campaign Classification

Campaigns are auto-classified by name pattern:

| Pattern | Offer Type |
|---------|-----------|
| `DFY`, `done for you` | DFY (primary focus) |
| `DWY`, `done with you` | DWY |
| `DIY` | DIY |
| `DFY_DWY`, `split` | DFY_DWY_SPLIT |
| `hiring`, `recrutement` | HIRING |
| `cours`, `formation` | COURSE |
| `brand`, `awareness` | BRAND_AWARENESS |
| `statix`, `oleazen` | CLIENT_CAMPAIGN |

## Future Phases

The platform is designed to expand to:
- **WhatsApp Sequence Analysis** — Optimize follow-up messaging
- **Content Strategy Layer** — Generate angles from client reviews + strategy calls
- **Knowledge Base Integration** — Instagram/YouTube content patterns
- **Pre-qualification Intelligence** — Better lead scoring before calls
