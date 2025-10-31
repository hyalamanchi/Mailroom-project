"""
Single File Upload Test

Tests document upload and task creation with one file before running bulk upload.
Verifies API connectivity, authentication, and proper integration with Logiqs CRM.

Author: Hemalatha Yalamanchi
Created: October 2025
Version: 1.0
"""

import os
import json
import requests
from datetime import datetime
from dotenv import load_dotenv
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload

# Load environment variables
load_dotenv()

class SingleFileUploadTest:
    """Test upload for a single file"""
    
    def __init__(self):
        # Logiqs API configuration
        self.api_key = os.getenv('LOGIQS_API_KEY', '4917fa0ce4694529a9b97ead1a60c932')
        self.secret_token = os.getenv('LOGIQS_SECRET_TOKEN', '1534a639-8422-4524-b2a4-6ea161d42014')
        
        # API endpoints
        self.document_url = "https://tps.logiqs.com/publicapi/2020-02-22/documents/casedocument"
        self.task_url = "https://tps.logiqs.com/publicapi/V3/Task/Task"
        
        # Google Drive configuration
        self.SCOPES = ['https://www.googleapis.com/auth/drive.readonly']
        self.drive_service = None
        
        # Folder configuration
        self.folders = {
            'cp2000_incoming': '1CGl9pdVWqGssSS3ausbw88MoBWvS65zl',
            'cp2000newbatch_incoming': '1qLKRE0HBtpqu1zf20fWjAkDsXKdPmkIK',
            'cp2000newbatch2_incoming': '10TVBMsMLBizE-vGmY2vKOolCwSlXK2s8'
        }
        
        # Working directory
        self.temp_dir = 'TEST_UPLOAD'
        os.makedirs(self.temp_dir, exist_ok=True)
    
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
    
    def load_test_case(self):
        """Load one test case from upload list"""
        print("📂 Loading test case...")
        
        # Find the latest upload list JSON
        upload_files = [f for f in os.listdir('UPLOAD_READY') 
                       if f.startswith('upload_list_') and f.endswith('.json')]
        
        if not upload_files:
            print("   ❌ No upload list found!")
            return None
        
        latest_file = sorted(upload_files)[-1]
        file_path = os.path.join('UPLOAD_READY', latest_file)
        
        with open(file_path, 'r') as f:
            data = json.load(f)
        
        upload_list = data.get('upload_list', data)
        
        # Get first case for testing
        test_case = upload_list[0] if upload_list else None
        
        if test_case:
            print(f"   ✅ Test case loaded:")
            print(f"      Case ID: {test_case['Case_ID']}")
            print(f"      Name: {test_case['Last_Name']}")
            print(f"      File: {test_case['New_Filename']}\n")
        
        return test_case
    
    def find_file_in_drive(self, filename: str):
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
    
    def upload_document(self, case_id: int, file_path: str, comment: str = "") -> dict:
        """Upload a document to Logiqs"""
        try:
            url = self.document_url
            
            # Use query parameters with apikey (exactly like curl command)
            params = {
                'apikey': self.api_key,
                'CaseID': case_id,
                'Comment': comment
            }
            
            filename = os.path.basename(file_path)
            
            with open(file_path, 'rb') as f:
                files = {
                    'file': (filename, f, 'application/pdf')
                }
                
                print(f"   🌐 API Request:")
                print(f"      URL: {url}")
                print(f"      CaseID: {case_id}")
                print(f"      File: {filename}")
                print(f"      Comment: {comment}")
                
                response = requests.post(
                    url,
                    params=params,
                    files=files,
                    timeout=60
                )
            
            print(f"\n   📡 API Response:")
            print(f"      Status Code: {response.status_code}")
            print(f"      Response: {response.text[:500]}")
            
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
    
    def create_task(self, case_id: int, subject: str, due_date: str, comments: str = "") -> dict:
        """Create a task in Logiqs"""
        try:
            import base64
            from dateutil import parser as date_parser
            
            # Parse due date
            try:
                due_dt = date_parser.parse(due_date)
                due_date_utc = due_dt.strftime('%Y-%m-%dT%H:%M:%SZ')
                reminder_date = due_dt.replace(hour=9, minute=0).strftime('%Y-%m-%dT%H:%M:%SZ')
            except:
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
            
            payload = {
                'CaseID': case_id,
                'Subject': subject,
                'Reminder': reminder_date,
                'TaskType': 1,
                'DueDate': due_date_utc,
                'UserID': [],
                'PriorityID': 2,
                'StatusID': 0,
                'Comments': comments
            }
            
            print(f"   🌐 Task API Request:")
            print(f"      URL: {self.task_url}")
            print(f"      CaseID: {case_id}")
            print(f"      Subject: {subject}")
            print(f"      Due Date: {due_date_utc}")
            
            response = requests.post(
                self.task_url,
                headers=headers,
                json=payload,
                timeout=30
            )
            
            print(f"\n   📡 Task API Response:")
            print(f"      Status Code: {response.status_code}")
            print(f"      Response: {response.text[:500]}")
            
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
            print(f"      ❌ Error: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def get_tasks(self, case_id: int) -> dict:
        """Get tasks/events for a case"""
        try:
            # Note: Task endpoint might use different version, will test
            url = f"https://tps.logiqs.com/publicapi/V3/Task/Task"
            
            params = {
                'apikey': self.api_key,
                'CaseID': case_id
            }
            
            print(f"\n   🔍 Fetching tasks for Case {case_id}...")
            
            response = requests.get(
                url,
                params=params,
                timeout=30
            )
            
            print(f"   📡 Task API Response:")
            print(f"      Status Code: {response.status_code}")
            
            if response.status_code == 200:
                tasks = response.json()
                print(f"      Tasks found: {len(tasks) if isinstance(tasks, list) else 'N/A'}")
                return {
                    'success': True,
                    'tasks': tasks,
                    'status_code': response.status_code
                }
            else:
                print(f"      Error: {response.text[:200]}")
                return {
                    'success': False,
                    'error': response.text,
                    'status_code': response.status_code
                }
        
        except Exception as e:
            print(f"      ❌ Error: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def run_test(self):
        """Run the single file upload test"""
        print("\n" + "=" * 80)
        print("🧪 SINGLE FILE UPLOAD TEST")
        print("=" * 80)
        print("\nThis will test:")
        print("   1. Google Drive authentication")
        print("   2. File download with new naming")
        print("   3. Document upload to Logiqs")
        print("   4. Task/Event retrieval")
        print("=" * 80)
        
        try:
            # Step 1: Authenticate
            self.authenticate_google_drive()
            
            # Step 2: Load test case
            test_case = self.load_test_case()
            
            if not test_case:
                print("❌ No test case found!")
                return
            
            old_filename = test_case['Old_Filename']
            new_filename = test_case['New_Filename']
            case_id = test_case['Case_ID']
            last_name = test_case['Last_Name']
            tax_year = test_case.get('Tax_Year', '')
            
            print("=" * 80)
            print("📋 TEST CASE DETAILS")
            print("=" * 80)
            print(f"Case ID: {case_id}")
            print(f"Taxpayer: {last_name}")
            print(f"Tax Year: {tax_year}")
            print(f"Old Filename: {old_filename}")
            print(f"New Filename: {new_filename}")
            print("=" * 80)
            
            response = input("\nProceed with test upload? (yes/no): ")
            
            if response.lower() != 'yes':
                print("Test cancelled.")
                return
            
            # Step 3: Find and download file
            print("\n📥 STEP 1: DOWNLOAD FROM GOOGLE DRIVE")
            print("-" * 80)
            
            print(f"   🔍 Finding file: {old_filename}")
            file_info, folder = self.find_file_in_drive(old_filename)
            
            if not file_info:
                print(f"   ❌ File not found in Google Drive")
                return
            
            print(f"   ✅ Found in {folder}")
            
            local_path = os.path.join(self.temp_dir, new_filename)
            print(f"   ⬇️  Downloading as: {new_filename}")
            
            if not self.download_file(file_info['id'], local_path):
                print("   ❌ Download failed")
                return
            
            file_size_mb = os.path.getsize(local_path) / (1024 * 1024)
            print(f"   ✅ Downloaded successfully ({file_size_mb:.2f} MB)")
            
            # Step 4: Upload to Logiqs
            print("\n⬆️  STEP 2: UPLOAD TO LOGIQS")
            print("-" * 80)
            
            comment = f"IRS {tax_year} - {last_name} - Test Upload via API"
            upload_result = self.upload_document(case_id, local_path, comment)
            
            if upload_result['success']:
                print(f"\n   ✅ UPLOAD SUCCESSFUL!")
                
                # Step 4: Create Task
                print("\n📋 STEP 3: CREATE TASK")
                print("-" * 80)
                
                task_subject = f"Review IRS CP2000 Notice - {tax_year}"
                due_date = test_case.get('Response_Due_Date', 'June 05, 2024')
                task_comments = f"IRS CP2000 document uploaded for {last_name}. Tax Year: {tax_year}. Please review and respond before due date."
                
                create_task_result = self.create_task(
                    case_id=case_id,
                    subject=task_subject,
                    due_date=due_date,
                    comments=task_comments
                )
                
                if create_task_result['success']:
                    task_id = create_task_result.get('task_id')
                    print(f"\n   ✅ Task created successfully! (Task ID: {task_id})")
                else:
                    print(f"\n   ⚠️  Task creation failed")
                    print(f"   Error: {create_task_result.get('error', 'Unknown')}")
            else:
                print(f"\n   ❌ UPLOAD FAILED!")
                print(f"   Error: {upload_result.get('error', 'Unknown')}")
                print(f"   Status Code: {upload_result.get('status_code', 'N/A')}")
                create_task_result = {'success': False}
            
            # Step 5: Get tasks (verify)
            print("\n📋 STEP 4: VERIFY TASKS")
            print("-" * 80)
            
            task_result = self.get_tasks(case_id)
            
            if task_result['success']:
                tasks = task_result.get('tasks', [])
                if isinstance(tasks, list) and len(tasks) > 0:
                    print(f"\n   ✅ Found {len(tasks)} task(s)/event(s)")
                    for i, task in enumerate(tasks[:3], 1):
                        print(f"\n   Task {i}:")
                        if isinstance(task, dict):
                            print(f"      Subject: {task.get('Subject', 'N/A')}")
                            print(f"      Type: {task.get('Type', 'N/A')}")
                            print(f"      Status: {task.get('Status', 'N/A')}")
                else:
                    print(f"   ℹ️  No tasks found for this case")
            
            # Step 6: Cleanup
            if os.path.exists(local_path):
                os.remove(local_path)
                print(f"\n🗑️  Cleaned up temporary file")
            
            # Final summary
            print("\n" + "=" * 80)
            print("📊 TEST SUMMARY")
            print("=" * 80)
            print(f"Case ID: {case_id}")
            print(f"File: {new_filename}")
            print(f"Upload: {'✅ SUCCESS' if upload_result['success'] else '❌ FAILED'}")
            print(f"Tasks Retrieved: {'✅ YES' if task_result['success'] else '❌ NO'}")
            
            if upload_result['success']:
                print("\n✅ TEST PASSED! Ready for bulk upload.")
                print("\nNext step: Run python3 upload_to_logiqs.py for all 169 files")
            else:
                print("\n⚠️  TEST FAILED! Check the error above.")
                print("Fix the issue before proceeding with bulk upload.")
            
            print("=" * 80)
            
            # Save test results
            test_results = {
                'test_case': test_case,
                'upload_result': upload_result,
                'task_result': task_result,
                'timestamp': datetime.now().isoformat()
            }
            
            with open('test_upload_results.json', 'w') as f:
                json.dump(test_results, f, indent=2)
            
            print(f"\n💾 Test results saved to: test_upload_results.json")
            
        except Exception as e:
            print(f"\n❌ Test error: {str(e)}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    tester = SingleFileUploadTest()
    tester.run_test()

