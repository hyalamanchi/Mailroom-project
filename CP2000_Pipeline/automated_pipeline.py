#!/usr/bin/env python3

import os
import sys
import json
import time
import logging
from datetime import datetime
from pathlib import Path
import pandas as pd
from dotenv import load_dotenv
from googleapiclient.http import MediaIoBaseDownload

# Import local modules
from enhanced_extractor import EnhancedExtractor
from logics_case_search import LogicsCaseSearcher
from google_drive_integration import GoogleDriveIntegration

# Load environment variables
load_dotenv()

# Google Drive Configuration
GOOGLE_DRIVE_FOLDERS = os.getenv('GOOGLE_DRIVE_FOLDERS', '').split(',')
GOOGLE_DRIVE_OUTPUT_FOLDER_ID = os.getenv('GOOGLE_DRIVE_OUTPUT_FOLDER_ID')

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Google Drive Configuration
GOOGLE_DRIVE_FOLDERS = os.getenv('GOOGLE_DRIVE_FOLDERS', '').split(',')
GOOGLE_DRIVE_OUTPUT_FOLDER_ID = os.getenv('GOOGLE_DRIVE_OUTPUT_FOLDER_ID')

class GoogleDriveHandler:
    def __init__(self):
        self.drive_service = GoogleDriveIntegration().get_service()
        self.sheets_service = GoogleDriveIntegration().get_sheets_service()
        
    def list_files_in_folder(self, folder_name):
        try:
            # Find folder ID
            results = self.drive_service.files().list(
                q=f"name = '{folder_name}' and mimeType = 'application/vnd.google-apps.folder'",
                fields="files(id, name)"
            ).execute()
            
            folder = results.get('files', [])
            if not folder:
                logger.warning(f"Folder not found: {folder_name}")
                return []
                
            folder_id = folder[0]['id']
            
            # List PDFs in folder
            files = self.drive_service.files().list(
                q=f"'{folder_id}' in parents and mimeType = 'application/pdf'",
                fields="files(id, name)"
            ).execute().get('files', [])
            
            return files
        except Exception as e:
            logger.error(f"Error listing files in folder {folder_name}: {str(e)}")
            return []
            
    def download_file(self, file_id, file_name):
        try:
            request = self.drive_service.files().get_media(fileId=file_id)
            file_path = os.path.join('TEMP_PROCESSING', file_name)
            
            if not os.path.exists('TEMP_PROCESSING'):
                os.makedirs('TEMP_PROCESSING')
                
            with open(file_path, 'wb') as f:
                downloader = MediaIoBaseDownload(f, request)
                done = False
                while done is False:
                    status, done = downloader.next_chunk()
                    
            return file_path
        except Exception as e:
            logger.error(f"Error downloading file {file_name}: {str(e)}")
            return None
            
    def move_file_in_drive(self, file_id, destination_folder_name):
        try:
            # Find destination folder ID
            results = self.drive_service.files().list(
                q=f"name = '{destination_folder_name}' and mimeType = 'application/vnd.google-apps.folder'",
                fields="files(id, name)"
            ).execute()
            
            folder = results.get('files', [])
            if not folder:
                logger.warning(f"Destination folder not found: {destination_folder_name}")
                return False
                
            folder_id = folder[0]['id']
            
            # Get current parents
            file = self.drive_service.files().get(
                fileId=file_id,
                fields='parents'
            ).execute()
            previous_parents = ",".join(file.get('parents', []))
            
            # Move file to new folder
            self.drive_service.files().update(
                fileId=file_id,
                addParents=folder_id,
                removeParents=previous_parents,
                fields='id, parents'
            ).execute()
            
            return True
        except Exception as e:
            logger.error(f"Error moving file in Drive: {str(e)}")
            return False

    def create_google_sheet(self, data, sheet_name):
        try:
            file_metadata = {
                'name': sheet_name,
                'parents': [GOOGLE_DRIVE_OUTPUT_FOLDER_ID],
                'mimeType': 'application/vnd.google-apps.spreadsheet'
            }
            
            file = self.drive_service.files().create(
                body=file_metadata,
                fields='id'
            ).execute()
            
            sheet_id = file.get('id')
            
            # Format data for sheets
            values = [list(data[0].keys())]  # Headers
            values.extend([list(row.values()) for row in data])
            
            body = {
                'values': values
            }
            
            self.sheets_service.spreadsheets().values().update(
                spreadsheetId=sheet_id,
                range='A1',
                valueInputOption='RAW',
                body=body
            ).execute()
            
            return sheet_id
        except Exception as e:
            logger.error(f"Error creating Google Sheet: {str(e)}")
            return None

