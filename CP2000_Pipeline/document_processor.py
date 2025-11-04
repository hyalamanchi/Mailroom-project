import os
import logging
from typing import Optional, Dict, Tuple
from logics_case_search import LogicsCaseSearcher
from google_drive_handler import GoogleDriveHandler

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DocumentProcessor:
    def __init__(self, credentials_path: str = 'google_credentials.json'):
        """Initialize with both LogicsCase and Google Drive handlers"""
        self.logics = LogicsCaseSearcher()
        self.drive = GoogleDriveHandler(credentials_path)
        logger.info("✅ Document processor initialized")
    
    def process_taxpayer_document(self, 
                                ssn_last_4: str, 
                                last_name: str, 
                                first_name: Optional[str],
                                document_path: str,
                                source_folder_id: str) -> Tuple[bool, Optional[str]]:
        """
        Process a taxpayer document by:
        1. Finding their case in LogicsCase
        2. Moving the document to appropriate Google Drive folder
        
        Returns:
            Tuple[bool, Optional[str]]: (success, case_id if found)
        """
        try:
            # Search for case in LogicsCase
            case_result = self.logics.search_case(ssn_last_4, last_name, first_name)
            
            if not case_result or 'case_data' not in case_result:
                logger.warning(f"❌ No case found for {last_name} (xxx-xx-{ssn_last_4})")
                return False, None
            
            case_data = case_result['case_data']
            case_id = case_data.get('caseId') or case_data.get('case_id')
            
            if not case_id:
                logger.error("❌ Case found but no case ID in response")
                return False, None
            
            # Ensure case folder exists in Google Drive
            case_folder_name = f"Case_{case_id}"
            case_folder_id = self.drive.ensure_folder_exists(case_folder_name, source_folder_id)
            
            if not case_folder_id:
                logger.error(f"❌ Failed to create/find folder for case {case_id}")
                return False, case_id
            
            # Upload document to case folder
            file_name = os.path.basename(document_path)
            file_id = self.drive.upload_file(document_path, case_folder_id)
            
            if not file_id:
                logger.error(f"❌ Failed to upload {file_name} to case folder")
                return False, case_id
            
            logger.info(f"✅ Successfully processed document for case {case_id}")
            return True, case_id
            
        except Exception as e:
            logger.error(f"❌ Error processing document: {str(e)}")
            return False, None
    
    def validate_setup(self) -> bool:
        """
        Validate both LogicsCase and Google Drive setup
        """
        try:
            # Test LogicsCase connection
            if not self.logics.test_connection():
                logger.error("❌ LogicsCase connection failed")
                return False
            
            # Test Google Drive access
            test_folder_name = "_test_folder"
            test_folder_id = self.drive.create_folder(test_folder_name)
            
            if not test_folder_id:
                logger.error("❌ Google Drive access failed")
                return False
            
            # Clean up test folder
            logger.info("✅ Setup validation successful")
            return True
            
        except Exception as e:
            logger.error(f"❌ Setup validation failed: {str(e)}")
            return False

def main():
    """Test the integrated document processor"""
    processor = DocumentProcessor('google_credentials.json')
    
    if not processor.validate_setup():
        logger.error("❌ Setup validation failed")
        return
    
    # Example test case
    test_data = {
        'ssn_last_4': '1234',
        'last_name': 'TEST',
        'first_name': 'JOHN',
        'document_path': 'path/to/test.pdf',
        'source_folder_id': 'your_source_folder_id'
    }
    
    success, case_id = processor.process_taxpayer_document(**test_data)
    
    if success:
        logger.info(f"✅ Test successful - Case ID: {case_id}")
    else:
        logger.error("❌ Test failed")

if __name__ == "__main__":
    main()