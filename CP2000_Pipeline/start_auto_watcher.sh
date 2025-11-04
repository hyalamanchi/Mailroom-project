#!/bin/bash
# START AUTO PIPELINE WATCHER
# This script starts the automatic file watcher that monitors for new files
# and triggers the pipeline automatically.

cd "$(dirname "$0")"

echo "======================================================================"
echo "🔍 STARTING AUTO PIPELINE WATCHER"
echo "======================================================================"
echo ""
echo "This watcher will:"
echo "  ✅ Monitor Google Drive for new PDF files"
echo "  ✅ Automatically extract case data"
echo "  ✅ Match cases in Logics"
echo "  ✅ Generate updated Google Sheets"
echo ""
echo "Press Ctrl+C to stop the watcher"
echo ""
echo "======================================================================"
echo ""

python3 auto_pipeline_watcher.py

echo ""
echo "🛑 Watcher stopped"

