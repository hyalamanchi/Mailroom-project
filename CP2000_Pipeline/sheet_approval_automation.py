"""
Sheet Approval Automation
Monitors Google Sheet for approved cases and automatically:
1. Creates tasks in Logics
2. Uploads documents to proper case IDs
"""

import os
import json
import time
import logging
from datetime import datetime
from typing import List, Dict, Optional
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
import requests

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SheetApprovalAutomation:
    """Automates task creation and document upload when cases are approved in Google Sheet"""
    
    def __init__(self, credentials_path: str = 'credentials.json'):
        """Initialize with Google credentials and Logics API"""
        try:
            # Google Services
            self.credentials = service_account.Credentials.from_service_account_file(
                credentials_path,
                scopes=[
                    'https://www.googleapis.com/auth/spreadsheets',
                    'https://www.googleapis.com/auth/drive.file'
                ]
            )
            
            self.sheets_service = build('sheets', 'v4', credentials=self.credentials)
            self.drive_service = build('drive', 'v3', credentials=self.credentials)
            
            # Logics API Configuration
            self.api_key = os.environ.get('LOGICS_API_KEY', "sk_BIWGmwZeahwOyI9ytZNMnZmM_mY1SOcpl4OXlmFpJvA")
            self.base_url = "https://tiparser-dev.onrender.com/case-data/api"
            self.headers = {
                "Content-Type": "application/json",
                "X-API-Key": self.api_key
            }
            
            logger.info("✅ Automation system initialized successfully")
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize automation: {str(e)}")
            raise
    
    def monitor_sheet(self, spreadsheet_id: str, check_interval: int = 60):
        """
        Monitor Google Sheet for approved cases and process them
        
        Args:
            spreadsheet_id: ID of the Google Sheet to monitor
            check_interval: Seconds between checks (default 60)
        """
        logger.info(f"🔍 Starting to monitor sheet: {spreadsheet_id}")
        logger.info(f"⏱️ Check interval: {check_interval} seconds")
        
        processed_rows = set()  # Track processed rows to avoid duplicates
        
        while True:
            try:
                # Read sheet data
                result = self.sheets_service.spreadsheets().values().get(
                    spreadsheetId=spreadsheet_id,
                    range='Matched Cases!A2:T1000'  # Skip header row
                ).execute()
                
                values = result.get('values', [])
                
                if not values:
                    logger.info("No data found in sheet")
                    time.sleep(check_interval)
                    continue
                
                # Process each row
                for idx, row in enumerate(values, start=2):  # Start at row 2 (after header)
                    if len(row) < 13:  # Minimum required columns
                        continue
                    
                    row_key = f"{idx}_{row[1] if len(row) > 1 else ''}"  # Row index + Case ID
                    
                    # Check if this row was already processed
                    if row_key in processed_rows:
                        continue
                    
                    status = row[0] if len(row) > 0 else ''
                    
                    # Process if approved
                    if status.strip().lower() == 'approve':
                        logger.info(f"\n{'='*60}")
                        logger.info(f"✅ APPROVED case found in row {idx}")
                        
                        success = self._process_approved_case(row, idx, spreadsheet_id)
                        
                        if success:
                            processed_rows.add(row_key)
                            logger.info(f"✅ Successfully processed row {idx}")
                        else:
                            logger.error(f"❌ Failed to process row {idx}")
                
                logger.info(f"✓ Check completed at {datetime.now().strftime('%H:%M:%S')}")
                time.sleep(check_interval)
                
            except KeyboardInterrupt:
                logger.info("\n⏹️ Monitoring stopped by user")
                break
            except Exception as e:
                logger.error(f"❌ Error during monitoring: {str(e)}")
                time.sleep(check_interval)
    
    def process_single_check(self, spreadsheet_id: str) -> int:
        """
        Process approved cases once (single check, no monitoring loop)
        
        Args:
            spreadsheet_id: ID of the Google Sheet
            
        Returns:
            Number of cases processed
        """
        processed_count = 0
        
        try:
            # Read sheet data
            result = self.sheets_service.spreadsheets().values().get(
                spreadsheetId=spreadsheet_id,
                range='Matched Cases!A2:T1000'
            ).execute()
            
            values = result.get('values', [])
            
            if not values:
                logger.info("No data found in sheet")
                return 0
            
            # Process each row
            for idx, row in enumerate(values, start=2):
                if len(row) < 13:
                    continue
                
                status = row[0] if len(row) > 0 else ''
                processing_status = row[18] if len(row) > 18 else ''
                
                # Process if approved and not already processed
                if status.strip().lower() == 'approve' and processing_status != 'Completed':
                    logger.info(f"\n{'='*60}")
                    logger.info(f"✅ Processing approved case in row {idx}")
                    
                    success = self._process_approved_case(row, idx, spreadsheet_id)
                    
                    if success:
                        processed_count += 1
                        logger.info(f"✅ Successfully processed row {idx}")
            
            logger.info(f"\n📊 Processed {processed_count} approved cases")
            return processed_count
            
        except Exception as e:
            logger.error(f"❌ Error during processing: {str(e)}")
            return processed_count
    
    def _process_approved_case(self, row: List, row_idx: int, spreadsheet_id: str) -> bool:
        """Process a single approved case"""
        try:
            # Extract case data
            case_id = row[1] if len(row) > 1 else ''
            taxpayer_name = row[2] if len(row) > 2 else ''
            tax_year = row[6] if len(row) > 6 else ''
            notice_date = row[7] if len(row) > 7 else ''
            response_due_date = row[8] if len(row) > 8 else ''
            notice_ref_number = row[11] if len(row) > 11 else ''
            filename = row[12] if len(row) > 12 else ''
            
            logger.info(f"📋 Case Details:")
            logger.info(f"   Case ID: {case_id}")
            logger.info(f"   Name: {taxpayer_name}")
            logger.info(f"   File: {filename}")
            
            # Update processing status
            self._update_cell_status(spreadsheet_id, row_idx, 'S', 'Processing...')
            
            # Step 1: Create task in Logics
            logger.info("📝 Creating task in Logics...")
            task_created = self._create_task(
                case_id, notice_date, tax_year, notice_ref_number, response_due_date
            )
            
            if not task_created:
                self._update_cell_status(spreadsheet_id, row_idx, 'S', 'Task Creation Failed')
                self._update_cell_status(spreadsheet_id, row_idx, 'T', 'Not Uploaded')
                return False
            
            # Step 2: Upload document
            logger.info("📤 Uploading document to Logics...")
            doc_uploaded = self._upload_document(case_id, filename, tax_year)
            
            if doc_uploaded:
                self._update_cell_status(spreadsheet_id, row_idx, 'S', 'Completed')
                self._update_cell_status(spreadsheet_id, row_idx, 'T', 'Uploaded Successfully')
                logger.info("✅ Case processing completed successfully!")
                return True
            else:
                self._update_cell_status(spreadsheet_id, row_idx, 'S', 'Task Created')
                self._update_cell_status(spreadsheet_id, row_idx, 'T', 'Upload Failed')
                logger.warning("⚠️ Task created but document upload failed")
                return True  # Still consider it successful since task was created
            
        except Exception as e:
            logger.error(f"❌ Error processing case: {str(e)}")
            try:
                self._update_cell_status(spreadsheet_id, row_idx, 'S', f'Error: {str(e)[:50]}')
            except:
                pass
            return False
    
    def _create_task(self, case_id: str, notice_date: str, tax_year: str, 
                    ref_number: str, due_date: str) -> bool:
        """Create task in Logics system"""
        try:
            url = f"{self.base_url}/tasks/create"
            
            payload = {
                'caseId': int(case_id),
                'taskType': 'CP2000_REVIEW',
                'priority': 'HIGH',
                'dueDate': due_date or notice_date,
                'title': f'CP2000 Notice Review - Tax Year {tax_year}',
                'description': f'Review and respond to CP2000 notice. Notice Date: {notice_date}, Reference: {ref_number}',
                'details': {
                    'taxYear': tax_year,
                    'noticeDate': notice_date,
                    'referenceNumber': ref_number,
                    'noticeType': 'CP2000',
                    'status': 'NEW',
                    'source': 'Automated Pipeline'
                }
            }
            
            logger.debug(f"Task payload: {json.dumps(payload, indent=2)}")
            
            response = requests.post(url, headers=self.headers, json=payload, timeout=30)
            
            if response.status_code in [200, 201]:
                logger.info(f"✅ Task created successfully for Case {case_id}")
                return True
            else:
                logger.error(f"❌ Task creation failed: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Error creating task: {str(e)}")
            return False
    
    def _upload_document(self, case_id: str, filename: str, tax_year: str) -> bool:
        """Upload document to Logics case"""
        try:
            # Find the document file
            file_path = self._find_document(filename)
            
            if not file_path:
                logger.error(f"❌ Document not found: {filename}")
                return False
            
            url = f"{self.base_url}/documents/upload"
            
            # Prepare multipart upload
            with open(file_path, 'rb') as file:
                files = {
                    'file': (os.path.basename(file_path), file, 'application/pdf')
                }
                
                data = {
                    'caseId': case_id,
                    'documentType': 'CP2000',
                    'taxYear': tax_year,
                    'description': f'CP2000 Notice - Tax Year {tax_year}',
                    'category': 'IRS_CORRESPONDENCE'
                }
                
                # Note: Remove Content-Type header for multipart/form-data
                headers = {"X-API-Key": self.api_key}
                
                response = requests.post(
                    url,
                    headers=headers,
                    data=data,
                    files=files,
                    timeout=60
                )
            
            if response.status_code in [200, 201]:
                logger.info(f"✅ Document uploaded successfully for Case {case_id}")
                return True
            else:
                logger.error(f"❌ Document upload failed: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Error uploading document: {str(e)}")
            return False
    
    def _find_document(self, filename: str) -> Optional[str]:
        """Find document file in various possible locations"""
        search_paths = [
            '.',
            'CP2000',
            'CP2000 NEW BATCH 2',
            'PROCESSED_FILES',
            '../CP2000_Production'
        ]
        
        for path in search_paths:
            full_path = os.path.join(path, filename)
            if os.path.exists(full_path):
                logger.info(f"📁 Found document: {full_path}")
                return full_path
        
        return None
    
    def _update_cell_status(self, spreadsheet_id: str, row_idx: int, 
                           column: str, value: str):
        """Update a specific cell in the sheet"""
        try:
            range_name = f"Matched Cases!{column}{row_idx}"
            
            self.sheets_service.spreadsheets().values().update(
                spreadsheetId=spreadsheet_id,
                range=range_name,
                valueInputOption='RAW',
                body={'values': [[value]]}
            ).execute()
            
            logger.debug(f"Updated {range_name} = {value}")
            
        except Exception as e:
            logger.error(f"❌ Failed to update cell: {str(e)}")


def main():
    """Main function to run the automation"""
    import sys
    
    if len(sys.argv) < 2:
        print("\n📋 Usage:")
        print("  python sheet_approval_automation.py <spreadsheet_id> [mode]")
        print("\nModes:")
        print("  monitor  - Continuous monitoring (default)")
        print("  once     - Single check and process")
        print("\nExample:")
        print("  python sheet_approval_automation.py 1abc123xyz456 monitor")
        print("  python sheet_approval_automation.py 1abc123xyz456 once")
        return
    
    spreadsheet_id = sys.argv[1]
    mode = sys.argv[2] if len(sys.argv) > 2 else 'monitor'
    
    try:
        automation = SheetApprovalAutomation()
        
        if mode == 'once':
            logger.info("🔄 Running single check...")
            count = automation.process_single_check(spreadsheet_id)
            logger.info(f"✅ Processed {count} approved cases")
        else:
            logger.info("🔄 Starting continuous monitoring...")
            logger.info("Press Ctrl+C to stop")
            automation.monitor_sheet(spreadsheet_id, check_interval=60)
            
    except KeyboardInterrupt:
        logger.info("\n👋 Automation stopped by user")
    except Exception as e:
        logger.error(f"❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()

