"""
GOOGLE DRIVE DOWNLOAD AND RENAME TOOL

This script automates:
1. Download PDFs from Google Drive (169 matched files)
2. Rename with proper convention: {CaseID}_CP2000_{Date}.pdf
3. Prepare for upload to Logiqs

USAGE:
    python download_and_rename.py
    
OUTPUT:
    READY_FOR_UPLOAD/ folder with renamed PDFs
"""

import os
import json
import shutil
from datetime import datetime
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload

class GoogleDriveDownloader:
    """Download and rename PDFs from Google Drive"""
    
    def __init__(self):
        self.SCOPES = ['https://www.googleapis.com/auth/drive.readonly']
        self.service = None
        
        # Google Drive folder
        self.folders = {
            'main_folder': '18e8lj66Mdr7PFGhJ7ySYtsnkNgiuczmx'
        }
        
        # Output directory
        self.output_dir = 'READY_FOR_UPLOAD'
        
        # Upload list
        self.upload_list = []
        
    def authenticate(self):
        """Authenticate with Google Drive using service account"""
        print("🔐 Authenticating with Google Drive...")
        
        try:
            creds = service_account.Credentials.from_service_account_file(
                'service-account-key.json',
                scopes=self.SCOPES
            )
            
            self.service = build('drive', 'v3', credentials=creds)
            print("   ✅ Authenticated successfully (Service Account)")
            
        except FileNotFoundError:
            print("   ❌ Error: service-account-key.json not found")
            print("   💡 Place your service account JSON file in the project root")
            raise
        except Exception as e:
            print(f"   ❌ Authentication error: {str(e)}")
            raise
    
    def load_upload_list(self):
        """Load the upload list with naming convention"""
        print("\n📂 Loading upload list...")
        
        # Find the latest upload list JSON file
        upload_files = [f for f in os.listdir('UPLOAD_READY') if f.startswith('upload_list_') and f.endswith('.json')]
        
        if not upload_files:
            print("   ❌ No upload list found!")
            print("   💡 Please run: python generate_upload_list.py first")
            return False
        
        # Get most recent
        latest_file = sorted(upload_files)[-1]
        file_path = os.path.join('UPLOAD_READY', latest_file)
        
        with open(file_path, 'r') as f:
            data = json.load(f)
        
        self.upload_list = data['upload_list']
        print(f"   ✅ Loaded {len(self.upload_list)} files from {latest_file}")
        return True
    
    def find_file_in_drive(self, filename):
        """Find a file in Google Drive across all folders"""
        for folder_name, folder_id in self.folders.items():
            try:
                # Search for file in this folder
                query = f"name='{filename}' and '{folder_id}' in parents and trashed=false"
                results = self.service.files().list(
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
    
    def download_file(self, file_id, output_path):
        """Download a file from Google Drive"""
        try:
            request = self.service.files().get_media(fileId=file_id)
            
            with open(output_path, 'wb') as f:
                downloader = MediaIoBaseDownload(f, request)
                done = False
                while not done:
                    status, done = downloader.next_chunk()
            
            return True
        except Exception as e:
            print(f"      ❌ Download error: {str(e)}")
            return False
    
    def download_and_rename_all(self):
        """Download all files and rename them"""
        print(f"\n🚀 Downloading and renaming {len(self.upload_list)} files...")
        print("=" * 80)
        
        # Create output directory
        if os.path.exists(self.output_dir):
            response = input(f"\n⚠️  {self.output_dir}/ already exists. Overwrite? (yes/no): ")
            if response.lower() != 'yes':
                print("Aborted.")
                return
            shutil.rmtree(self.output_dir)
        
        os.makedirs(self.output_dir)
        
        # Statistics
        downloaded = 0
        renamed = 0
        not_found = []
        errors = []
        
        # Process each file
        for idx, entry in enumerate(self.upload_list, 1):
            old_filename = entry['Old_Filename']
            new_filename = entry['New_Filename']
            case_id = entry['Case_ID']
            last_name = entry['Last_Name']
            
            # Progress
            if idx % 10 == 0:
                print(f"\n📊 Progress: {idx}/{len(self.upload_list)} ({idx/len(self.upload_list)*100:.1f}%)")
            
            print(f"\n{idx:3d}. {last_name:15s} (Case: {case_id})")
            print(f"     Old: {old_filename[:60]}")
            print(f"     New: {new_filename}")
            
            # Find file in Drive
            file_info, folder = self.find_file_in_drive(old_filename)
            
            if not file_info:
                print(f"     ❌ Not found in Google Drive")
                not_found.append(entry)
                continue
            
            print(f"     📁 Found in: {folder}")
            
            # Download with new name
            output_path = os.path.join(self.output_dir, new_filename)
            
            if self.download_file(file_info['id'], output_path):
                print(f"     ✅ Downloaded and renamed")
                downloaded += 1
                renamed += 1
            else:
                print(f"     ❌ Download failed")
                errors.append(entry)
        
        # Summary
        print("\n" + "=" * 80)
        print("📊 DOWNLOAD AND RENAME SUMMARY")
        print("=" * 80)
        print(f"\nTotal Files: {len(self.upload_list)}")
        print(f"✅ Downloaded & Renamed: {renamed}")
        print(f"❌ Not Found: {len(not_found)}")
        print(f"❌ Errors: {len(errors)}")
        print(f"\n✅ Success Rate: {renamed/len(self.upload_list)*100:.1f}%")
        
        # Save results
        results = {
            'timestamp': datetime.now().isoformat(),
            'total_files': len(self.upload_list),
            'downloaded': renamed,
            'not_found': len(not_found),
            'errors': len(errors),
            'not_found_list': not_found,
            'error_list': errors
        }
        
        results_file = os.path.join(self.output_dir, 'download_results.json')
        with open(results_file, 'w') as f:
            json.dump(results, f, indent=2)
        
        print(f"\n💾 Results saved to: {results_file}")
        
        if not_found:
            print(f"\n⚠️  {len(not_found)} files not found in Google Drive:")
            for entry in not_found[:5]:
                print(f"   • {entry['Old_Filename']}")
            if len(not_found) > 5:
                print(f"   ... and {len(not_found) - 5} more")
        
        print(f"\n📂 Renamed files location: {self.output_dir}/")
        print(f"\n🎯 Next step: Upload {renamed} files to Logiqs")
    
    def run(self):
        """Main execution"""
        print("\n" + "=" * 80)
        print("🚀 GOOGLE DRIVE DOWNLOAD AND RENAME TOOL")
        print("=" * 80)
        
        # Authenticate
        self.authenticate()
        
        # Load upload list
        if not self.load_upload_list():
            return
        
        # Download and rename
        self.download_and_rename_all()
        
        print("\n" + "=" * 80)
        print("✅ DOWNLOAD AND RENAME COMPLETE")
        print("=" * 80)

if __name__ == "__main__":
    downloader = GoogleDriveDownloader()
    downloader.run()

