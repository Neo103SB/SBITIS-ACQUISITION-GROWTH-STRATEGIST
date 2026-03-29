#!/bin/bash
# ══════════════════════════════════════════════════════════════════════════════
# SBITIS Growth Intelligence Platform — Cron Setup
# Run this script once to install the daily cron job.
# ══════════════════════════════════════════════════════════════════════════════

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON_PATH="$(which python3)"
LOG_FILE="$SCRIPT_DIR/logs/sbitis_platform.log"

mkdir -p "$SCRIPT_DIR/logs"

# Daily run at 07:00 AM server time
CRON_ENTRY="0 7 * * * cd $SCRIPT_DIR && $PYTHON_PATH main.py >> $LOG_FILE 2>&1"

# Add to crontab if not already present
(crontab -l 2>/dev/null | grep -v "sbitis.*main.py"; echo "$CRON_ENTRY") | crontab -

echo "✅ Cron job installed:"
echo "   $CRON_ENTRY"
echo ""
echo "📋 Current crontab:"
crontab -l
echo ""
echo "📁 Logs will be written to: $LOG_FILE"
