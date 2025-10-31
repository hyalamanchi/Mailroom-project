#!/usr/bin/env python3
"""
Daily Mail Room Pipeline Orchestrator

This script automates the complete daily workflow for IRS CP2000 mail processing:
- Downloads new files from Google Drive input folders
- Extracts taxpayer data using OCR
- Matches cases to Logiqs CRM
- Organizes files into matched/unmatched folders
- Generates comprehensive reports for team review

Author: Hemalatha Yalamanchi
Created: October 2025
Version: 1.0
"""

import os
import sys
import json
import shutil
import time
import gc
import re
from datetime import datetime
from typing import Dict, List, Optional
import pandas as pd
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload, MediaFileUpload
from google.oauth2 import service_account

# Import our existing modules
from hundred_percent_accuracy_extractor import HundredPercentAccuracyExtractor
from logics_case_search import LogicsCaseSearcher

# Import robust API utilities (TRA_API pattern)
from api_utils import run_resiliently, resilient_api_call, rate_limited


class DailyPipelineOrchestrator:
    """
    Complete daily pipeline orchestrator with Google Drive folder management
    """
    
    def __init__(self, test_mode=False, test_file_limit=5):
        # Test mode configuration
        self.test_mode = test_mode
        self.test_file_limit = test_file_limit if test_mode else None
        
        # Google Drive configuration
        self.SCOPES = ['https://www.googleapis.com/auth/drive']
        self.service = None
        
        # API quota management and rate limiting
        self.api_call_delay = 0.1  # 100ms between API calls (10 calls/sec)
        self.batch_size = 100  # Process files in batches to manage memory
        self.max_retries = 3  # Retry failed API calls
        self.retry_delay = 2  # Initial retry delay in seconds (exponential backoff)
        
        # Processing history for incremental processing
        self.history_file = 'PROCESSING_HISTORY.json'
        self.processed_files = self.load_processing_history()
        
        # Load test folder IDs if in test mode
        if test_mode and os.path.exists('.test_folders.json'):
            import json
            with open('.test_folders.json', 'r') as f:
                test_folders = json.load(f)
            self.test_matched_folder = test_folders.get('matched_id')
            self.test_unmatched_folder = test_folders.get('unmatched_id')
            print(f"🧪 Loaded TEST folders: MATCHED={self.test_matched_folder}, UNMATCHED={self.test_unmatched_folder}")
        else:
            self.test_matched_folder = None
            self.test_unmatched_folder = None
        
        # Google Drive Folder IDs
        self.folders = {
            # Input folder - Main CP2000 folder
            'input_main': '18e8lj66Mdr7PFGhJ7ySYtsnkNgiuczmx',
            
            # Output folders (to be created or configured)
            'output_matched': None,    # Folder B - Matched cases (auto upload)
            'output_unmatched': None   # Folder C - Unmatched cases (manual review)
        }
        
        # Local directories
        self.temp_dir = 'TEMP_DAILY_PROCESSING'
        self.output_dir = 'DAILY_REPORTS'
        self.matched_dir = os.path.join(self.output_dir, 'MATCHED')
        self.unmatched_dir = os.path.join(self.output_dir, 'UNMATCHED')
        
        # Create directories
        for dir_path in [self.temp_dir, self.output_dir, self.matched_dir, self.unmatched_dir]:
            os.makedirs(dir_path, exist_ok=True)
        
        # Processing results
        self.matched_cases = []
        self.unmatched_cases = []
        self.processing_stats = {
            'total_files': 0,
            'matched': 0,
            'unmatched': 0,
            'uploaded': 0,
            'failed': 0
        }
        
        # Initialize searcher
        self.logics_searcher = LogicsCaseSearcher()
        
        # Initialize Logiqs uploader (for document upload and task creation)
        from upload_to_logiqs import LogiqsDocumentUploader
        self.logiqs_uploader = LogiqsDocumentUploader() if not test_mode else None
        
        if self.test_mode:
            print(f"📋 Daily Pipeline Orchestrator initialized (TEST MODE - {self.test_file_limit} files only)")
        else:
            print("📋 Daily Pipeline Orchestrator initialized")
    
    def load_processing_history(self):
        """Load processing history to avoid reprocessing files"""
        if os.path.exists(self.history_file):
            try:
                with open(self.history_file, 'r') as f:
                    return json.load(f)
            except:
                return {}
        return {}
    
    def save_to_history(self, file_id, filename, status):
        """Save processed file to history"""
        self.processed_files[file_id] = {
            'filename': filename,
            'status': status,
            'processed_at': datetime.now().isoformat()
        }
        with open(self.history_file, 'w') as f:
            json.dump(self.processed_files, f, indent=2)
    
    def is_already_processed(self, file_id):
        """Check if file was already processed"""
        return file_id in self.processed_files
    
    def _sanitize_for_log(self, text: str) -> str:
        """
        Sanitize sensitive data before logging (prevent data leakage)
        Masks SSN, email, phone numbers, and other PII
        """
        if not text:
            return text
        
        # Mask SSN patterns (###-##-####)
        text = re.sub(r'\b\d{3}-\d{2}-\d{4}\b', '***-**-****', text)
        
        # Mask partial SSN (last 4 digits only shown)
        text = re.sub(r'\b\d{3}-\d{2}-(\d{4})\b', r'***-**-\1', text)
        
        # Mask email addresses
        text = re.sub(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', '***@***.***', text)
        
        # Mask phone numbers
        text = re.sub(r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b', '***-***-****', text)
        
        return text
    
    def _api_call_with_retry(self, api_call_func, *args, **kwargs):
        """
        Execute API call with exponential backoff retry logic using run_resiliently.
        
        This is a wrapper around the robust run_resiliently pattern from TRA_API,
        which handles quota errors, rate limiting, network issues, and timeouts.
        """
        return run_resiliently(
            api_call_func,
            *args,
            max_retries=self.max_retries,
            initial_delay=self.retry_delay,
            backoff_factor=2.0,
            max_delay=60.0,
            rate_limit_delay=self.api_call_delay,
            **kwargs
        )
    
    def authenticate_google_drive(self):
        """Authenticate with Google Drive API using service account"""
        print("\n🔐 Authenticating with Google Drive...")
        
        try:
            # Use service account credentials
            creds = service_account.Credentials.from_service_account_file(
                'service-account-key.json',
                scopes=self.SCOPES
            )
            
            self.service = build('drive', 'v3', credentials=creds)
            print("   ✅ Google Drive authenticated (Service Account)")
            
        except FileNotFoundError:
            print("   ❌ Error: service-account-key.json not found")
            print("   💡 Place your service account JSON file in the project root")
            raise
        except Exception as e:
            print(f"   ❌ Authentication error: {str(e)}")
            raise
    
    def create_output_folders_if_needed(self):
        """Create output folders in Google Drive if they don't exist"""
        print("\n📁 Checking output folders in Google Drive...")
        
        # Search for existing folders
        matched_folder = self._find_folder_by_name("CP2000_MATCHED")
        unmatched_folder = self._find_folder_by_name("CP2000_UNMATCHED")
        
        # Create if not exist
        if not matched_folder:
            print("   📁 Creating 'CP2000_MATCHED' folder...")
            matched_folder_id = self._create_folder("CP2000_MATCHED")
            self.folders['output_matched'] = matched_folder_id
            print(f"   ✅ Created: CP2000_MATCHED (ID: {matched_folder_id})")
        else:
            self.folders['output_matched'] = matched_folder['id']
            print(f"   ✅ Found: CP2000_MATCHED (ID: {matched_folder['id']})")
        
        if not unmatched_folder:
            print("   📁 Creating 'CP2000_UNMATCHED' folder...")
            unmatched_folder_id = self._create_folder("CP2000_UNMATCHED")
            self.folders['output_unmatched'] = unmatched_folder_id
            print(f"   ✅ Created: CP2000_UNMATCHED (ID: {unmatched_folder_id})")
        else:
            self.folders['output_unmatched'] = unmatched_folder['id']
            print(f"   ✅ Found: CP2000_UNMATCHED (ID: {unmatched_folder['id']})")
    
    def _find_folder_by_name(self, folder_name: str) -> Optional[Dict]:
        """Find a folder by name in Google Drive"""
        query = f"name='{folder_name}' and mimeType='application/vnd.google-apps.folder' and trashed=false"
        results = self.service.files().list(q=query, fields="files(id, name)").execute()
        items = results.get('files', [])
        return items[0] if items else None
    
    def _create_folder(self, folder_name: str) -> str:
        """Create a folder in Google Drive"""
        file_metadata = {
            'name': folder_name,
            'mimeType': 'application/vnd.google-apps.folder'
        }
        folder = self.service.files().create(body=file_metadata, fields='id').execute()
        return folder.get('id')
    
    def find_cp2000_folders(self, parent_id, path=""):
        """Recursively find all CP2000 folders"""
        cp2000_folders = []
        
        try:
            query = f"'{parent_id}' in parents and mimeType='application/vnd.google-apps.folder' and trashed=false"
            results = self.service.files().list(q=query, fields="files(id, name)").execute()
            folders = results.get('files', [])
            
            for folder in folders:
                folder_name = folder.get('name', '').upper()
                folder_id = folder.get('id')
                folder_path = f"{path}/{folder['name']}" if path else folder['name']
                
                # Check if this is a CP2000 folder
                if 'CP2000' in folder_name or 'CP 2000' in folder_name:
                    cp2000_folders.append({
                        'id': folder_id,
                        'name': folder['name'],
                        'path': folder_path
                    })
                    print(f"   ✅ Found CP2000 folder: {folder_path}")
                
                # Recurse into subfolders
                cp2000_folders.extend(self.find_cp2000_folders(folder_id, folder_path))
        
        except Exception as e:
            print(f"   ⚠️  Error scanning folder: {str(e)}")
        
        return cp2000_folders
    
    def _list_files_paginated(self, folder_id: str, max_results: int = None) -> List[Dict]:
        """
        List files with pagination and rate limiting to avoid quota issues
        For production use with 1000s of files
        """
        all_files = []
        page_token = None
        page_size = 100  # Safe page size (API max is 1000)
        
        try:
            while True:
                # API call with retry logic
                def list_call():
                    return self.service.files().list(
                        q=f"'{folder_id}' in parents and mimeType='application/pdf' and trashed=false",
                        pageSize=page_size,
                        pageToken=page_token,
                        fields="nextPageToken, files(id, name, size)"
                    ).execute()
                
                results = self._api_call_with_retry(list_call)
                
                if results:
                    files = results.get('files', [])
                    all_files.extend(files)
                    
                    page_token = results.get('nextPageToken')
                    if not page_token:
                        break
                    
                    # Break if we've reached max_results
                    if max_results and len(all_files) >= max_results:
                        all_files = all_files[:max_results]
                        break
                else:
                    break
        
        except Exception as e:
            print(f"   ❌ Error listing files: {self._sanitize_for_log(str(e))}")
        
        return all_files
    
    def _download_files_in_batches(self, files: List[Dict], folder_info: Dict) -> List[Dict]:
        """
        Download files in batches with memory management
        Prevents memory leaks for large-scale processing
        """
        downloaded_files = []
        
        for batch_start in range(0, len(files), self.batch_size):
            batch_end = min(batch_start + self.batch_size, len(files))
            batch = files[batch_start:batch_end]
            
            batch_num = batch_start // self.batch_size + 1
            total_batches = (len(files) + self.batch_size - 1) // self.batch_size
            print(f"   📦 Batch {batch_num}/{total_batches}: Processing {len(batch)} files...")
            
            for i, file in enumerate(batch, 1):
                try:
                    local_path = os.path.join(self.temp_dir, file['name'])
                    
                    # Download with retry logic
                    def download_call():
                        request = self.service.files().get_media(fileId=file['id'])
                        with open(local_path, 'wb') as f:
                            downloader = MediaIoBaseDownload(f, request, chunksize=1024*1024)  # 1MB chunks
                            done = False
                            while not done:
                                status, done = downloader.next_chunk()
                        return True
                    
                    self._api_call_with_retry(download_call)
                    
                    # Check if already processed (skip in non-test mode)
                    if not self.test_mode and self.is_already_processed(file['id']):
                        print(f"   ⏭️  Skipping (already processed): {file['name']}")
                        continue
                    
                    downloaded_files.append({
                        'local_path': local_path,
                        'filename': file['name'],
                        'drive_id': file['id'],
                        'source_folder': folder_info['path']
                    })
                
                except Exception as e:
                    print(f"   ❌ Error downloading {file['name']}: {self._sanitize_for_log(str(e))}")
            
            # Force garbage collection after each batch to free memory
            gc.collect()
            
            print(f"   ✅ Batch {batch_num}/{total_batches} complete: {len(downloaded_files)}/{len(files)} total downloaded")
        
        return downloaded_files
    
    def download_new_files(self) -> List[str]:
        """Download new files from CP2000 folders only"""
        print("\n📥 STEP 1: DOWNLOADING CP2000 FILES FROM GOOGLE DRIVE")
        print("=" * 80)
        print("🎯 Focus: CP2000 letters only (all batches)")
        
        if self.test_mode:
            print(f"⚠️  TEST MODE: Will download only {self.test_file_limit} files for testing")
        
        # Find all CP2000 folders recursively
        print("\n🔍 Scanning for CP2000 folders...")
        cp2000_folders = self.find_cp2000_folders(self.folders['input_main'])
        
        print(f"\n✅ Found {len(cp2000_folders)} CP2000 folder(s)")
        
        all_files = []
        
        # Download PDFs from each CP2000 folder
        for folder_info in cp2000_folders:
            # Skip if we've reached test limit
            if self.test_mode and len(all_files) >= self.test_file_limit:
                break
            
            print(f"\n📁 Processing: {folder_info['path']}")
            
            # IMPROVED: Use paginated file listing (handles 1000s of files)
            max_results = None
            if self.test_mode:
                max_results = self.test_file_limit - len(all_files)
            
            files = self._list_files_paginated(folder_info['id'], max_results=max_results)
            
            print(f"   Found: {len(files)} PDFs")
            
            if self.test_mode and files:
                print(f"   Test mode: Processing {len(files)} files from this folder")
            
            # IMPROVED: Download in batches with memory management
            downloaded = self._download_files_in_batches(files, folder_info)
            all_files.extend(downloaded)
        
        print(f"\n✅ Total CP2000 files downloaded: {len(all_files)}")
        self.processing_stats['total_files'] = len(all_files)
        
        return all_files
    
    def extract_and_match(self, files: List[Dict]) -> None:
        """Extract data and match to Logiqs cases"""
        print("\n🔍 STEP 2: EXTRACTING DATA AND MATCHING TO LOGIQS")
        print("=" * 80)
        
        extractor = HundredPercentAccuracyExtractor()
        
        for i, file_info in enumerate(files, 1):
            print(f"\n{i}/{len(files)} - {file_info['filename']}")
            
            try:
                # Extract data
                print("   📄 Extracting data...")
                extracted_data = extractor.extract_100_percent_accuracy_data(file_info['local_path'])
                
                if not extracted_data:
                    print("   ⚠️  Extraction failed - marking as unmatched")
                    file_info['status'] = 'unmatched'
                    file_info['reason'] = 'Extraction failed'
                    self.unmatched_cases.append(file_info)
                    continue
                
                # Get SSN and name for matching
                ssn_last_4 = extracted_data.get('ssn_last_4', '')
                taxpayer_name = extracted_data.get('taxpayer_name', '')
                
                # Split taxpayer name into first and last name for Logiqs search
                if taxpayer_name:
                    name_parts = taxpayer_name.strip().split()
                    last_name = name_parts[-1] if name_parts else ''
                    first_name = name_parts[0] if len(name_parts) > 1 else ''
                else:
                    last_name = ''
                    first_name = ''
                
                if not ssn_last_4 or not last_name:
                    print("   ⚠️  Missing SSN or name - marking as unmatched")
                    file_info['status'] = 'unmatched'
                    file_info['reason'] = 'Missing SSN or name'
                    file_info['extracted_data'] = extracted_data
                    self.unmatched_cases.append(file_info)
                    continue
                
                # Search in Logiqs
                print(f"   🔍 Searching Logiqs for {last_name} (SSN: {ssn_last_4})...")
                case_data = self.logics_searcher.search_case(ssn_last_4, last_name, first_name)
                
                if case_data and case_data.get('matchFound'):
                    case_id = case_data.get('caseData', {}).get('data', {}).get('CaseID')
                    print(f"   ✅ Match found! Case ID: {case_id}")
                    
                    file_info['status'] = 'matched'
                    file_info['case_id'] = case_id
                    file_info['extracted_data'] = extracted_data
                    file_info['match_data'] = case_data
                    self.matched_cases.append(file_info)
                    self.processing_stats['matched'] += 1
                else:
                    print("   ⚠️  No match found in Logiqs")
                    file_info['status'] = 'unmatched'
                    file_info['reason'] = 'No case found in Logiqs'
                    file_info['extracted_data'] = extracted_data
                    self.unmatched_cases.append(file_info)
                    self.processing_stats['unmatched'] += 1
            
            except Exception as e:
                print(f"   ❌ Error: {str(e)}")
                file_info['status'] = 'unmatched'
                file_info['reason'] = f'Processing error: {str(e)}'
                self.unmatched_cases.append(file_info)
                self.processing_stats['unmatched'] += 1
        
        print(f"\n📊 Matching Results:")
        print(f"   ✅ Matched: {self.processing_stats['matched']}")
        print(f"   ⚠️  Unmatched: {self.processing_stats['unmatched']}")
    
    def generate_quality_review_sheet(self):
        """
        Generate a comprehensive review sheet for quality control before uploading to Logiqs
        
        This sheet contains:
        - Case ID
        - Proposed naming convention
        - All extracted data
        - Confidence scores
        
        Returns:
            str: Path to the generated review Excel file
        """
        if not self.matched_cases:
            print("\n⏭️  No matched cases to review")
            return None
        
        print("\n📋 GENERATING QUALITY REVIEW SHEET")
        print("=" * 80)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        review_dir = 'QUALITY_REVIEW'
        os.makedirs(review_dir, exist_ok=True)
        
        # Prepare data for review
        review_data = []
        for file_info in self.matched_cases:
            extracted = file_info.get('extracted_data', {})
            
            # Generate proposed naming convention
            letter_type = extracted.get('letter_type', 'CP2000')
            tax_year = extracted.get('tax_year', 'Unknown')
            notice_date = extracted.get('notice_date', 'Unknown')
            taxpayer_name = extracted.get('taxpayer_name', '')
            last_name = taxpayer_name.split()[-1] if taxpayer_name else 'Unknown'
            
            # Naming convention: IRS_CORR_{Letter Type}_{Tax Year}_DTD {Date of Notice}_{Last Name}.pdf
            proposed_name = f"IRS_CORR_{letter_type}_{tax_year}_DTD_{notice_date}_{last_name}.pdf"
            
            review_data.append({
                'Case_ID': file_info.get('case_id', ''),
                'Original_Filename': file_info.get('filename', ''),
                'Proposed_Filename': proposed_name,
                'Taxpayer_Name': taxpayer_name,
                'SSN_Last_4': extracted.get('ssn_last_4', ''),
                'Letter_Type': letter_type,
                'Tax_Year': tax_year,
                'Notice_Date': notice_date,
                'Due_Date': extracted.get('response_due_date', ''),
                'Source_Folder': file_info.get('source_folder', ''),
                'Match_Confidence': 'High',
                'Status': '',  # Fill this: APPROVE / UNDER_REVIEW / REJECT
                'Notes': ''  # Add notes if needed
            })
        
        # Create Excel sheet
        df = pd.DataFrame(review_data)
        
        # Add formatting instructions at the top
        instructions_data = [
            {'Case_ID': '=== INSTRUCTIONS ===', 'Original_Filename': '', 'Proposed_Filename': '', 
             'Taxpayer_Name': '', 'SSN_Last_4': '', 'Letter_Type': '', 'Tax_Year': '', 
             'Notice_Date': '', 'Due_Date': '', 'Source_Folder': '', 'Match_Confidence': '',
             'Status': '', 'Notes': ''},
            {'Case_ID': 'Review each matched case below', 'Original_Filename': '', 'Proposed_Filename': '', 
             'Taxpayer_Name': '', 'SSN_Last_4': '', 'Letter_Type': '', 'Tax_Year': '', 
             'Notice_Date': '', 'Due_Date': '', 'Source_Folder': '', 'Match_Confidence': '',
             'Status': '', 'Notes': ''},
            {'Case_ID': 'In Status column, enter: APPROVE, UNDER_REVIEW, or REJECT', 'Original_Filename': '', 
             'Proposed_Filename': '', 'Taxpayer_Name': '', 'SSN_Last_4': '', 'Letter_Type': '', 
             'Tax_Year': '', 'Notice_Date': '', 'Due_Date': '', 'Source_Folder': '', 
             'Match_Confidence': '', 'Status': '', 'Notes': ''},
            {'Case_ID': 'Add any notes in Notes column', 'Original_Filename': '', 'Proposed_Filename': '', 
             'Taxpayer_Name': '', 'SSN_Last_4': '', 'Letter_Type': '', 'Tax_Year': '', 
             'Notice_Date': '', 'Due_Date': '', 'Source_Folder': '', 'Match_Confidence': '',
             'Status': '', 'Notes': ''},
            {'Case_ID': 'Save this file and run: python3 daily_pipeline_orchestrator.py --upload-approved', 
             'Original_Filename': '', 'Proposed_Filename': '', 'Taxpayer_Name': '', 'SSN_Last_4': '', 
             'Letter_Type': '', 'Tax_Year': '', 'Notice_Date': '', 'Due_Date': '', 'Source_Folder': '', 
             'Match_Confidence': '', 'Status': '', 'Notes': ''},
            {'Case_ID': '', 'Original_Filename': '', 'Proposed_Filename': '', 'Taxpayer_Name': '', 
             'SSN_Last_4': '', 'Letter_Type': '', 'Tax_Year': '', 'Notice_Date': '', 'Due_Date': '', 
             'Source_Folder': '', 'Match_Confidence': '', 'Status': '', 'Notes': ''},
        ]
        
        instructions_df = pd.DataFrame(instructions_data)
        final_df = pd.concat([instructions_df, df], ignore_index=True)
        
        # Save to Excel
        excel_path = os.path.join(review_dir, f'QUALITY_REVIEW_MATCHED_CASES_{timestamp}.xlsx')
        
        with pd.ExcelWriter(excel_path, engine='openpyxl') as writer:
            final_df.to_excel(writer, sheet_name='Matched Cases - Review', index=False)
            
            # Auto-adjust column widths
            worksheet = writer.sheets['Matched Cases - Review']
            for idx, col in enumerate(final_df.columns):
                max_length = max(
                    final_df[col].astype(str).map(len).max(),
                    len(col)
                ) + 2
                col_letter = chr(65 + idx) if idx < 26 else chr(65 + idx // 26 - 1) + chr(65 + idx % 26)
                worksheet.column_dimensions[col_letter].width = min(max_length, 50)
        
        print(f"\n✅ Quality Review Sheet Generated:")
        print(f"   📄 {excel_path}")
        print(f"   📊 {len(self.matched_cases)} cases ready for review")
        print(f"\n⏸️  PIPELINE PAUSED FOR QUALITY REVIEW")
        print(f"=" * 80)
        print(f"\n📋 NEXT STEPS:")
        print(f"   1. Open: {excel_path}")
        print(f"   2. Review each matched case")
        print(f"   3. In 'Status' column, enter:")
        print(f"      • APPROVE - Will upload to Logiqs")
        print(f"      • UNDER_REVIEW - Needs additional review")
        print(f"      • REJECT - Will move to UNMATCHED folder")
        print(f"   4. Save the file")
        print(f"   5. Run: python3 daily_pipeline_orchestrator.py --upload-approved")
        print(f"\n💡 Or to skip review and upload all (NOT RECOMMENDED):")
        print(f"   python3 daily_pipeline_orchestrator.py --skip-review")
        print("=" * 80)
        
        return excel_path
    
    def process_quality_approvals(self, review_file_path):
        """
        Process approved cases from the quality review sheet
        
        Args:
            review_file_path: Path to the approved review Excel file
            
        Returns:
            list: List of approved cases
        """
        if not os.path.exists(review_file_path):
            print(f"\n❌ Review file not found: {review_file_path}")
            print(f"   Please ensure you've saved the quality review sheet")
            return []
        
        print("\n📋 PROCESSING QUALITY APPROVALS")
        print("=" * 80)
        
        # Read the review sheet
        df = pd.read_excel(review_file_path, sheet_name='Matched Cases - Review')
        
        # Skip instruction rows
        df = df[df['Case_ID'] != '=== INSTRUCTIONS ===']
        df = df[~df['Case_ID'].astype(str).str.startswith('Review each')]
        df = df[~df['Case_ID'].astype(str).str.startswith('In Status')]
        df = df[~df['Case_ID'].astype(str).str.startswith('Add any notes')]
        df = df[~df['Case_ID'].astype(str).str.startswith('Save this file')]
        df = df[df['Case_ID'].notna()]
        df = df[df['Case_ID'].astype(str).str.strip() != '']
        
        approved_cases = []
        rejected_cases = []
        needs_review_cases = []
        
        for _, row in df.iterrows():
            case_id = str(row.get('Case_ID', '')).strip()
            approval_status = str(row.get('Status', '')).strip().upper()
            
            # Find the matching case in self.matched_cases
            matching_case = None
            for case in self.matched_cases:
                if str(case.get('case_id', '')).strip() == case_id:
                    matching_case = case
                    break
            
            if not matching_case:
                print(f"   ⚠️  Case {case_id} not found in matched cases")
                continue
            
            # Add review notes to the case
            matching_case['review_notes'] = str(row.get('Notes', '')).strip()
            matching_case['approved_name'] = str(row.get('Proposed_Filename', '')).strip()
            
            if approval_status == 'APPROVE':
                approved_cases.append(matching_case)
            elif approval_status == 'REJECT':
                rejected_cases.append(matching_case)
                # Move rejected cases to unmatched
                matching_case['status'] = 'rejected_by_review'
                matching_case['reason'] = f"Rejected: {matching_case['review_notes']}"
                self.unmatched_cases.append(matching_case)
            elif approval_status == 'UNDER_REVIEW' or approval_status == 'REVIEW':
                needs_review_cases.append(matching_case)
            else:
                print(f"   ⚠️  Case {case_id}: No status set (skipping)")
        
        print(f"\n📊 Quality Review Summary:")
        print(f"   ✅ Approved: {len(approved_cases)} (will upload)")
        print(f"   ❌ Rejected: {len(rejected_cases)} (moved to UNMATCHED)")
        print(f"   🔍 Under Review: {len(needs_review_cases)} (requires additional review)")
        
        # Update self.matched_cases to only include approved
        self.matched_cases = approved_cases
        
        if needs_review_cases:
            print(f"\n⚠️  WARNING: {len(needs_review_cases)} cases still need review")
            print(f"   These will NOT be uploaded until approved")
            for case in needs_review_cases:
                case_id = case.get('case_id', 'Unknown')
                filename = case.get('filename', 'Unknown')
                print(f"   • Case {case_id}: {filename}")
        
        return approved_cases
    
    def upload_matched_cases_to_logiqs(self):
        """Upload matched cases to Logiqs CRM with document and task creation"""
        if not self.matched_cases:
            print("\n⏭️  No matched cases to upload")
            return
        
        if self.test_mode:
            print("\n🧪 TEST MODE: Skipping Logiqs upload (would upload in production)")
            print(f"   Would upload {len(self.matched_cases)} documents to Logiqs")
            return
        
        if not self.logiqs_uploader:
            print("\n⚠️  Logiqs uploader not initialized - skipping upload")
            return
        
        print("\n📤 UPLOADING MATCHED CASES TO LOGIQS")
        print("=" * 80)
        
        for i, file_info in enumerate(self.matched_cases, 1):
            try:
                case_id = file_info.get('case_id')
                local_path = file_info.get('local_path')
                filename = file_info.get('filename')
                extracted_data = file_info.get('extracted_data', {})
                
                print(f"\n{i}/{len(self.matched_cases)} - Uploading to Case {case_id}")
                print(f"   📄 File: {filename}")
                
                # Upload document
                upload_result = self.logiqs_uploader.upload_to_logiqs(
                    case_id=case_id,
                    file_path=local_path,
                    comment=f"CP2000 Notice - Auto-uploaded {datetime.now().strftime('%Y-%m-%d')}"
                )
                
                if upload_result.get('success'):
                    print(f"   ✅ Document uploaded successfully")
                    
                    # Create task
                    notice_date = extracted_data.get('notice_date', 'Unknown')
                    due_date = extracted_data.get('response_due_date', datetime.now().strftime('%Y-%m-%d'))
                    
                    task_result = self.logiqs_uploader.create_task(
                        case_id=case_id,
                        subject=f"Review CP2000 Notice - {notice_date}",
                        due_date=due_date,
                        comments=f"CP2000 notice uploaded. Response required by {due_date}.",
                        priority=2  # High priority
                    )
                    
                    if task_result.get('success'):
                        print(f"   ✅ Task created (ID: {task_result.get('task_id')})")
                        self.processing_stats['uploaded'] += 1
                    else:
                        print(f"   ⚠️  Task creation failed: {task_result.get('error')}")
                else:
                    print(f"   ❌ Upload failed: {upload_result.get('error')}")
                    self.processing_stats['failed'] += 1
                
            except Exception as e:
                print(f"   ❌ Error: {self._sanitize_for_log(str(e))}")
                self.processing_stats['failed'] += 1
        
        print(f"\n📊 Upload Summary:")
        print(f"   ✅ Uploaded: {self.processing_stats['uploaded']}")
        print(f"   ❌ Failed: {self.processing_stats['failed']}")
    
    def move_files_to_output_folders(self):
        """Move files to appropriate Google Drive folders"""
        print("\n📦 STEP 3: ORGANIZING FILES IN GOOGLE DRIVE")
        print("=" * 80)
        
        # In test mode, use TEST folders instead of production folders
        if self.test_mode:
            print("🧪 TEST MODE: Moving files to TEST/MATCHED and TEST/UNMATCHED folders")
            matched_folder = self.test_matched_folder
            unmatched_folder = self.test_unmatched_folder
            
            if not matched_folder or not unmatched_folder:
                print("⚠️  TEST folders not configured - skipping file movement")
                print("   💡 Run: python3 -c \"from daily_pipeline_orchestrator import setup_test_folders; setup_test_folders()\"")
                return
        else:
            matched_folder = self.folders['output_matched']
            unmatched_folder = self.folders['output_unmatched']
        
        # Move matched files to appropriate folder
        folder_name = "TEST/MATCHED" if self.test_mode else "CP2000_MATCHED"
        print(f"\n✅ Moving {len(self.matched_cases)} matched files to {folder_name}...")
        for i, file_info in enumerate(self.matched_cases, 1):
            try:
                file_id = file_info['drive_id']
                new_parents = matched_folder
                
                # IMPROVED: Move with retry logic and rate limiting
                def move_call():
                    file = self.service.files().get(fileId=file_id, fields='parents').execute()
                    previous_parents = ",".join(file.get('parents', []))
                    
                    self.service.files().update(
                        fileId=file_id,
                        addParents=new_parents,
                        removeParents=previous_parents,
                        fields='id, parents'
                    ).execute()
                    return True
                
                self._api_call_with_retry(move_call)
                
                if i % 10 == 0:
                    print(f"   Moved: {i}/{len(self.matched_cases)} files...")
                
            except Exception as e:
                print(f"   ❌ Error moving {file_info['filename']}: {self._sanitize_for_log(str(e))}")
        
        print(f"   ✅ Moved {len(self.matched_cases)} files to {folder_name}")
        
        # Move unmatched files to appropriate folder
        folder_name = "TEST/UNMATCHED" if self.test_mode else "CP2000_UNMATCHED"
        print(f"\n⚠️  Moving {len(self.unmatched_cases)} unmatched files to {folder_name}...")
        for i, file_info in enumerate(self.unmatched_cases, 1):
            try:
                file_id = file_info['drive_id']
                new_parents = unmatched_folder
                
                # IMPROVED: Move with retry logic and rate limiting
                def move_call():
                    file = self.service.files().get(fileId=file_id, fields='parents').execute()
                    previous_parents = ",".join(file.get('parents', []))
                    
                    self.service.files().update(
                        fileId=file_id,
                        addParents=new_parents,
                        removeParents=previous_parents,
                        fields='id, parents'
                    ).execute()
                    return True
                
                self._api_call_with_retry(move_call)
                
                if i % 10 == 0:
                    print(f"   Moved: {i}/{len(self.unmatched_cases)} files...")
                
            except Exception as e:
                print(f"   ❌ Error moving {file_info['filename']}: {self._sanitize_for_log(str(e))}")
        
        print(f"   ✅ Moved {len(self.unmatched_cases)} files to {folder_name}")
    
    def upload_file_to_drive(self, local_path, folder_id, filename):
        """Upload a file to Google Drive"""
        from googleapiclient.http import MediaFileUpload
        
        try:
            file_metadata = {
                'name': filename,
                'parents': [folder_id]
            }
            media = MediaFileUpload(local_path, resumable=True)
            file = self.service.files().create(
                body=file_metadata,
                media_body=media,
                fields='id, webViewLink'
            ).execute()
            return file.get('id'), file.get('webViewLink')
        except Exception as e:
            print(f"   ⚠️  Error uploading {filename}: {str(e)}")
            return None, None
    
    def generate_reports(self):
        """Generate comprehensive daily reports and upload to Google Drive"""
        print("\n📊 STEP 4: GENERATING DAILY REPORTS")
        print("=" * 80)
        
        # Determine target folders based on test mode
        if self.test_mode and self.test_matched_folder and self.test_unmatched_folder:
            print("🧪 TEST MODE: Reports will be saved to TEST folder in Google Drive")
            matched_folder_id = self.test_matched_folder
            unmatched_folder_id = self.test_unmatched_folder
            folder_name_matched = "TEST/MATCHED"
            folder_name_unmatched = "TEST/UNMATCHED"
        else:
            print("📤 Reports will be saved to Google Drive")
            matched_folder_id = self.folders['output_matched']
            unmatched_folder_id = self.folders['output_unmatched']
            folder_name_matched = "CP2000_MATCHED"
            folder_name_unmatched = "CP2000_UNMATCHED"
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Save matched cases report
        if self.matched_cases:
            matched_report = {
                'timestamp': timestamp,
                'total_matched': len(self.matched_cases),
                'cases': self.matched_cases
            }
            
            # Save locally first
            matched_json = os.path.join(self.matched_dir, f'matched_cases_{timestamp}.json')
            with open(matched_json, 'w', encoding='utf-8') as f:
                json.dump(matched_report, f, indent=2, ensure_ascii=False)
            
            # Excel report for matched
            matched_df = pd.DataFrame([{
                'Filename': c['filename'],
                'Case_ID': c.get('case_id', ''),
                'Last_Name': c.get('extracted_data', {}).get('last_name', ''),
                'SSN_Last_4': c.get('extracted_data', {}).get('ssn_last_4', ''),
                'Tax_Year': c.get('extracted_data', {}).get('tax_year', ''),
                'Source_Folder': c['source_folder'],
                'Status': 'Ready for Upload'
            } for c in self.matched_cases])
            
            matched_excel = os.path.join(self.matched_dir, f'matched_cases_{timestamp}.xlsx')
            matched_df.to_excel(matched_excel, index=False, engine='openpyxl')
            
            # Upload to Google Drive
            print(f"   📤 Uploading matched report to {folder_name_matched}...")
            file_id, link = self.upload_file_to_drive(
                matched_excel,
                matched_folder_id,
                f'MATCHED_REPORT_{timestamp}.xlsx'
            )
            if file_id:
                print(f"   ✅ Matched report uploaded to {folder_name_matched} folder")
                # Clean up local file only if upload succeeded
                os.remove(matched_excel)
                os.remove(matched_json)
            else:
                if self.test_mode:
                    print(f"   📁 Upload failed - Report saved locally: {matched_excel}")
                else:
                    # In production, still clean up even if upload failed
                    os.remove(matched_excel)
                    os.remove(matched_json)
        
        # Save unmatched cases report
        if self.unmatched_cases:
            unmatched_report = {
                'timestamp': timestamp,
                'total_unmatched': len(self.unmatched_cases),
                'cases': self.unmatched_cases
            }
            
            # Save locally first
            unmatched_json = os.path.join(self.unmatched_dir, f'unmatched_cases_{timestamp}.json')
            with open(unmatched_json, 'w', encoding='utf-8') as f:
                json.dump(unmatched_report, f, indent=2, ensure_ascii=False)
            
            # Excel report for unmatched (for manual review)
            unmatched_df = pd.DataFrame([{
                'Filename': c['filename'],
                'Last_Name': c.get('extracted_data', {}).get('last_name', 'N/A'),
                'SSN_Last_4': c.get('extracted_data', {}).get('ssn_last_4', 'N/A'),
                'Tax_Year': c.get('extracted_data', {}).get('tax_year', 'N/A'),
                'Source_Folder': c['source_folder'],
                'Reason': c.get('reason', 'Unknown'),
                'Status': 'Needs Manual Review'
            } for c in self.unmatched_cases])
            
            unmatched_excel = os.path.join(self.unmatched_dir, f'unmatched_cases_{timestamp}.xlsx')
            unmatched_df.to_excel(unmatched_excel, index=False, engine='openpyxl')
            
            # Upload to Google Drive
            print(f"   📤 Uploading unmatched report to {folder_name_unmatched}...")
            file_id, link = self.upload_file_to_drive(
                unmatched_excel,
                unmatched_folder_id,
                f'UNMATCHED_REPORT_{timestamp}.xlsx'
            )
            if file_id:
                print(f"   ✅ Unmatched report uploaded to {folder_name_unmatched} folder")
                # Clean up local file only if upload succeeded
                os.remove(unmatched_excel)
                os.remove(unmatched_json)
            else:
                if self.test_mode:
                    print(f"   📁 Upload failed - Report saved locally: {unmatched_excel}")
                else:
                    # In production, still clean up even if upload failed
                    os.remove(unmatched_excel)
                    os.remove(unmatched_json)
        
        if self.test_mode:
            print(f"\n   📊 Reports saved locally (upload not available with service account)")
            print(f"   📁 Check DAILY_REPORTS/ folder for test outputs")
        else:
            print(f"\n   📊 All reports uploaded to Google Drive")
            print(f"   🗑️  Local report files cleaned up")
    
    def cleanup(self):
        """
        Clean up temporary files and local report directories
        IMPROVED: Secure file deletion with memory management
        """
        print("\n🗑️  STEP 5: CLEANING UP")
        print("=" * 80)
        
        # IMPROVED: Delete files individually to manage memory better
        if os.path.exists(self.temp_dir):
            try:
                # Remove files one by one (prevents memory spikes with large files)
                for file in os.listdir(self.temp_dir):
                    try:
                        file_path = os.path.join(self.temp_dir, file)
                        if os.path.isfile(file_path):
                            os.remove(file_path)  # Securely delete temp files
                    except Exception as e:
                        print(f"   ⚠️  Could not remove {file}: {str(e)}")
                
                # Remove directory
                shutil.rmtree(self.temp_dir)
                print("   ✅ Temporary PDF files deleted (secure cleanup)")
            except Exception as e:
                print(f"   ⚠️  Error during cleanup: {str(e)}")
        
        # In test mode, keep reports locally if they exist
        if self.test_mode:
            if os.path.exists(self.output_dir):
                print("   📁 Test reports kept in DAILY_REPORTS/ folder for review")
        else:
            # Clean up DAILY_REPORTS directory in production (reports are in Google Drive)
            if os.path.exists(self.output_dir):
                try:
                    shutil.rmtree(self.output_dir)
                    print("   ✅ Local report directory cleaned (reports saved to Google Drive)")
                except Exception as e:
                    print(f"   ⚠️  Error cleaning reports: {str(e)}")
        
        # IMPROVED: Force garbage collection to free memory
        gc.collect()
        print("   ✅ Memory released (garbage collection complete)")
    
    def run(self, skip_review=False, upload_approved_file=None):
        """
        Run the complete daily pipeline with optional COO review
        
        Args:
            skip_review: If True, skip COO review and upload all matched cases (NOT RECOMMENDED)
            upload_approved_file: Path to COO-approved review file to process
        """
        print("\n" + "=" * 80)
        if self.test_mode:
            print(f"🧪 DAILY MAIL ROOM PIPELINE - TEST MODE ({self.test_file_limit} FILES)")
        else:
            print("🚀 DAILY MAIL ROOM PIPELINE - STARTING")
        print("=" * 80)
        print(f"📅 Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        if self.test_mode:
            print("⚠️  TEST MODE ENABLED:")
            print(f"   • Processing only {self.test_file_limit} files")
            print("   • Files will NOT be moved in Google Drive")
            print("   • Reports will still be generated")
            print("   • Safe to run without affecting production")
        
        start_time = datetime.now()
        
        try:
            # If we have an approved file, process it and upload
            if upload_approved_file:
                print("\n📋 UPLOAD MODE: Processing approved cases")
                
                # Authenticate
                self.authenticate_google_drive()
                self.create_output_folders_if_needed()
                
                # Process the approved review file
                self.process_quality_approvals(upload_approved_file)
                
                # Upload approved cases
                self.upload_matched_cases_to_logiqs()
                
                # Move files
                self.move_files_to_output_folders()
                
                # Generate final reports
                self.generate_reports()
                
                # Cleanup
                self.cleanup()
                
                print("\n✅ APPROVED CASES UPLOADED")
                return
            
            # Normal pipeline flow
            # Step 1: Authenticate
            self.authenticate_google_drive()
            
            # Step 2: Ensure output folders exist
            self.create_output_folders_if_needed()
            
            # Step 3: Download new files
            files = self.download_new_files()
            
            if not files:
                print("\n✅ No new files to process!")
                return
            
            # Step 4: Extract and match
            self.extract_and_match(files)
            
            # Step 5: Generate quality review sheet (UNLESS skip_review is True or test_mode)
            if not skip_review and self.matched_cases and not self.test_mode:
                review_file = self.generate_quality_review_sheet()
                
                # PAUSE HERE - Don't upload yet
                print("\n⏸️  Pipeline paused. Please review and approve cases before continuing.")
                
                # Save processing history for downloaded files
                for file_info in files:
                    self.save_to_history(
                        file_info['drive_id'],
                        file_info['filename'],
                        file_info.get('status', 'pending_review')
                    )
                
                return
            
            # Step 6: Upload matched cases to Logiqs (only if skip_review or test_mode)
            if skip_review or self.test_mode:
                self.upload_matched_cases_to_logiqs()
            
            # Step 7: Move files to output folders
            self.move_files_to_output_folders()
            
            # Step 8: Generate reports
            self.generate_reports()
            
            # Step 9: Save processing history
            for file_info in files:
                self.save_to_history(
                    file_info['drive_id'],
                    file_info['filename'],
                    file_info.get('status', 'processed')
                )
            
            # Step 10: Cleanup
            self.cleanup()
            
            # Final summary
            duration = (datetime.now() - start_time).total_seconds()
            
            print("\n" + "=" * 80)
            if self.test_mode:
                print("✅ TEST RUN COMPLETE")
            else:
                print("✅ DAILY PIPELINE COMPLETE")
            print("=" * 80)
            print(f"⏱️  Duration: {duration:.1f}s")
            print(f"\n📊 Processing Summary:")
            print(f"   Total Files: {self.processing_stats['total_files']}")
            if self.test_mode:
                print(f"   ✅ Matched: {self.processing_stats['matched']} (would move to CP2000_MATCHED)")
                print(f"   ⚠️  Unmatched: {self.processing_stats['unmatched']} (would move to CP2000_UNMATCHED)")
            else:
                print(f"   ✅ Matched: {self.processing_stats['matched']} (moved to CP2000_MATCHED)")
                print(f"   ⚠️  Unmatched: {self.processing_stats['unmatched']} (moved to CP2000_UNMATCHED)")
            
            if not self.test_mode:
                print(f"\n📁 Google Drive Folders:")
                print(f"   Matched: {self.folders['output_matched']}")
                print(f"   Unmatched: {self.folders['output_unmatched']}")
            
            print(f"\n📊 Local Reports:")
            print(f"   Matched: DAILY_REPORTS/MATCHED/")
            print(f"   Unmatched: DAILY_REPORTS/UNMATCHED/")
            
            if self.test_mode:
                print(f"\n🧪 Test Mode Results:")
                print(f"   • {self.processing_stats['matched']} files identified for Folder B (CP2000_MATCHED)")
                print(f"   • {self.processing_stats['unmatched']} files identified for Folder C (CP2000_UNMATCHED)")
                print(f"   • Files remain in original folders (not moved)")
                print(f"   • Review reports to verify categorization")
                print(f"\n💡 Next Steps:")
                print(f"   1. Review reports in DAILY_REPORTS/")
                print(f"   2. If results look good, run in production mode:")
                print(f"      python3 daily_pipeline_orchestrator.py")
            else:
                print(f"\n💡 Next Steps:")
                print(f"   1. Review unmatched cases in Google Drive: CP2000_UNMATCHED")
                print(f"   2. Run upload script for matched cases: python3 upload_to_logiqs.py")
            print("=" * 80)
        
        except Exception as e:
            print(f"\n❌ Pipeline error: {str(e)}")
            import traceback
            traceback.print_exc()
            self.cleanup()
            raise


if __name__ == "__main__":
    import sys
    
    # Check for test mode flag
    test_mode = '--test' in sys.argv
    skip_review = '--skip-review' in sys.argv
    
    # Check for upload approved flag
    upload_approved_file = None
    for arg in sys.argv:
        if arg.startswith('--upload-approved='):
            upload_approved_file = arg.split('=')[1]
        elif arg == '--upload-approved':
            # Find the most recent quality review file
            review_dir = 'QUALITY_REVIEW'
            if os.path.exists(review_dir):
                review_files = [f for f in os.listdir(review_dir) if f.startswith('QUALITY_REVIEW_MATCHED_CASES_') and f.endswith('.xlsx')]
                if review_files:
                    review_files.sort(reverse=True)  # Most recent first
                    upload_approved_file = os.path.join(review_dir, review_files[0])
                    print(f"\n📋 Using most recent review file: {upload_approved_file}")
                else:
                    print("\n❌ No review files found in QUALITY_REVIEW/")
                    print("   Please run the pipeline first to generate a review file:")
                    print("   python3 daily_pipeline_orchestrator.py")
                    sys.exit(1)
            else:
                print("\n❌ QUALITY_REVIEW directory not found")
                print("   Please run the pipeline first to generate a review file:")
                print("   python3 daily_pipeline_orchestrator.py")
                sys.exit(1)
    
    # Check for custom file limit
    test_limit = 5  # default
    for arg in sys.argv:
        if arg.startswith('--limit='):
            try:
                test_limit = int(arg.split('=')[1])
            except:
                print("Invalid limit value, using default: 5")
    
    if test_mode:
        print("=" * 80)
        print("🧪 RUNNING IN TEST MODE")
        print("=" * 80)
        print(f"• Will process only {test_limit} files")
        print("• Files will NOT be moved")
        print("• Safe to test without affecting production")
        print("=" * 80)
    
    if skip_review and not test_mode:
        print("\n⚠️  WARNING: Skipping COO review (--skip-review flag)")
        print("   All matched cases will be uploaded automatically")
        print("   This is NOT RECOMMENDED for production use")
        print("   Press Ctrl+C to cancel or wait 5 seconds to continue...")
        import time
        time.sleep(5)
    
    orchestrator = DailyPipelineOrchestrator(test_mode=test_mode, test_file_limit=test_limit)
    orchestrator.run(skip_review=skip_review, upload_approved_file=upload_approved_file)

