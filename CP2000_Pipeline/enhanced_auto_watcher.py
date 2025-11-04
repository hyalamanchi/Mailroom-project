#!/usr/bin/env python3
"""
ENHANCED AUTO PIPELINE WATCHER
Monitors CP2000 folders for new files and appends to existing Google Sheet.

FEATURES:
- Monitors local CP2000 folders for new PDF files
- Processes only new files (tracks processed files)
- APPENDS to existing Google Sheet (doesn't create new ones)
- Adds timestamp for each case
- Logs all activities

USAGE:
    python3 enhanced_auto_watcher.py <spreadsheet_id>
    python3 enhanced_auto_watcher.py <spreadsheet_id> --interval 300
    python3 enhanced_auto_watcher.py <spreadsheet_id> --once
"""

import os
import sys
import time
import json
import argparse
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

# Import your existing modules
from hundred_percent_accuracy_extractor import HundredPercentAccuracyExtractor
from logics_case_search import LogicsCaseSearcher


class EnhancedAutoWatcher:
    """Watches CP2000 folders and appends new cases to existing Google Sheet"""
    
    def __init__(self, spreadsheet_id: str, check_interval: int = 300, google_drive_folders: List[str] = None):
        self.spreadsheet_id = spreadsheet_id
        self.check_interval = check_interval
        self.state_file = 'processed_files_tracking.json'
        self.log_file = 'enhanced_watcher.log'
        self.temp_download_folder = 'TEMP_DRIVE_DOWNLOADS'
        
        # Folders to monitor (local)
        self.watch_folders = [
            'CP2000',
            'CP2000 NEW BATCH 2',
            '../CP2000_Production/CP2000 NEW BATCH 2'
        ]
        
        # Google Drive folders to monitor
        self.google_drive_folders = google_drive_folders or []
        
        # Initialize services
        self.sheets_service = self.init_google_sheets()
        self.drive_service = self.init_google_drive() if self.google_drive_folders else None
        self.extractor = HundredPercentAccuracyExtractor()
        self.searcher = LogicsCaseSearcher()
        
        # Create temp download folder if monitoring Google Drive
        if self.google_drive_folders:
            os.makedirs(self.temp_download_folder, exist_ok=True)
        
        # Load processed files state
        self.processed_files = self.load_processed_state()
        
        self.log("✅ Enhanced Auto Watcher initialized")
        if self.google_drive_folders:
            self.log(f"✅ Google Drive monitoring enabled ({len(self.google_drive_folders)} folder(s))")
    
    def init_google_sheets(self):
        """Initialize Google Sheets API"""
        try:
            creds = Credentials.from_authorized_user_file('token.json')
            service = build('sheets', 'v4', credentials=creds)
            self.log("✅ Connected to Google Sheets")
            return service
        except Exception as e:
            self.log(f"❌ Failed to connect to Google Sheets: {e}")
            return None
    
    def init_google_drive(self):
        """Initialize Google Drive API"""
        try:
            creds = Credentials.from_authorized_user_file('token.json')
            service = build('drive', 'v3', credentials=creds)
            self.log("✅ Connected to Google Drive")
            return service
        except Exception as e:
            self.log(f"❌ Failed to connect to Google Drive: {e}")
            return None
    
    def load_processed_state(self) -> Dict:
        """Load list of already processed files"""
        if os.path.exists(self.state_file):
            with open(self.state_file, 'r') as f:
                state = json.load(f)
                # Ensure google_drive_files exists for backward compatibility
                if 'google_drive_files' not in state:
                    state['google_drive_files'] = {}
                return state
        return {'processed_files': {}, 'google_drive_files': {}, 'last_check': None}
    
    def save_processed_state(self):
        """Save processed files state"""
        self.processed_files['last_check'] = datetime.now().isoformat()
        with open(self.state_file, 'w') as f:
            json.dump(self.processed_files, f, indent=2)
    
    def log(self, message: str):
        """Log message to console and file"""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        log_message = f"[{timestamp}] {message}"
        print(log_message)
        
        with open(self.log_file, 'a') as f:
            f.write(log_message + '\n')
    
    def find_new_files(self) -> List[str]:
        """Find new PDF files in monitored folders"""
        new_files = []
        
        for folder in self.watch_folders:
            if not os.path.exists(folder):
                self.log(f"   ⚠️  Folder not found: {folder}")
                continue
            
            for file in os.listdir(folder):
                if not file.lower().endswith('.pdf'):
                    continue
                
                full_path = os.path.join(folder, file)
                
                # Skip if not a file
                if not os.path.isfile(full_path):
                    continue
                
                file_mtime = os.path.getmtime(full_path)
                
                # Check if this file has been processed
                if file not in self.processed_files['processed_files']:
                    new_files.append(full_path)
                    self.log(f"   🆕 New file: {file}")
                elif self.processed_files['processed_files'][file] < file_mtime:
                    # File was modified after processing
                    new_files.append(full_path)
                    self.log(f"   🔄 Modified file: {file}")
        
        return new_files
    
    def find_new_drive_files(self) -> List[Dict]:
        """Find new PDF files in Google Drive folders"""
        new_files = []
        
        if not self.drive_service:
            return new_files
        
        for folder_id in self.google_drive_folders:
            try:
                # List PDF files in the Google Drive folder
                query = f"'{folder_id}' in parents and mimeType='application/pdf' and trashed=false"
                
                results = self.drive_service.files().list(
                    q=query,
                    fields='files(id, name, modifiedTime, size)',
                    pageSize=1000
                ).execute()
                
                files = results.get('files', [])
                
                # Check which files are new
                for file in files:
                    file_id = file['id']
                    
                    # Check if this Drive file has been processed
                    if file_id not in self.processed_files['google_drive_files']:
                        new_files.append(file)
                        self.log(f"   🆕 New Drive file: {file['name']}")
                    
            except Exception as e:
                self.log(f"❌ Error checking Google Drive folder {folder_id}: {e}")
        
        return new_files
    
    def download_drive_file(self, file_info: Dict) -> Optional[str]:
        """Download a file from Google Drive"""
        try:
            file_id = file_info['id']
            file_name = file_info['name']
            
            # Download file content
            request = self.drive_service.files().get_media(fileId=file_id)
            
            # Save to temp folder
            local_path = os.path.join(self.temp_download_folder, file_name)
            
            import io
            fh = io.FileIO(local_path, 'wb')
            
            from googleapiclient.http import MediaIoBaseDownload
            downloader = MediaIoBaseDownload(fh, request)
            
            done = False
            while not done:
                status, done = downloader.next_chunk()
            
            fh.close()
            
            self.log(f"   📥 Downloaded: {file_name}")
            return local_path
            
        except Exception as e:
            self.log(f"❌ Error downloading {file_info.get('name')}: {e}")
            return None
    
    def mark_drive_file_processed(self, file_info: Dict):
        """Mark a Google Drive file as processed"""
        file_id = file_info['id']
        self.processed_files['google_drive_files'][file_id] = {
            'name': file_info['name'],
            'processed_time': datetime.now().isoformat()
        }
        self.save_processed_state()
    
    def process_file(self, file_path: str) -> Optional[Dict]:
        """Process a single PDF file"""
        try:
            self.log(f"   📄 Processing: {os.path.basename(file_path)}")
            
            # Extract data
            extracted_data = self.extractor.extract_100_percent_accuracy_data(file_path)
            if not extracted_data:
                self.log(f"   ⚠️  No data extracted from {file_path}")
                return None
            
            # Search for matching case in Logics
            ssn_last_4 = extracted_data.get('ssn_last_4')
            taxpayer_name = extracted_data.get('taxpayer_name', '')
            
            if ssn_last_4 and taxpayer_name:
                name_parts = taxpayer_name.split(' ', 1)
                last_name = name_parts[-1]
                first_name = name_parts[0] if len(name_parts) > 1 else None
                
                match_result = self.searcher.search_case(
                    last_name=last_name,
                    first_name=first_name,
                    ssn_last_4=ssn_last_4
                )
                
                if match_result:
                    # Extract case ID from nested structure
                    case_id = match_result.get('case_data', {}).get('caseId')
                    extracted_data['logics_case_id'] = case_id
                    extracted_data['logics_case_data'] = match_result
                    extracted_data['match_status'] = 'MATCHED'
                    extracted_data['match_confidence'] = 'High'
                    self.log(f"   ✅ Matched to Case ID: {case_id}")
                else:
                    extracted_data['match_status'] = 'UNMATCHED'
                    extracted_data['match_confidence'] = 'N/A'
                    self.log(f"   ⚠️  No match found in Logics")
            else:
                extracted_data['match_status'] = 'UNMATCHED'
                extracted_data['match_confidence'] = 'N/A'
                self.log(f"   ⚠️  Missing SSN or Name for matching")
            
            # Add processing timestamp
            extracted_data['processed_timestamp'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            extracted_data['filename'] = os.path.basename(file_path)
            
            return extracted_data
            
        except Exception as e:
            self.log(f"   ❌ Error processing {file_path}: {e}")
            import traceback
            self.log(traceback.format_exc())
            return None
    
    def append_to_sheet(self, case_data: Dict, sheet_name: str):
        """Append case data to the appropriate sheet tab"""
        try:
            # Prepare row data with timestamp
            row = [
                str(case_data.get('logics_case_id', 'N/A')),
                case_data.get('filename', 'N/A'),
                self.generate_proposed_filename(case_data),
                (case_data.get('taxpayer_name', 'N/A') or 'N/A').title(),
                str(case_data.get('ssn_last_4', 'N/A')),
                case_data.get('letter_type', 'N/A'),
                str(case_data.get('tax_year', 'N/A')),
                case_data.get('notice_date', 'N/A'),
                case_data.get('response_due_date', 'N/A'),
                'TEMP_PROCESSING',
                case_data.get('match_confidence', 'N/A'),
                '',  # Status - empty for user to fill
                '',  # Notes - empty
                case_data.get('processed_timestamp', 'N/A')  # Timestamp
            ]
            
            # Append to sheet
            range_name = f"{sheet_name}!A:N"
            body = {'values': [row]}
            
            result = self.sheets_service.spreadsheets().values().append(
                spreadsheetId=self.spreadsheet_id,
                range=range_name,
                valueInputOption='USER_ENTERED',
                insertDataOption='INSERT_ROWS',
                body=body
            ).execute()
            
            self.log(f"   ✅ Added to '{sheet_name}' sheet at row {result.get('updates', {}).get('updatedRange', '')}")
            return True
            
        except Exception as e:
            self.log(f"   ❌ Failed to append to sheet: {e}")
            import traceback
            self.log(traceback.format_exc())
            return False
    
    def generate_proposed_filename(self, case: Dict) -> str:
        """Generate proposed filename from case data"""
        letter_type = case.get('letter_type', 'CP2000')
        tax_year = case.get('tax_year', '')
        notice_date = case.get('notice_date', '')
        taxpayer_name = (case.get('taxpayer_name', '') or '').title()
        
        if notice_date and taxpayer_name:
            return f"IRS_CORR_{letter_type}_{tax_year}_DTD_{notice_date}_{taxpayer_name}.pdf"
        
        return case.get('filename', 'N/A')
    
    def mark_file_processed(self, file_path: str):
        """Mark a file as processed"""
        filename = os.path.basename(file_path)
        self.processed_files['processed_files'][filename] = os.path.getmtime(file_path)
        self.save_processed_state()
    
    def watch(self, run_once: bool = False):
        """Main watch loop"""
        self.log("="*70)
        self.log("🔍 ENHANCED AUTO WATCHER STARTED")
        self.log(f"   Spreadsheet: {self.spreadsheet_id}")
        self.log(f"   Check interval: {self.check_interval} seconds")
        self.log(f"   Monitoring local folders: {', '.join(self.watch_folders)}")
        if self.google_drive_folders:
            self.log(f"   Monitoring Google Drive folders: {len(self.google_drive_folders)}")
        self.log(f"   Mode: {'One-time' if run_once else 'Continuous'}")
        self.log("="*70)
        
        iteration = 0
        
        while True:
            iteration += 1
            self.log(f"\n--- Check #{iteration} at {datetime.now().strftime('%H:%M:%S')} ---")
            
            # Find new files
            new_files = self.find_new_files()
            
            if new_files:
                self.log(f"📦 Found {len(new_files)} new file(s) to process")
                
                processed_count = 0
                matched_count = 0
                unmatched_count = 0
                
                for file_path in new_files:
                    case_data = self.process_file(file_path)
                    
                    if case_data:
                        # Determine which sheet to append to
                        if case_data.get('match_status') == 'MATCHED':
                            sheet_name = 'Matched Cases'
                            matched_count += 1
                        else:
                            sheet_name = 'Unmatched Cases'
                            unmatched_count += 1
                        
                        # Append to sheet
                        if self.append_to_sheet(case_data, sheet_name):
                            processed_count += 1
                            self.mark_file_processed(file_path)
                
                self.log(f"\n📊 Local files processing complete:")
                self.log(f"   Total processed: {processed_count}/{len(new_files)}")
                self.log(f"   Matched: {matched_count}")
                self.log(f"   Unmatched: {unmatched_count}")
            else:
                self.log("✅ No new local files found")
            
            # Check Google Drive for new files
            if self.google_drive_folders:
                new_drive_files = self.find_new_drive_files()
                
                if new_drive_files:
                    self.log(f"\n☁️  Found {len(new_drive_files)} new Drive file(s) to process")
                    
                    drive_processed = 0
                    drive_matched = 0
                    drive_unmatched = 0
                    
                    for file_info in new_drive_files:
                        # Download file
                        local_path = self.download_drive_file(file_info)
                        
                        if local_path:
                            # Process the downloaded file
                            case_data = self.process_file(local_path)
                            
                            if case_data:
                                # Determine which sheet to append to
                                if case_data.get('match_status') == 'MATCHED':
                                    sheet_name = 'Matched Cases'
                                    drive_matched += 1
                                else:
                                    sheet_name = 'Unmatched Cases'
                                    drive_unmatched += 1
                                
                                # Append to sheet
                                if self.append_to_sheet(case_data, sheet_name):
                                    drive_processed += 1
                                    self.mark_drive_file_processed(file_info)
                            
                            # Clean up downloaded file
                            try:
                                os.remove(local_path)
                                self.log(f"   🗑️  Cleaned up: {os.path.basename(local_path)}")
                            except:
                                pass
                    
                    self.log(f"\n📊 Drive files processing complete:")
                    self.log(f"   Total processed: {drive_processed}/{len(new_drive_files)}")
                    self.log(f"   Matched: {drive_matched}")
                    self.log(f"   Unmatched: {drive_unmatched}")
                else:
                    self.log("✅ No new Drive files found")
            
            # Save state
            self.save_processed_state()
            
            # Exit if running once
            if run_once:
                self.log("\n🏁 One-time run completed")
                break
            
            # Wait for next check
            self.log(f"\n💤 Next check in {self.check_interval} seconds...")
            time.sleep(self.check_interval)


def main():
    parser = argparse.ArgumentParser(description='Enhanced Auto Watcher - Append to Existing Sheet with Google Drive Support')
    parser.add_argument('spreadsheet_id', help='Google Sheet ID to append to')
    parser.add_argument('--interval', type=int, default=300,
                        help='Check interval in seconds (default: 300)')
    parser.add_argument('--once', action='store_true',
                        help='Run once then exit (default: continuous)')
    parser.add_argument('--drive-folders', nargs='+',
                        help='Google Drive folder IDs to monitor (space-separated)')
    
    args = parser.parse_args()
    
    if not args.spreadsheet_id:
        print("❌ Error: Spreadsheet ID is required")
        print("\nUsage: python3 enhanced_auto_watcher.py <spreadsheet_id> [--drive-folders FOLDER_ID1 FOLDER_ID2]")
        print("Example: python3 enhanced_auto_watcher.py 1abc123xyz456")
        print("Example with Drive: python3 enhanced_auto_watcher.py 1abc123xyz456 --drive-folders 1CGl9pdVWqGssSS3ausbw88MoBWvS65zl")
        sys.exit(1)
    
    # Create watcher
    watcher = EnhancedAutoWatcher(
        spreadsheet_id=args.spreadsheet_id,
        check_interval=args.interval,
        google_drive_folders=args.drive_folders
    )
    
    try:
        watcher.watch(run_once=args.once)
    except KeyboardInterrupt:
        watcher.log("\n\n🛑 Watcher stopped by user")
        sys.exit(0)
    except Exception as e:
        watcher.log(f"\n\n❌ Fatal error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()

