"""
Complete Case Management Workflow
Integrates case matching, Google Sheet creation, and approval automation
"""

import os
import json
import logging
import subprocess
from datetime import datetime
from typing import Dict, Optional
from case_management_sheet import CaseManagementSheet
from sheet_approval_automation import SheetApprovalAutomation

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class CompleteCaseWorkflow:
    """Orchestrates the complete case management workflow"""
    
    def __init__(self, credentials_path: str = 'credentials.json'):
        """Initialize workflow components"""
        self.credentials_path = credentials_path
        self.sheet_manager = None
        self.automation = None
        
    def run_complete_workflow(self, auto_approve_mode: bool = False):
        """
        Run the complete workflow:
        1. Match cases with Logics
        2. Create folder structure
        3. Create Google Sheets
        4. Optionally start automation
        
        Args:
            auto_approve_mode: If True, start continuous monitoring for approvals
        """
        logger.info("="*80)
        logger.info("🚀 STARTING COMPLETE CASE MANAGEMENT WORKFLOW")
        logger.info("="*80)
        
        try:
            # Step 1: Run case matching
            logger.info("\n📋 STEP 1: Matching cases with Logics system...")
            case_data = self._run_case_matching()
            
            if not case_data:
                logger.error("❌ Case matching failed")
                return False
            
            matched_cases = case_data.get('matched_cases', [])
            unmatched_cases = case_data.get('unmatched_cases', [])
            
            logger.info(f"✅ Matched: {len(matched_cases)} cases")
            logger.info(f"📝 Unmatched: {len(unmatched_cases)} cases")
            
            # Step 2: Initialize Google Services
            logger.info("\n📊 STEP 2: Initializing Google Services...")
            self.sheet_manager = CaseManagementSheet(self.credentials_path)
            
            # Step 3: Create folder structure
            logger.info("\n📁 STEP 3: Creating Google Drive folder structure...")
            folders = self.sheet_manager.create_case_folders()
            
            if not folders:
                logger.error("❌ Failed to create folders")
                return False
            
            logger.info(f"✅ Created folders:")
            logger.info(f"   Batch: {folders['batch']}")
            logger.info(f"   Matched: {folders['matched']}")
            logger.info(f"   Unmatched: {folders['unmatched']}")
            
            # Step 4: Create Google Sheets
            logger.info("\n📈 STEP 4: Creating Google Sheets...")
            
            matched_sheet_id = None
            unmatched_sheet_id = None
            
            if matched_cases:
                logger.info(f"Creating matched cases sheet ({len(matched_cases)} cases)...")
                matched_sheet_id = self.sheet_manager.create_matched_cases_sheet(
                    matched_cases,
                    folders['matched']
                )
                
                if matched_sheet_id:
                    matched_url = f"https://docs.google.com/spreadsheets/d/{matched_sheet_id}"
                    logger.info(f"✅ Matched Cases Sheet: {matched_url}")
                else:
                    logger.error("❌ Failed to create matched cases sheet")
            
            if unmatched_cases:
                logger.info(f"Creating unmatched cases sheet ({len(unmatched_cases)} cases)...")
                unmatched_sheet_id = self.sheet_manager.create_unmatched_cases_sheet(
                    unmatched_cases,
                    folders['unmatched']
                )
                
                if unmatched_sheet_id:
                    unmatched_url = f"https://docs.google.com/spreadsheets/d/{unmatched_sheet_id}"
                    logger.info(f"✅ Unmatched Cases Sheet: {unmatched_url}")
                else:
                    logger.error("❌ Failed to create unmatched cases sheet")
            
            # Step 5: Save workflow summary
            logger.info("\n💾 STEP 5: Saving workflow summary...")
            self._save_workflow_summary(
                folders, matched_sheet_id, unmatched_sheet_id,
                len(matched_cases), len(unmatched_cases)
            )
            
            # Step 6: Process approvals or start monitoring
            if matched_sheet_id:
                logger.info("\n🔄 STEP 6: Setting up approval automation...")
                
                self.automation = SheetApprovalAutomation(self.credentials_path)
                
                if auto_approve_mode:
                    logger.info("🔁 Starting continuous monitoring for approvals...")
                    logger.info("💡 Change cell values in column A to 'Approve' to process cases")
                    logger.info("⏹️  Press Ctrl+C to stop monitoring")
                    self.automation.monitor_sheet(matched_sheet_id, check_interval=30)
                else:
                    logger.info("🔍 Checking for pre-approved cases...")
                    processed = self.automation.process_single_check(matched_sheet_id)
                    logger.info(f"✅ Processed {processed} approved cases")
                    
                    if processed == 0:
                        logger.info("\n💡 To process approvals:")
                        logger.info("   1. Open the matched cases sheet")
                        logger.info("   2. Set status column to 'Approve' for cases to process")
                        logger.info("   3. Run automation with:")
                        logger.info(f"      python sheet_approval_automation.py {matched_sheet_id} once")
                        logger.info("   Or for continuous monitoring:")
                        logger.info(f"      python sheet_approval_automation.py {matched_sheet_id} monitor")
            
            # Final summary
            logger.info("\n" + "="*80)
            logger.info("✅ WORKFLOW COMPLETED SUCCESSFULLY!")
            logger.info("="*80)
            logger.info(f"\n📊 Summary:")
            logger.info(f"   Total Matched Cases: {len(matched_cases)}")
            logger.info(f"   Total Unmatched Cases: {len(unmatched_cases)}")
            if matched_sheet_id:
                logger.info(f"   Matched Sheet: https://docs.google.com/spreadsheets/d/{matched_sheet_id}")
            if unmatched_sheet_id:
                logger.info(f"   Unmatched Sheet: https://docs.google.com/spreadsheets/d/{unmatched_sheet_id}")
            logger.info("\n")
            
            return True
            
        except KeyboardInterrupt:
            logger.info("\n⏹️  Workflow stopped by user")
            return False
        except Exception as e:
            logger.error(f"❌ Workflow failed: {str(e)}")
            import traceback
            traceback.print_exc()
            return False
    
    def _run_case_matching(self) -> Optional[Dict]:
        """Run the case matching process"""
        try:
            # Import and run case matching
            from case_id_extractor import process_cases
            
            # Check if we have extracted data
            import glob
            data_files = glob.glob('LOGICS_DATA_*.json')
            
            if not data_files:
                logger.error("❌ No extracted data files found. Run extraction first.")
                return None
            
            # Run case matching
            logger.info("🔍 Running case matching...")
            process_cases()
            
            # Find the latest match file
            match_files = glob.glob('CASE_MATCHES_*.json')
            if not match_files:
                logger.error("❌ No case match files generated")
                return None
            
            latest_match_file = max(match_files)
            logger.info(f"📄 Loading results from: {latest_match_file}")
            
            with open(latest_match_file, 'r') as f:
                data = json.load(f)
            
            return data
            
        except Exception as e:
            logger.error(f"❌ Case matching error: {str(e)}")
            return None
    
    def _save_workflow_summary(self, folders: Dict, matched_sheet_id: Optional[str],
                               unmatched_sheet_id: Optional[str],
                               matched_count: int, unmatched_count: int):
        """Save workflow execution summary"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            summary_file = f"WORKFLOW_SUMMARY_{timestamp}.json"
            
            summary = {
                'timestamp': datetime.now().isoformat(),
                'folders': folders,
                'sheets': {
                    'matched': matched_sheet_id,
                    'unmatched': unmatched_sheet_id
                },
                'counts': {
                    'matched': matched_count,
                    'unmatched': unmatched_count,
                    'total': matched_count + unmatched_count
                },
                'urls': {
                    'matched_sheet': f"https://docs.google.com/spreadsheets/d/{matched_sheet_id}" if matched_sheet_id else None,
                    'unmatched_sheet': f"https://docs.google.com/spreadsheets/d/{unmatched_sheet_id}" if unmatched_sheet_id else None
                }
            }
            
            with open(summary_file, 'w') as f:
                json.dump(summary, f, indent=2)
            
            logger.info(f"💾 Workflow summary saved: {summary_file}")
            
        except Exception as e:
            logger.error(f"❌ Failed to save summary: {str(e)}")


def main():
    """Main entry point"""
    import sys
    
    print("\n" + "="*80)
    print("🎯 CP2000 CASE MANAGEMENT WORKFLOW")
    print("="*80)
    print("\nThis workflow will:")
    print("  1. Match cases with Logics system")
    print("  2. Create Google Drive folder structure")
    print("  3. Generate Google Sheets for matched and unmatched cases")
    print("  4. Set up approval automation")
    print("\n" + "="*80)
    
    # Check for credentials
    if not os.path.exists('credentials.json'):
        print("\n❌ Error: credentials.json not found")
        print("💡 Please ensure your Google credentials file is in the current directory")
        return
    
    # Ask for mode
    print("\n📋 Select mode:")
    print("  1. Run workflow and exit (manual approval in sheets)")
    print("  2. Run workflow and start continuous monitoring")
    
    try:
        choice = input("\nEnter choice (1 or 2): ").strip()
        
        auto_monitor = (choice == '2')
        
        print("\n🚀 Starting workflow...\n")
        
        workflow = CompleteCaseWorkflow()
        success = workflow.run_complete_workflow(auto_approve_mode=auto_monitor)
        
        if success:
            print("\n✅ Workflow completed successfully!")
        else:
            print("\n❌ Workflow completed with errors")
            
    except KeyboardInterrupt:
        print("\n\n⏹️  Workflow cancelled by user")
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")


if __name__ == "__main__":
    main()

