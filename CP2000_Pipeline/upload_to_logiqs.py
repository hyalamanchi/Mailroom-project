"""
Logiqs Document Upload Automation

Automates bulk document upload to Logiqs CRM with task creation.
Downloads matched CP2000 files from Google Drive and uploads them to 
corresponding cases in Logiqs, creating review tasks automatically.

API Endpoints:
- Document Upload: https://tps.logiqs.com/publicapi/2020-02-22/documents/casedocument
- Task Creation: https://tps.logiqs.com/publicapi/V3/Task/Task

Author: Hemalatha Yalamanchi
Created: October 2025
Version: 1.0
"""

import os
import json
import requests
import time
from datetime import datetime
from typing import List, Dict, Optional
from dotenv import load_dotenv
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
import pandas as pd

# Load environment variables
load_dotenv()

class LogiqsDocumentUploader:
    """Automated document uploader for Logiqs CRM"""
    
    def __init__(self):
        # Logiqs API configuration
        self.api_key = os.getenv('LOGIQS_API_KEY')
        self.secret_token = os.getenv('LOGIQS_SECRET_TOKEN')
        
        # Validate required credentials
        if not self.api_key:
            raise ValueError(
                "❌ LOGIQS_API_KEY not found!\n"
                "💡 Please set it in your .env file:\n"
                "   LOGIQS_API_KEY=your_api_key_here"
            )
        if not self.secret_token:
            raise ValueError(
                "❌ LOGIQS_SECRET_TOKEN not found!\n"
                "💡 Please set it in your .env file:\n"
                "   LOGIQS_SECRET_TOKEN=your_secret_token_here"
            )
        
        # API endpoints
        self.document_url = "https://tps.logiqs.com/publicapi/2020-02-22/documents/casedocument"
        self.task_url = "https://tps.logiqs.com/publicapi/V3/Task/Task"
        
        # Google Drive configuration
        self.SCOPES = ['https://www.googleapis.com/auth/drive.readonly']
        self.drive_service = None
        
        # Folder configuration
        self.folders = {
            'main_folder': '18e8lj66Mdr7PFGhJ7ySYtsnkNgiuczmx'
        }
        
        # Working directories
        self.temp_dir = 'TEMP_UPLOAD'
        self.results_dir = 'UPLOAD_RESULTS'
        os.makedirs(self.temp_dir, exist_ok=True)
        os.makedirs(self.results_dir, exist_ok=True)
        
        # Upload tracking
        self.upload_list = []
        self.successful_uploads = []
        self.failed_uploads = []
        
        # Rate limiting
        self.delay_between_uploads = 1  # 1 second between uploads
        
    def authenticate_google_drive(self):
        """Authenticate with Google Drive using service account"""
        print("🔐 Authenticating with Google Drive...")
        
        try:
            creds = service_account.Credentials.from_service_account_file(
                'service-account-key.json',
                scopes=self.SCOPES
            )
            
            self.drive_service = build('drive', 'v3', credentials=creds)
            print("   ✅ Google Drive authenticated (Service Account)\n")
            
        except FileNotFoundError:
            print("   ❌ Error: service-account-key.json not found")
            print("   💡 Place your service account JSON file in the project root")
            raise
        except Exception as e:
            print(f"   ❌ Authentication error: {str(e)}")
            raise
    
    def load_upload_list(self):
        """Load the upload list from JSON"""
        print("📂 Loading upload list...")
        
        # Find the latest upload list JSON
        upload_files = [f for f in os.listdir('UPLOAD_READY') 
                       if f.startswith('upload_list_') and f.endswith('.json')]
        
        if not upload_files:
            print("   ❌ No upload list found! Run generate_upload_list.py first")
            return False
        
        latest_file = sorted(upload_files)[-1]
        file_path = os.path.join('UPLOAD_READY', latest_file)
        
        with open(file_path, 'r') as f:
            data = json.load(f)
        
        self.upload_list = data.get('upload_list', data)
        print(f"   ✅ Loaded {len(self.upload_list)} files from {latest_file}\n")
        return True
    
    def find_file_in_drive(self, filename: str) -> Optional[tuple]:
        """Find a file in Google Drive across all folders"""
        for folder_name, folder_id in self.folders.items():
            try:
                query = f"name='{filename}' and '{folder_id}' in parents and trashed=false"
                results = self.drive_service.files().list(
                    q=query,
                    fields="files(id, name)",
                    pageSize=1
                ).execute()
                
                files = results.get('files', [])
                if files:
                    return files[0], folder_name
            except Exception as e:
                continue
        
        return None, None
    
    def download_file(self, file_id: str, output_path: str) -> bool:
        """Download a file from Google Drive"""
        try:
            request = self.drive_service.files().get_media(fileId=file_id)
            
            with open(output_path, 'wb') as f:
                downloader = MediaIoBaseDownload(f, request)
                done = False
                while not done:
                    status, done = downloader.next_chunk()
            
            return True
        except Exception as e:
            print(f"      ❌ Download error: {str(e)}")
            return False
    
    def upload_to_logiqs(self, case_id: int, file_path: str, comment: str = "") -> Dict:
        """
        Upload a document to Logiqs CRM
        
        Args:
            case_id: Logiqs Case ID
            file_path: Path to the PDF file
            comment: Optional comment for the document
            
        Returns:
            Dict with upload status and details
        """
        try:
            # Use the verified working endpoint
            url = self.document_url
            
            # Query parameters only (no Authorization header needed)
            params = {
                'apikey': self.api_key,
                'CaseID': case_id,
                'Comment': comment or f"Uploaded via API - {datetime.now().strftime('%Y-%m-%d %H:%M')}"
            }
            
            # Prepare the file
            filename = os.path.basename(file_path)
            
            with open(file_path, 'rb') as f:
                files = {
                    'file': (filename, f, 'application/pdf')
                }
                
                # Make the request (no headers needed - query params only)
                response = requests.post(
                    url,
                    params=params,
                    files=files,
                    timeout=60
                )
            
            # Check response
            if response.status_code == 200 or response.status_code == 201:
                return {
                    'success': True,
                    'status_code': response.status_code,
                    'response': response.text,
                    'case_id': case_id,
                    'filename': filename
                }
            else:
                return {
                    'success': False,
                    'status_code': response.status_code,
                    'error': response.text,
                    'case_id': case_id,
                    'filename': filename
                }
        
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'case_id': case_id,
                'filename': filename
            }
    
    def create_task(self, case_id: int, subject: str, due_date: str, comments: str = "", priority: int = 2) -> Dict:
        """
        Create a task in Logiqs using Basic Authentication
        
        Args:
            case_id: Logiqs Case ID
            subject: Task subject/title
            due_date: Due date string (will be converted to UTC)
            comments: Task comments
            priority: 0=Normal, 1=Medium, 2=High, 3=Urgent
            
        Returns:
            Dict with task creation status
        """
        try:
            import base64
            from dateutil import parser as date_parser
            
            # Parse and convert due date to UTC ISO format
            try:
                due_dt = date_parser.parse(due_date)
                due_date_utc = due_dt.strftime('%Y-%m-%dT%H:%M:%SZ')
                reminder_date = due_dt.replace(hour=9, minute=0).strftime('%Y-%m-%dT%H:%M:%SZ')
            except:
                # Default to 30 days from now if parsing fails
                from datetime import timedelta
                due_dt = datetime.now() + timedelta(days=30)
                due_date_utc = due_dt.strftime('%Y-%m-%dT%H:%M:%SZ')
                reminder_date = due_dt.replace(hour=9, minute=0).strftime('%Y-%m-%dT%H:%M:%SZ')
            
            # Basic Authentication
            credentials = f"{self.api_key}:{self.secret_token}"
            b64_credentials = base64.b64encode(credentials.encode()).decode()
            
            headers = {
                'Authorization': f'Basic {b64_credentials}',
                'Content-Type': 'application/json'
            }
            
            # Task payload
            payload = {
                'CaseID': case_id,
                'Subject': subject,
                'Reminder': reminder_date,
                'TaskType': 1,  # 1 = Task
                'DueDate': due_date_utc,
                'UserID': [],  # Empty array - will be assigned to case owner
                'PriorityID': priority,
                'StatusID': 0,  # 0 = Incomplete
                'Comments': comments
            }
            
            response = requests.post(
                self.task_url,
                headers=headers,
                json=payload,
                timeout=30
            )
            
            if response.status_code == 200 or response.status_code == 201:
                response_data = response.json()
                task_id = response_data.get('Data', {}).get('TaskID') or response_data.get('data', {}).get('TaskID')
                return {
                    'success': True,
                    'status_code': response.status_code,
                    'response': response_data,
                    'task_id': task_id
                }
            else:
                return {
                    'success': False,
                    'status_code': response.status_code,
                    'error': response.text
                }
        
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def process_upload(self, entry: Dict, index: int, total: int) -> Dict:
        """Process a single file upload"""
        old_filename = entry['Old_Filename']
        new_filename = entry['New_Filename']
        case_id = entry['Case_ID']
        last_name = entry['Last_Name']
        
        print(f"\n{index}/{total} - {last_name} (Case: {case_id})")
        print(f"   File: {new_filename}")
        
        result = {
            'index': index,
            'case_id': case_id,
            'old_filename': old_filename,
            'new_filename': new_filename,
            'last_name': last_name,
            'tax_year': entry.get('Tax_Year', ''),
            'ssn_last_4': entry.get('SSN_Last_4', ''),
            'match_type': entry.get('Match_Type', ''),
            'success': False,
            'error': None,
            'timestamp': datetime.now().isoformat()
        }
        
        try:
            # Step 1: Find file in Google Drive
            print(f"   📁 Finding in Google Drive...")
            file_info, folder = self.find_file_in_drive(old_filename)
            
            if not file_info:
                print(f"   ❌ File not found in Google Drive")
                result['error'] = "File not found in Google Drive"
                return result
            
            print(f"   ✅ Found in {folder}")
            
            # Step 2: Download with new name
            local_path = os.path.join(self.temp_dir, new_filename)
            print(f"   ⬇️  Downloading...")
            
            if not self.download_file(file_info['id'], local_path):
                result['error'] = "Download failed"
                return result
            
            print(f"   ✅ Downloaded as {new_filename}")
            
            # Step 3: Upload to Logiqs
            print(f"   ⬆️  Uploading to Logiqs Case {case_id}...")
            
            comment = f"IRS {entry.get('Tax_Year', '')} - {last_name} - Uploaded via API"
            upload_result = self.upload_to_logiqs(case_id, local_path, comment)
            
            if upload_result['success']:
                print(f"   ✅ Upload successful!")
                result['success'] = True
                result['upload_response'] = upload_result.get('response', '')
                
                # Step 4: Create Task in Logiqs
                print(f"   📋 Creating task...")
                
                task_subject = f"Review IRS CP2000 Notice - {entry.get('Tax_Year', '')}"
                due_date = entry.get('Response_Due_Date', '')
                task_comments = f"IRS CP2000 document uploaded for {last_name}. Tax Year: {entry.get('Tax_Year', '')}. SSN Last 4: {entry.get('SSN_Last_4', '')}. Please review and respond before due date."
                
                task_result = self.create_task(
                    case_id=case_id,
                    subject=task_subject,
                    due_date=due_date,
                    comments=task_comments,
                    priority=2  # High priority
                )
                
                if task_result['success']:
                    print(f"   ✅ Task created (ID: {task_result.get('task_id')})")
                    result['task_created'] = True
                    result['task_id'] = task_result.get('task_id')
                else:
                    print(f"   ⚠️  Task creation failed: {task_result.get('error', 'Unknown')}")
                    result['task_created'] = False
                    result['task_error'] = task_result.get('error')
            else:
                print(f"   ❌ Upload failed: {upload_result.get('error', 'Unknown error')}")
                result['error'] = upload_result.get('error', 'Unknown error')
                result['status_code'] = upload_result.get('status_code', 0)
            
            # Step 5: Cleanup local file
            if os.path.exists(local_path):
                os.remove(local_path)
            
        except Exception as e:
            print(f"   ❌ Error: {str(e)}")
            result['error'] = str(e)
        
        return result
    
    def run_batch_upload(self):
        """Run batch upload for all files"""
        print("\n" + "=" * 80)
        print("🚀 LOGIQS BULK DOCUMENT UPLOAD")
        print("=" * 80)
        print(f"\nTotal files to upload: {len(self.upload_list)}")
        print(f"Rate limit: {self.delay_between_uploads}s between uploads")
        print("\nStarting upload process...\n")
        
        start_time = datetime.now()
        
        for idx, entry in enumerate(self.upload_list, 1):
            result = self.process_upload(entry, idx, len(self.upload_list))
            
            if result['success']:
                self.successful_uploads.append(result)
            else:
                self.failed_uploads.append(result)
            
            # Progress update every 10 files
            if idx % 10 == 0:
                success_rate = (len(self.successful_uploads) / idx) * 100
                elapsed = (datetime.now() - start_time).total_seconds()
                avg_time = elapsed / idx
                eta = avg_time * (len(self.upload_list) - idx)
                
                print(f"\n{'='*80}")
                print(f"📊 Progress: {idx}/{len(self.upload_list)} ({idx/len(self.upload_list)*100:.1f}%)")
                print(f"   Success: {len(self.successful_uploads)} | Failed: {len(self.failed_uploads)}")
                print(f"   Success Rate: {success_rate:.1f}%")
                print(f"   Avg Time: {avg_time:.1f}s/file | ETA: {int(eta/60)}m {int(eta%60)}s")
                print(f"{'='*80}\n")
            
            # Rate limiting
            if idx < len(self.upload_list):
                time.sleep(self.delay_between_uploads)
        
        duration = (datetime.now() - start_time).total_seconds()
        
        return duration
    
    def generate_report(self, duration: float):
        """Generate upload report"""
        print("\n" + "=" * 80)
        print("📊 UPLOAD REPORT")
        print("=" * 80)
        
        total = len(self.upload_list)
        success_count = len(self.successful_uploads)
        failed_count = len(self.failed_uploads)
        success_rate = (success_count / total * 100) if total > 0 else 0
        
        print(f"\nTotal Files: {total}")
        print(f"✅ Successful: {success_count} ({success_rate:.1f}%)")
        print(f"❌ Failed: {failed_count} ({(failed_count/total*100):.1f}%)")
        print(f"⏱️  Duration: {int(duration/60)}m {int(duration%60)}s")
        print(f"📈 Throughput: {total/duration:.2f} files/sec")
        
        # Save detailed reports
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # 1. JSON report
        json_file = os.path.join(self.results_dir, f'upload_report_{timestamp}.json')
        report_data = {
            'summary': {
                'total_files': total,
                'successful': success_count,
                'failed': failed_count,
                'success_rate': success_rate,
                'duration_seconds': duration,
                'timestamp': datetime.now().isoformat()
            },
            'successful_uploads': self.successful_uploads,
            'failed_uploads': self.failed_uploads
        }
        
        with open(json_file, 'w') as f:
            json.dump(report_data, f, indent=2)
        
        print(f"\n💾 JSON Report: {json_file}")
        
        # 2. Excel report
        excel_file = os.path.join(self.results_dir, f'upload_report_{timestamp}.xlsx')
        
        with pd.ExcelWriter(excel_file, engine='openpyxl') as writer:
            # Summary sheet
            summary_df = pd.DataFrame([{
                'Total Files': total,
                'Successful': success_count,
                'Failed': failed_count,
                'Success Rate (%)': f"{success_rate:.1f}",
                'Duration (min)': f"{duration/60:.1f}",
                'Timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }])
            summary_df.to_excel(writer, sheet_name='Summary', index=False)
            
            # Successful uploads sheet
            if self.successful_uploads:
                success_df = pd.DataFrame(self.successful_uploads)
                success_df.to_excel(writer, sheet_name='Successful', index=False)
            
            # Failed uploads sheet
            if self.failed_uploads:
                failed_df = pd.DataFrame(self.failed_uploads)
                failed_df.to_excel(writer, sheet_name='Failed', index=False)
        
        print(f"📊 Excel Report: {excel_file}")
        
        # 3. Failed uploads list for retry
        if self.failed_uploads:
            failed_file = os.path.join(self.results_dir, f'failed_uploads_{timestamp}.json')
            with open(failed_file, 'w') as f:
                json.dump(self.failed_uploads, f, indent=2)
            
            print(f"⚠️  Failed List: {failed_file}")
            print(f"\n⚠️  {failed_count} uploads failed. Check the report for details.")
            
            # Show first 5 failed uploads
            print("\nFirst 5 failed uploads:")
            for i, failed in enumerate(self.failed_uploads[:5], 1):
                print(f"   {i}. Case {failed['case_id']} - {failed['last_name']}: {failed.get('error', 'Unknown')}")
            
            if failed_count > 5:
                print(f"   ... and {failed_count - 5} more")
        
        print("\n" + "=" * 80)
        
    def cleanup(self):
        """Cleanup temporary files"""
        if os.path.exists(self.temp_dir):
            import shutil
            shutil.rmtree(self.temp_dir)
            print(f"🗑️  Cleaned up temporary files")
    
    def run(self):
        """Main execution"""
        print("\n" + "=" * 80)
        print("🚀 LOGIQS DOCUMENT UPLOAD AUTOMATION")
        print("=" * 80)
        print("\nAPI Endpoint: https://tps.logiqs.com/publicapi/V3/Documents/CaseDocument")
        print("Max file size: 6 MB (all files < 4MB ✅)")
        print("=" * 80)
        
        try:
            # Step 1: Authenticate
            self.authenticate_google_drive()
            
            # Step 2: Load upload list
            if not self.load_upload_list():
                return
            
            # Step 3: Confirm before starting
            print(f"⚠️  About to upload {len(self.upload_list)} files to Logiqs")
            print(f"   This will take approximately {len(self.upload_list) * 3 / 60:.0f}-{len(self.upload_list) * 5 / 60:.0f} minutes")
            
            response = input("\nProceed with upload? (yes/no): ")
            if response.lower() != 'yes':
                print("Upload cancelled.")
                return
            
            # Step 4: Run batch upload
            duration = self.run_batch_upload()
            
            # Step 5: Generate report
            self.generate_report(duration)
            
            # Step 6: Cleanup
            self.cleanup()
            
            print("\n✅ Upload automation complete!")
            
        except KeyboardInterrupt:
            print("\n\n⚠️  Upload interrupted by user")
            self.generate_report((datetime.now() - datetime.now()).total_seconds())
            self.cleanup()
        except Exception as e:
            print(f"\n❌ Error: {str(e)}")
            self.cleanup()
            raise

if __name__ == "__main__":
    uploader = LogiqsDocumentUploader()
    uploader.run()

