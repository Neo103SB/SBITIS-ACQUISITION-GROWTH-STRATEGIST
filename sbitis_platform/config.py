"""Central configuration — loads from environment variables."""

import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    # ── LLM ──────────────────────────────────────────────────────────────────
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    ANTHROPIC_API_KEY: str = os.getenv("ANTHROPIC_API_KEY", "")

    # Primary model: Gemini 2.5 Flash for speed/cost; Claude for heavy reasoning
    PRIMARY_LLM: str = os.getenv("PRIMARY_LLM", "gemini")  # "gemini" | "claude"
    GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
    CLAUDE_MODEL: str = os.getenv("CLAUDE_MODEL", "claude-sonnet-4-6")

    # ── LangSmith ────────────────────────────────────────────────────────────
    LANGCHAIN_API_KEY: str = os.getenv("LANGCHAIN_API_KEY", "")
    LANGCHAIN_PROJECT: str = os.getenv("LANGCHAIN_PROJECT", "sbitis-growth-platform")
    LANGSMITH_DATASET_STRATEGY_CALLS: str = os.getenv(
        "LANGSMITH_DATASET_STRATEGY_CALLS", "sbitis-strategy-calls"
    )
    LANGSMITH_DATASET_SALES_TRAINING: str = os.getenv(
        "LANGSMITH_DATASET_SALES_TRAINING", "sbitis-sales-training"
    )
    LANGSMITH_DATASET_LEADERSHIP: str = os.getenv(
        "LANGSMITH_DATASET_LEADERSHIP", "sbitis-leadership-meetings"
    )
    LANGSMITH_DATASET_TEAM_MEETINGS: str = os.getenv(
        "LANGSMITH_DATASET_TEAM_MEETINGS", "sbitis-team-meetings"
    )
    LANGSMITH_DATASET_CLIENT_REVIEWS: str = os.getenv(
        "LANGSMITH_DATASET_CLIENT_REVIEWS", "sbitis-client-reviews"
    )
    LANGSMITH_DATASET_PARTNERSHIPS: str = os.getenv(
        "LANGSMITH_DATASET_PARTNERSHIPS", "sbitis-partnership-meetings"
    )

    # ── Fireflies ─────────────────────────────────────────────────────────────
    FIREFLIES_API_KEY: str = os.getenv("FIREFLIES_API_KEY", "")
    FIREFLIES_GRAPHQL_URL: str = "https://api.fireflies.ai/graphql"
    # How many hours back to look for new transcripts on each run
    FIREFLIES_LOOKBACK_HOURS: int = int(os.getenv("FIREFLIES_LOOKBACK_HOURS", "25"))

    # ── Meta Ads ──────────────────────────────────────────────────────────────
    META_APP_ID: str = os.getenv("META_APP_ID", "")
    META_APP_SECRET: str = os.getenv("META_APP_SECRET", "")
    META_ACCESS_TOKEN: str = os.getenv("META_ACCESS_TOKEN", "")
    META_AD_ACCOUNT_ID: str = os.getenv("META_AD_ACCOUNT_ID", "")  # e.g. "act_XXXXXXXXX"
    META_REPORT_DAYS: int = int(os.getenv("META_REPORT_DAYS", "7"))  # rolling window

    # ── Google Sheets ─────────────────────────────────────────────────────────
    GOOGLE_SERVICE_ACCOUNT_JSON: str = os.getenv(
        "GOOGLE_SERVICE_ACCOUNT_JSON", "credentials/google_service_account.json"
    )
    WAR_SHEET_ID: str = os.getenv("WAR_SHEET_ID", "")  # The spreadsheet ID
    AI_INTELLIGENCE_TAB: str = os.getenv("AI_INTELLIGENCE_TAB", "🧠 AI Intelligence")
    KPI_ADS_TAB: str = os.getenv("KPI_ADS_TAB", "KPIs - Ads")

    # Closer tabs — add/remove as team grows
    CLOSER_TABS: list[str] = [
        tab.strip()
        for tab in os.getenv(
            "CLOSER_TABS",
            "Hamza SBITI - Sales Tracking,Zineb Lahbabi - Sales Tracking,Chakir - Sales Tracking,Austin - Sales Tracking",
        ).split(",")
        if tab.strip()
    ]

    # ── GoHighLevel ───────────────────────────────────────────────────────────
    GHL_API_KEY: str = os.getenv("GHL_API_KEY", "")
    GHL_LOCATION_ID: str = os.getenv("GHL_LOCATION_ID", "")
    GHL_BASE_URL: str = "https://services.leadconnectorhq.com"

    # ── General ───────────────────────────────────────────────────────────────
    # ── Knowledge Base ────────────────────────────────────────────────────────
    # Comma-separated Google Drive folder IDs to index into the KB
    # Get a folder ID from the Drive URL: drive.google.com/drive/folders/FOLDER_ID
    KNOWLEDGE_BASE_FOLDER_IDS: list[str] = [
        fid.strip()
        for fid in os.getenv("KB_FOLDER_IDS", "").split(",")
        if fid.strip()
    ]
    # Local path for the persistent ChromaDB vector store
    KB_STORE_PATH: str = os.getenv("KB_STORE_PATH", "./knowledge_base_store")
    # Skip KB ingestion entirely (useful in pure dry-run or offline mode)
    KB_ENABLED: bool = os.getenv("KB_ENABLED", "true").lower() == "true"

    # ── General ───────────────────────────────────────────────────────────────
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    DRY_RUN: bool = os.getenv("DRY_RUN", "false").lower() == "true"
    # When True, skip writes to sheets and LangSmith (for testing)


config = Config()
