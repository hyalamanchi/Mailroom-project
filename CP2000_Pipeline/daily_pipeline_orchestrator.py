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
from datetime import datetime
from typing import Dict, List, Optional
import pandas as pd
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload, MediaFileUpload
from google.oauth2 import service_account

# Import our existing modules
from hundred_percent_accuracy_extractor import HundredPercentAccuracyExtractor
from logics_case_search import LogicsCaseSearcher
from generate_upload_list import UploadListGenerator


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
    
    def download_new_files(self) -> List[str]:
        """Download new files from input folders"""
        print("\n📥 STEP 1: DOWNLOADING NEW FILES FROM INPUT FOLDERS")
        print("=" * 80)
        
        if self.test_mode:
            print(f"⚠️  TEST MODE: Will download only {self.test_file_limit} files for testing")
        
        all_files = []
        
        # Download from main input folder
        input_folders = {
            'main_folder': self.folders['input_main']
        }
        
        for folder_name, folder_id in input_folders.items():
            # Skip if we've reached test limit
            if self.test_mode and len(all_files) >= self.test_file_limit:
                break
            
            print(f"\n📁 Processing: {folder_name}")
            
            # List files in folder
            query = f"'{folder_id}' in parents and mimeType='application/pdf' and trashed=false"
            results = self.service.files().list(q=query, fields="files(id, name)").execute()
            files = results.get('files', [])
            
            print(f"   Found: {len(files)} PDFs")
            
            # Limit files in test mode
            if self.test_mode:
                remaining = self.test_file_limit - len(all_files)
                files = files[:remaining]
                print(f"   Test mode: Processing only {len(files)} files from this folder")
            
            # Download each file
            for i, file in enumerate(files, 1):
                try:
                    local_path = os.path.join(self.temp_dir, file['name'])
                    
                    request = self.service.files().get_media(fileId=file['id'])
                    with open(local_path, 'wb') as f:
                        downloader = MediaIoBaseDownload(f, request)
                        done = False
                        while not done:
                            status, done = downloader.next_chunk()
                    
                    all_files.append({
                        'local_path': local_path,
                        'filename': file['name'],
                        'drive_id': file['id'],
                        'source_folder': folder_name
                    })
                    
                    if i % 10 == 0:
                        print(f"   Downloaded: {i}/{len(files)} files...")
                
                except Exception as e:
                    print(f"   ❌ Error downloading {file['name']}: {str(e)}")
        
        print(f"\n✅ Total files downloaded: {len(all_files)}")
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
        
        if self.test_mode:
            print("⚠️  TEST MODE: Files will NOT be moved (dry run only)")
            print(f"   Would move {len(self.matched_cases)} files to CP2000_MATCHED")
            print(f"   Would move {len(self.unmatched_cases)} files to CP2000_UNMATCHED")
            return
        
        # Move matched files to Folder B
        print(f"\n✅ Moving {len(self.matched_cases)} matched files to CP2000_MATCHED...")
        for i, file_info in enumerate(self.matched_cases, 1):
            try:
                # Move file in Google Drive
                file_id = file_info['drive_id']
                new_parents = self.folders['output_matched']
                
                # Remove from old parent and add to new parent
                file = self.service.files().get(fileId=file_id, fields='parents').execute()
                previous_parents = ",".join(file.get('parents', []))
                
                self.service.files().update(
                    fileId=file_id,
                    addParents=new_parents,
                    removeParents=previous_parents,
                    fields='id, parents'
                ).execute()
                
                if i % 10 == 0:
                    print(f"   Moved: {i}/{len(self.matched_cases)} files...")
                
            except Exception as e:
                print(f"   ❌ Error moving {file_info['filename']}: {str(e)}")
        
        print(f"   ✅ Moved {len(self.matched_cases)} files to CP2000_MATCHED")
        
        # Move unmatched files to Folder C
        print(f"\n⚠️  Moving {len(self.unmatched_cases)} unmatched files to CP2000_UNMATCHED...")
        for i, file_info in enumerate(self.unmatched_cases, 1):
            try:
                # Move file in Google Drive
                file_id = file_info['drive_id']
                new_parents = self.folders['output_unmatched']
                
                # Remove from old parent and add to new parent
                file = self.service.files().get(fileId=file_id, fields='parents').execute()
                previous_parents = ",".join(file.get('parents', []))
                
                self.service.files().update(
                    fileId=file_id,
                    addParents=new_parents,
                    removeParents=previous_parents,
                    fields='id, parents'
                ).execute()
                
                if i % 10 == 0:
                    print(f"   Moved: {i}/{len(self.unmatched_cases)} files...")
                
            except Exception as e:
                print(f"   ❌ Error moving {file_info['filename']}: {str(e)}")
        
        print(f"   ✅ Moved {len(self.unmatched_cases)} files to CP2000_UNMATCHED")
    
    def generate_reports(self):
        """Generate comprehensive daily reports"""
        print("\n📊 STEP 4: GENERATING DAILY REPORTS")
        print("=" * 80)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Save matched cases report
        if self.matched_cases:
            matched_report = {
                'timestamp': timestamp,
                'total_matched': len(self.matched_cases),
                'cases': self.matched_cases
            }
            
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
            
            print(f"   ✅ Matched cases report: {matched_excel}")
        
        # Save unmatched cases report
        if self.unmatched_cases:
            unmatched_report = {
                'timestamp': timestamp,
                'total_unmatched': len(self.unmatched_cases),
                'cases': self.unmatched_cases
            }
            
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
            
            print(f"   ✅ Unmatched cases report: {unmatched_excel}")
        
        # Summary report
        summary = {
            'date': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            'statistics': self.processing_stats,
            'matched_folder_id': self.folders['output_matched'],
            'unmatched_folder_id': self.folders['output_unmatched']
        }
        
        summary_file = os.path.join(self.output_dir, f'daily_summary_{timestamp}.json')
        with open(summary_file, 'w', encoding='utf-8') as f:
            json.dump(summary, f, indent=2)
        
        print(f"   ✅ Daily summary: {summary_file}")
    
    def cleanup(self):
        """Clean up temporary files"""
        print("\n🗑️  STEP 5: CLEANING UP")
        print("=" * 80)
        
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
            print("   ✅ Temporary files deleted")
    
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