class ProcessingLog:
    def __init__(self, log_file="processed_files_log.json"):
        self.log_file = log_file
        self.processed_files = self._load_log()
        
    def _load_log(self):
        if os.path.exists(self.log_file):
            try:
                with open(self.log_file, 'r') as f:
                    return json.load(f)
            except:
                return {}
        return {}
        
    def save_log(self):
        with open(self.log_file, 'w') as f:
            json.dump(self.processed_files, f, indent=2)
            
    def is_processed(self, filename):
        return filename in self.processed_files
        
    def mark_processed(self, filename, result):
        self.processed_files[filename] = {
            'timestamp': datetime.now().isoformat(),
            'result': result
        }
        self.save_log()

# Main pipeline class
class CP2000Pipeline:
    def __init__(self):
        # Initialize components
        self.extractor = EnhancedExtractor()
        self.case_searcher = LogicsCaseSearcher()
        self.drive = GoogleDriveIntegration()
        
        # Get paths from environment
        self.input_folder = os.getenv('INPUT_FOLDER')
        self.processed_folder = os.getenv('PROCESSED_FOLDER')
        self.quality_review_folder = os.getenv('QUALITY_REVIEW_FOLDER')
        
        # Create folders if they don't exist
        for folder in [self.input_folder, self.processed_folder, self.quality_review_folder]:
            os.makedirs(folder, exist_ok=True)
            
        # Initialize tracking lists
        self.matched_cases = []
        self.unmatched_cases = []

# Import for Google Drive
from googleapiclient.http import MediaIoBaseDownload

