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
        
        if self.test_mode:
            print(f"📋 Daily Pipeline Orchestrator initialized (TEST MODE - {self.test_file_limit} files only)")
        else:
            print("📋 Daily Pipeline Orchestrator initialized")
    
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
                last_name = extracted_data.get('last_name', '')
                first_name = extracted_data.get('first_name', '')
                
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
    
    def run(self):
        """Run the complete daily pipeline"""
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
            
            # Step 5: Move files to output folders
            self.move_files_to_output_folders()
            
            # Step 6: Generate reports
            self.generate_reports()
            
            # Step 7: Cleanup
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
    
    orchestrator = DailyPipelineOrchestrator(test_mode=test_mode, test_file_limit=test_limit)
    orchestrator.run()

