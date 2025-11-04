import os
import logging
from typing import Optional
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class GoogleDriveHandler:
    """Handle all Google Drive operations with proper authentication"""
    
    def __init__(self, credentials_path: str = 'google_credentials.json'):
        """Initialize with service account credentials"""
        try:
            self.credentials = service_account.Credentials.from_service_account_file(
                credentials_path,
                scopes=['https://www.googleapis.com/auth/drive.file']
            )
            self.service = build('drive', 'v3', credentials=self.credentials)
            logger.info("✅ Google Drive handler initialized successfully")
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize Google Drive handler: {str(e)}")
            raise
    
    def move_file(self, file_id: str, new_parent_folder_id: str, remove_parent_folder_id: Optional[str] = None) -> bool:
        """Move a file to a new folder with enhanced error handling"""
        try:
            # Prepare the update parameters
            file_params = {'addParents': new_parent_folder_id}
            if remove_parent_folder_id:
                file_params['removeParents'] = remove_parent_folder_id
            
            # Execute the move
            self.service.files().update(
                fileId=file_id,
                body={},
                **file_params,
                fields='id, parents'
            ).execute()
            
            logger.info(f"✅ Successfully moved file {file_id} to folder {new_parent_folder_id}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to move file {file_id}: {str(e)}")
            return False
    
    def get_folder_id(self, folder_name: str, parent_folder_id: Optional[str] = None) -> Optional[str]:
        """Get folder ID by name with optional parent folder"""
        try:
            query = f"mimeType='application/vnd.google-apps.folder' and name='{folder_name}'"
            if parent_folder_id:
                query += f" and '{parent_folder_id}' in parents"
            
            results = self.service.files().list(
                q=query,
                spaces='drive',
                fields='files(id, name)'
            ).execute()
            
            items = results.get('files', [])
            if items:
                return items[0]['id']
                
            return None
            
        except Exception as e:
            logger.error(f"❌ Failed to get folder ID for {folder_name}: {str(e)}")
            return None
    
    def create_folder(self, folder_name: str, parent_folder_id: Optional[str] = None) -> Optional[str]:
        """Create a new folder with optional parent"""
        try:
            file_metadata = {
                'name': folder_name,
                'mimeType': 'application/vnd.google-apps.folder'
            }
            
            if parent_folder_id:
                file_metadata['parents'] = [parent_folder_id]
            
            folder = self.service.files().create(
                body=file_metadata,
                fields='id'
            ).execute()
            
            logger.info(f"✅ Created folder: {folder_name}")
            return folder.get('id')
            
        except Exception as e:
            logger.error(f"❌ Failed to create folder {folder_name}: {str(e)}")
            return None
    
    def upload_file(self, file_path: str, parent_folder_id: Optional[str] = None) -> Optional[str]:
        """Upload a file to Google Drive"""
        try:
            file_metadata = {
                'name': os.path.basename(file_path)
            }
            
            if parent_folder_id:
                file_metadata['parents'] = [parent_folder_id]
            
            media = MediaFileUpload(
                file_path,
                resumable=True
            )
            
            file = self.service.files().create(
                body=file_metadata,
                media_body=media,
                fields='id'
            ).execute()
            
            logger.info(f"✅ Uploaded file: {file_path}")
            return file.get('id')
            
        except Exception as e:
            logger.error(f"❌ Failed to upload file {file_path}: {str(e)}")
            return None
    
    def ensure_folder_exists(self, folder_name: str, parent_folder_id: Optional[str] = None) -> Optional[str]:
        """Get folder ID or create if it doesn't exist"""
        folder_id = self.get_folder_id(folder_name, parent_folder_id)
        if not folder_id:
            folder_id = self.create_folder(folder_name, parent_folder_id)
        return folder_id