# Test run
if __name__ == "__main__":
    try:
        # Initialize components
        extractor = EnhancedExtractor()
        case_searcher = LogicsCaseSearcher()
        processing_log = ProcessingLog()
        drive_handler = GoogleDriveHandler()
        
        matched_cases = []
        unmatched_cases = []
        
        # Create required folders
        folders = ['TEMP_PROCESSING', 'CP2000', 'CP2000 NEW BATCH 2', 'PROCESSED_FILES', 'QUALITY_REVIEW']
        for folder in folders:
            os.makedirs(folder, exist_ok=True)
            
        # Process local folders
        local_folders = ['CP2000', 'CP2000 NEW BATCH 2', 'TEMP_PROCESSING']
        logger.info("Processing local folders...")
        
        for folder in local_folders:
            logger.info(f"\n📁 Processing folder: {folder}")
            if not os.path.exists(folder):
                logger.warning(f"Folder not found: {folder}")
                continue
                
            # Process each PDF file in the folder
            for filename in os.listdir(folder):
                if not filename.lower().endswith('.pdf'):
                    continue
                    
                if processing_log.is_processed(filename):
                    logger.info(f"Skipping already processed file: {filename}")
                    continue
                    
                file_path = os.path.join(folder, filename)
                logger.info(f"\n📄 Processing: {filename}")
                
                try:
                    # Extract information
                    extracted_data = extractor.extract_data(file_path)
                    
                    if extracted_data:
                        # Search for matching case
                        case_match = case_searcher.search_case(
                            ssn_last_4=extracted_data.get('ssn_last_4'),
                            last_name=extracted_data.get('last_name'),
                            first_name=extracted_data.get('first_name')
                        )
                        
                        if case_match:
                            logger.info(f"✅ Found matching case for {filename}")
                            matched_cases.append({
                                'filename': filename,
                                'folder': folder,
                                'extracted_data': extracted_data,
                                'case_match': case_match
                            })
                            
                            # Move to processed folder
                            dest_path = os.path.join('PROCESSED_FILES', filename)
                            os.rename(file_path, dest_path)
                            logger.info(f"📦 Moved {filename} to PROCESSED_FILES folder")
                        else:
                            logger.info(f"❌ No matching case found for {filename}")
                            unmatched_cases.append({
                                'filename': filename,
                                'folder': folder,
                                'extracted_data': extracted_data
                            })
                            
                            # Move to quality review folder
                            dest_path = os.path.join('QUALITY_REVIEW', filename)
                            os.rename(file_path, dest_path)
                            logger.info(f"📦 Moved {filename} to QUALITY_REVIEW folder")
                        
                        # Mark as processed
                        processing_log.mark_processed(filename, 'success')
                    else:
                        logger.warning(f"⚠️ No data extracted from {filename}")
                        processing_log.mark_processed(filename, 'failed_extraction')
                        
                except Exception as e:
                    logger.error(f"❌ Error processing {filename}: {str(e)}")
                    processing_log.mark_processed(filename, 'error')
                    
        # Process Google Drive if configured
        folder_id = os.getenv('GOOGLE_DRIVE_FOLDER_ID')
        if folder_id:
            logger.info("🔍 Searching for PDF files in Google Drive folder...")
            
            # List PDF files in the Google Drive folder
            files = drive_handler.drive_service.files().list(
                q=f"'{folder_id}' in parents and mimeType='application/pdf'",
                fields="files(id, name)"
            ).execute().get('files', [])
                
            logger.info("Processing files from Google Drive...")
            
            # Process each file from Google Drive
            for file in files:
                filename = file['name']
                file_id = file['id']
                
                if processing_log.is_processed(filename):
                    logger.info(f"Skipping already processed file: {filename}")
                    continue
                    
                try:
                    # Download file to temp processing folder
                    logger.info(f"⬇️ Downloading {filename}...")
                    temp_file_path = drive_handler.download_file(file_id, filename)
                    
                    if not temp_file_path:
                        logger.error(f"Failed to download {filename}")
                        continue
                    
                    # Extract information
                    logger.info(f"📄 Extracting data from {filename}...")
                    extracted_data = extractor.extract_data(temp_file_path)
                    
                    if extracted_data:
                        # Search for matching case
                        logger.info(f"🔍 Searching for matching case...")
                        case_match = case_searcher.search_case(
                            ssn_last_4=extracted_data.get('ssn_last_4'),
                            last_name=extracted_data.get('last_name'),
                            first_name=extracted_data.get('first_name')
                        )
                        
                        if case_match:
                            logger.info(f"✅ Found matching case for {filename}")
                            matched_cases.append({
                                'filename': filename,
                                'source': 'google_drive',
                                'extracted_data': extracted_data,
                                'case_match': case_match
                            })
                            
                            # Move file to processed folder in Google Drive
                            if drive_handler.move_file_in_drive(file_id, 'PROCESSED_FILES'):
                                logger.info(f"📦 Moved {filename} to PROCESSED_FILES folder")
                        else:
                            logger.info(f"❌ No matching case found for {filename}")
                            unmatched_cases.append({
                                'filename': filename,
                                'source': 'google_drive',
                                'extracted_data': extracted_data
                            })
                            
                            # Move file to quality review folder in Google Drive
                            if drive_handler.move_file_in_drive(file_id, 'QUALITY_REVIEW'):
                                logger.info(f"📦 Moved {filename} to QUALITY_REVIEW folder")
                        
                        # Mark as processed
                        processing_log.mark_processed(filename, 'success')
                    else:
                        logger.warning(f"⚠️ No data extracted from {filename}")
                        processing_log.mark_processed(filename, 'failed_extraction')
                        
                    # Clean up temp file
                    try:
                        os.remove(temp_file_path)
                    except:
                        pass
                        
                except Exception as e:
                    logger.error(f"❌ Error processing {filename}: {str(e)}")
                    processing_log.mark_processed(filename, 'error')
            
        logger.info("🔍 Searching for PDF files in Google Drive folder...")
        
        # List PDF files in the Google Drive folder
        files = drive_handler.drive_service.files().list(
            q=f"'{folder_id}' in parents and mimeType='application/pdf'",
            fields="files(id, name)"
        ).execute().get('files', [])
            
        logger.info("Processing files from Google Drive...")
        
        # Process each file from Google Drive
        for file in files:
            filename = file['name']
            file_id = file['id']
            
            if processing_log.is_processed(filename):
                logger.info(f"Skipping already processed file: {filename}")
                continue
                
            try:
                # Download file to temp processing folder
                logger.info(f"⬇️ Downloading {filename}...")
                temp_file_path = drive_handler.download_file(file_id, filename)
                
                if not temp_file_path:
                    logger.error(f"Failed to download {filename}")
                    continue
                
                # Extract information
                logger.info(f"📄 Extracting data from {filename}...")
                extracted_data = extractor.extract_data(temp_file_path)
                
                if extracted_data:
                    # Search for matching case
                    logger.info(f"🔍 Searching for matching case...")
                    case_match = case_searcher.search_case(
                        ssn_last_4=extracted_data.get('ssn_last_4'),
                        last_name=extracted_data.get('last_name'),
                        first_name=extracted_data.get('first_name')
                    )
                    
                    if case_match:
                        logger.info(f"✅ Found matching case for {filename}")
                        matched_cases.append({
                            'filename': filename,
                            'extracted_data': extracted_data,
                            'case_match': case_match
                        })
                        
                        # Move file to processed folder in Google Drive
                        if drive_handler.move_file_in_drive(file_id, 'PROCESSED_FILES'):
                            logger.info(f"📦 Moved {filename} to PROCESSED_FILES folder")
                    else:
                        logger.info(f"❌ No matching case found for {filename}")
                        unmatched_cases.append({
                            'filename': filename,
                            'extracted_data': extracted_data
                        })
                        
                        # Move file to quality review folder in Google Drive
                        if drive_handler.move_file_in_drive(file_id, 'QUALITY_REVIEW'):
                            logger.info(f"📦 Moved {filename} to QUALITY_REVIEW folder")
                    
                    # Mark as processed
                    processing_log.mark_processed(filename, 'success')
                else:
                    logger.warning(f"⚠️ No data extracted from {filename}")
                    processing_log.mark_processed(filename, 'failed_extraction')
                    
                # Clean up temp file
                try:
                    os.remove(temp_file_path)
                except:
                    pass
                    
            except Exception as e:
                logger.error(f"❌ Error processing {filename}: {str(e)}")
                processing_log.mark_processed(filename, 'error')
                    
        # Generate reports
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # Save matched cases
        if matched_cases:
            matched_file = f'CASE_MATCHES_{timestamp}.json'
            with open(matched_file, 'w') as f:
                json.dump(matched_cases, f, indent=2)
            logger.info(f"Saved matched cases to {matched_file}")
            
        # Save unmatched cases
        if unmatched_cases:
            unmatched_file = f'UNMATCHED_CASES_{timestamp}.json'
            with open(unmatched_file, 'w') as f:
                json.dump(unmatched_cases, f, indent=2)
            logger.info(f"Saved unmatched cases to {unmatched_file}")
            
        logger.info("Processing completed successfully")
        
    except Exception as e:
        logger.error(f"Pipeline error: {str(e)}")
        sys.exit(1)