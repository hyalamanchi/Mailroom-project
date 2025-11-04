#!/bin/bash
#
# START ENHANCED AUTO WATCHER
# Monitors CP2000 folders and appends new cases to existing Google Sheet
#
# Usage: ./start_enhanced_watcher.sh <spreadsheet_id>
#

cd "$(dirname "$0")"

echo "╔═══════════════════════════════════════════════════════════════╗"
echo "║       ENHANCED CP2000 AUTO WATCHER                            ║"
echo "║  Monitors folders and appends to existing Google Sheet        ║"
echo "╚═══════════════════════════════════════════════════════════════╝"
echo ""

# Check if spreadsheet ID is provided
if [ -z "$1" ]; then
    echo "❌ Error: Spreadsheet ID is required"
    echo ""
    echo "Usage: ./start_enhanced_watcher.sh <spreadsheet_id> [interval]"
    echo ""
    echo "Example:"
    echo "  ./start_enhanced_watcher.sh 1abc123xyz456"
    echo "  ./start_enhanced_watcher.sh 1abc123xyz456 180  # Check every 3 minutes"
    echo ""
    echo "To get your spreadsheet ID:"
    echo "  1. Open your Google Sheet"
    echo "  2. Look at the URL:"
    echo "     https://docs.google.com/spreadsheets/d/SPREADSHEET_ID/edit"
    echo "  3. Copy the SPREADSHEET_ID part"
    echo ""
    exit 1
fi

SPREADSHEET_ID=$1
INTERVAL=${2:-300}  # Default 5 minutes

echo "📋 Configuration:"
echo "   Spreadsheet ID: $SPREADSHEET_ID"
echo "   Check Interval: $INTERVAL seconds"
echo "   Monitoring Folders:"
echo "     • CP2000/"
echo "     • CP2000 NEW BATCH 2/"
echo ""
echo "🚀 Starting watcher..."
echo "   Press Ctrl+C to stop"
echo "════════════════════════════════════════════════════════════════"
echo ""

# Run the enhanced watcher
python3 enhanced_auto_watcher.py "$SPREADSHEET_ID" --interval "$INTERVAL"

# Capture exit status
EXIT_STATUS=$?

echo ""
echo "════════════════════════════════════════════════════════════════"
if [ $EXIT_STATUS -eq 0 ]; then
    echo "✅ Watcher stopped successfully"
else
    echo "❌ Watcher stopped with error (exit code: $EXIT_STATUS)"
fi
echo ""

