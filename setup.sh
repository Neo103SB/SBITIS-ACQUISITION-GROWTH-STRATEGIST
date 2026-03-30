#!/bin/bash
# SBITIS Platform — Environment setup
# Run: bash setup.sh
# Creates .env and credentials/google_service_account.json

set -e
echo "SBITIS Growth Intelligence Platform — Setup"
echo "==========================================="
echo "Enter credentials (get values from team credential store)"
echo ""

read -p "FIREFLIES_API_KEY: " FIREFLIES_API_KEY
read -p "GEMINI_API_KEY: " GEMINI_API_KEY
read -p "LANGCHAIN_API_KEY: " LANGCHAIN_API_KEY
read -p "META_APP_ID: " META_APP_ID
read -p "META_APP_SECRET: " META_APP_SECRET
read -p "META_ACCESS_TOKEN: " META_ACCESS_TOKEN
read -p "META_AD_ACCOUNT_ID [act_650660610644809]: " META_AD_ACCOUNT_ID
META_AD_ACCOUNT_ID=${META_AD_ACCOUNT_ID:-act_650660610644809}
read -p "GHL_API_KEY: " GHL_API_KEY
read -p "GHL_LOCATION_ID [068UQiIubnC75W5OG5iZ]: " GHL_LOCATION_ID
GHL_LOCATION_ID=${GHL_LOCATION_ID:-068UQiIubnC75W5OG5iZ}
read -p "WAR_SHEET_ID [1BV2Cm3MpBDH_lRGKbDWhmufLVtiNWc8LAPIVf82nAQI]: " WAR_SHEET_ID
WAR_SHEET_ID=${WAR_SHEET_ID:-1BV2Cm3MpBDH_lRGKbDWhmufLVtiNWc8LAPIVf82nAQI}
read -p "KB_FOLDER_IDS [1SN05U7quWsEW9P9g7qvxuk1NTBmPF2XB]: " KB_FOLDER_IDS
KB_FOLDER_IDS=${KB_FOLDER_IDS:-1SN05U7quWsEW9P9g7qvxuk1NTBmPF2XB}
read -p "DRY_RUN [true]: " DRY_RUN
DRY_RUN=${DRY_RUN:-true}

cat > .env << EOF
FIREFLIES_API_KEY=$FIREFLIES_API_KEY
GEMINI_API_KEY=$GEMINI_API_KEY
LANGCHAIN_API_KEY=$LANGCHAIN_API_KEY
META_APP_ID=$META_APP_ID
META_APP_SECRET=$META_APP_SECRET
META_ACCESS_TOKEN=$META_ACCESS_TOKEN
META_AD_ACCOUNT_ID=$META_AD_ACCOUNT_ID
GHL_API_KEY=$GHL_API_KEY
GHL_LOCATION_ID=$GHL_LOCATION_ID
WAR_SHEET_ID=$WAR_SHEET_ID
KB_FOLDER_IDS=$KB_FOLDER_IDS
DRY_RUN=$DRY_RUN
EOF

echo ""
echo "✓ .env created"
echo ""
echo "Now paste the google_service_account.json content."
echo "Press Enter, paste the JSON, then press Ctrl+D:"
mkdir -p credentials
cat > credentials/google_service_account.json

echo "✓ credentials/google_service_account.json created"
echo ""
echo "Setup complete. Run: python main.py --dry-run"
