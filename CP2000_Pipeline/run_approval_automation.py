#!/usr/bin/env python3
"""
Run the Sheet Approval Automation
This script helps you easily start the automation that monitors Google Sheets
and automatically processes approved cases.
"""

import sys
import os

# Add current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sheet_approval_automation import SheetApprovalAutomation
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def main():
    print("\n" + "="*70)
    print("🤖 CP2000 SHEET APPROVAL AUTOMATION")
    print("="*70)
    print("\nThis script monitors your Google Sheet for cases with 'APPROVE' status")
    print("and automatically:")
    print("  1. Creates tasks in Logics")
    print("  2. Uploads documents to the case")
    print("  3. Updates the Notes column with status")
    print("\n" + "="*70)
    
    # Get spreadsheet ID from user
    if len(sys.argv) > 1:
        spreadsheet_id = sys.argv[1]
    else:
        print("\n📋 Please provide the Google Sheet ID")
        print("(You can find this in the sheet URL)")
        print("Example: https://docs.google.com/spreadsheets/d/SPREADSHEET_ID/edit")
        print()
        spreadsheet_id = input("Enter Spreadsheet ID: ").strip()
    
    if not spreadsheet_id:
        print("❌ Spreadsheet ID is required!")
        return
    
    # Get mode from user
    if len(sys.argv) > 2:
        mode = sys.argv[2]
    else:
        print("\n🔄 Choose mode:")
        print("  1. monitor - Continuous monitoring (checks every 60 seconds)")
        print("  2. once    - Single check and exit")
        print()
        mode_choice = input("Enter mode (1 or 2) [default: 1]: ").strip()
        mode = 'once' if mode_choice == '2' else 'monitor'
    
    print("\n" + "="*70)
    print(f"📊 Spreadsheet ID: {spreadsheet_id}")
    print(f"🔄 Mode: {mode}")
    print("="*70 + "\n")
    
    try:
        # Initialize automation
        logger.info("🚀 Initializing automation...")
        automation = SheetApprovalAutomation()
        
        if mode == 'once':
            logger.info("🔍 Running single check...")
            count = automation.process_single_check(spreadsheet_id)
            logger.info(f"\n✅ Processed {count} approved cases")
            print("\n" + "="*70)
            print(f"✅ COMPLETED - Processed {count} cases")
            print("="*70 + "\n")
        else:
            logger.info("🔄 Starting continuous monitoring...")
            logger.info("⏱️  Checking every 60 seconds")
            logger.info("🛑 Press Ctrl+C to stop\n")
            automation.monitor_sheet(spreadsheet_id, check_interval=60)
    
    except KeyboardInterrupt:
        print("\n\n" + "="*70)
        print("👋 Automation stopped by user")
        print("="*70 + "\n")
    
    except Exception as e:
        logger.error(f"\n❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
        print("\n" + "="*70)
        print("❌ AUTOMATION FAILED")
        print("="*70)
        print("\nCommon issues:")
        print("  • Make sure token.json exists (run create_review_workbook.py first)")
        print("  • Verify the spreadsheet ID is correct")
        print("  • Check that you have access to the Google Sheet")
        print("  • Ensure the Logics API is accessible")
        print("="*70 + "\n")


if __name__ == "__main__":
    main()

