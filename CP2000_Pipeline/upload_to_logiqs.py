"""
Module for uploading documents and tasks to Logiqs
"""

import os
import logging
import requests
from typing import Optional, Dict

logger = logging.getLogger(__name__)

class LogiqsDocumentUploader:
    """Class for uploading documents and tasks to Logiqs"""
    
    def __init__(self):
        # Set API config
        self.api_key = "sk_BIWGmwZeahwOyI9ytZNMnZmM_mY1SOcpl4OXlmFpJvA"
        self.base_url = "https://tiparser-dev.onrender.com/case-data/api"
        
        # Set up headers
        self.headers = {
            "Content-Type": "application/json",
            "X-API-Key": self.api_key
        }
        
        logger.info("✅ Document uploader initialized")
    
    def upload_document(self, case_id: str, file_path: str, 
                       document_type: str, tax_year: str) -> bool:
        """
        Upload document to Logiqs
        
        Args:
            case_id (str): Case ID to upload to
            file_path (str): Path to document file
            document_type (str): Type of document (e.g. CP2000)
            tax_year (str): Tax year for document
            
        Returns:
            bool: True if upload successful
        """
        try:
            if not os.path.exists(file_path):
                logger.error(f"File not found: {file_path}")
                return False
            
            # Prepare upload
            url = f"{self.base_url}/documents/upload"
            
            files = {
                'file': (os.path.basename(file_path), 
                        open(file_path, 'rb'),
                        'application/pdf')
            }
            
            data = {
                'caseId': case_id,
                'documentType': document_type,
                'taxYear': tax_year
            }
            
            # Make request
            response = requests.post(
                url,
                headers=self.headers,
                data=data,
                files=files
            )
            
            response.raise_for_status()
            
            logger.info(f"✅ Document uploaded for Case {case_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to upload document: {str(e)}")
            return False
            
    def create_cp2000_task(self, case_id: str, notice_date: str,
                          tax_year: str, ref_number: str) -> bool:
        """
        Create CP2000 task in Logiqs
        
        Args:
            case_id (str): Case ID to create task for
            notice_date (str): Date of CP2000 notice
            tax_year (str): Tax year of notice
            ref_number (str): CP2000 reference number
            
        Returns:
            bool: True if task created successfully
        """
        try:
            url = f"{self.base_url}/tasks/create"
            
            data = {
                'caseId': case_id,
                'taskType': 'CP2000_REVIEW',
                'dueDate': notice_date,  # Use notice date as due date
                'details': {
                    'taxYear': tax_year,
                    'noticeDate': notice_date,
                    'referenceNumber': ref_number,
                    'status': 'NEW'
                }
            }
            
            # Create task
            response = requests.post(
                url,
                headers=self.headers,
                json=data
            )
            
            response.raise_for_status()
            
            logger.info(f"✅ Created CP2000 task for Case {case_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to create task: {str(e)}")
            return False
    
    def update_task_status(self, task_id: str, status: str) -> bool:
        """
        Update task status
        
        Args:
            task_id (str): ID of task to update
            status (str): New status (NEW, IN_PROGRESS, COMPLETED, etc)
            
        Returns:
            bool: True if update successful
        """
        try:
            url = f"{self.base_url}/tasks/{task_id}/status"
            
            data = {
                'status': status
            }
            
            response = requests.patch(
                url, 
                headers=self.headers,
                json=data
            )
            
            response.raise_for_status()
            
            logger.info(f"✅ Updated task {task_id} status to {status}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to update task status: {str(e)}")
            return False
    
def main():
    """Test the uploader"""
    uploader = LogiqsDocumentUploader()
    
    # Test with sample data
    test_case_id = "123456"
    test_file = "sample.pdf"
    
    if os.path.exists(test_file):
        logger.info("Testing document upload...")
        result = uploader.upload_document(
            test_case_id,
            test_file,
            "CP2000",
            "2022"
        )
        
        if result:
            logger.info("✅ Upload test successful")
        else:
            logger.error("❌ Upload test failed")
            
        # Test task creation
        logger.info("Testing task creation...")
        task_result = uploader.create_cp2000_task(
            test_case_id,
            "2023-10-15",
            "2022",
            "1234-5678"
        )
        
        if task_result:
            logger.info("✅ Task creation test successful")
        else:
            logger.error("❌ Task creation test failed")
    else:
        logger.warning(f"Test file not found: {test_file}")

if __name__ == "__main__":
    main()