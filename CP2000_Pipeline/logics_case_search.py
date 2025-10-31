import os
import json
import pandas as pd
import requests
from dotenv import load_dotenv
from pathlib import Path
import logging
import time
from typing import Dict, List, Optional, Tuple
from datetime import datetime

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()
LOGICS_API_KEY = os.getenv('LOGICS_API_KEY')

class LogicsCaseSearcher:
    def __init__(self, max_retries: int = 3, retry_delay: float = 2.0):
        self.api_key = os.getenv('LOGICS_API_KEY')
        self.base_url = "https://tiparser-dev.onrender.com/case-data/api"
        self.headers = {
            "X-API-Key": self.api_key,
            "Content-Type": "application/json"
        }
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.session = requests.Session()
        self.session.headers.update(self.headers)
        
        # Validate API key
        if not self.api_key:
            raise ValueError("LOGICS_API_KEY environment variable not set")
        
        logger.info("✅ LogicsCaseSearcher initialized with enhanced error handling")

    def _make_request_with_retry(self, method: str, url: str, **kwargs) -> Optional[requests.Response]:
        """
        Make HTTP request with retry logic
        
        Args:
            method: HTTP method (GET, POST, etc.)
            url: Request URL
            **kwargs: Additional request parameters
            
        Returns:
            Response object or None if all retries failed
        """
        for attempt in range(self.max_retries):
            try:
                logger.debug(f"Making {method} request to {url} (attempt {attempt + 1}/{self.max_retries})")
                response = self.session.request(method, url, **kwargs)
                
                # Check for rate limiting
                if response.status_code == 429:
                    retry_after = int(response.headers.get('Retry-After', self.retry_delay))
                    logger.warning(f"Rate limited. Waiting {retry_after} seconds...")
                    time.sleep(retry_after)
                    continue
                
                response.raise_for_status()
                return response
                
            except requests.exceptions.RequestException as e:
                logger.warning(f"Request failed (attempt {attempt + 1}/{self.max_retries}): {e}")
                
                if attempt < self.max_retries - 1:
                    wait_time = self.retry_delay * (2 ** attempt)  # Exponential backoff
                    logger.info(f"Retrying in {wait_time} seconds...")
                    time.sleep(wait_time)
                else:
                    logger.error(f"All retry attempts failed for {method} {url}")
                    return None
        
        return None

    def search_case(self, ssn_last_4: str, last_name: str, first_name: Optional[str] = None) -> Optional[Dict]:
        """
        Search for a case using SSN last 4 digits and name with enhanced error handling
        
        Args:
            ssn_last_4 (str): Last 4 digits of SSN
            last_name (str): Last name of taxpayer
            first_name (Optional[str]): First name of taxpayer if available
            
        Returns:
            Optional[Dict]: Case details if found, None otherwise
        """
        try:
            url = f"{self.base_url}/case/match"
            
            # Prepare request body for POST request
            payload = {
                "ssn_last_4": ssn_last_4,
                "last_name": last_name.strip().upper()  # Normalize case
            }
            if first_name:
                payload["first_name"] = first_name.strip().title()  # Normalize case
            
            logger.info(f"Searching Logiqs for SSN: {ssn_last_4}, Name: {last_name}")
            
            # Use POST instead of GET for the /case/match endpoint
            response = self._make_request_with_retry('POST', url, json=payload)
            
            if response:
                data = response.json()
                
                # Enhanced response validation
                if isinstance(data, dict):
                    if data.get('case_id'):
                        logger.info(f"✅ Case found: {data['case_id']}")
                        return data
                    elif data.get('cases') and len(data['cases']) > 0:
                        # Handle multiple cases returned
                        case = data['cases'][0]  # Take first match
                        logger.info(f"✅ Multiple cases found, using first: {case.get('case_id')}")
                        return case
                    else:
                        logger.info("ℹ️ No matching cases found")
                        return None
                else:
                    logger.warning("Unexpected response format from Logics API")
                    return None
            else:
                logger.error("Failed to get response from Logics API")
                return None
                
        except Exception as e:
            logger.error(f"Unexpected error searching case: {str(e)}")
            return None
            
    def upload_document(self, case_id: str, file_path: str, document_type: str) -> Optional[Dict]:
        """
        Upload a document to a Logics case with enhanced error handling
        
        Args:
            case_id (str): The Logics case ID
            file_path (str): Path to the document file
            document_type (str): Type of document being uploaded
            
        Returns:
            Optional[Dict]: Upload response if successful, None otherwise
        """
        try:
            # Validate file exists and is readable
            if not os.path.exists(file_path):
                logger.error(f"File not found: {file_path}")
                return None
            
            file_size = os.path.getsize(file_path)
            if file_size == 0:
                logger.error(f"File is empty: {file_path}")
                return None
            
            # Check file size limit (adjust as needed)
            max_size = 50 * 1024 * 1024  # 50MB
            if file_size > max_size:
                logger.error(f"File too large: {file_size} bytes (max: {max_size})")
                return None
            
            url = f"{self.base_url}/cases/{case_id}/documents"
            
            logger.info(f"Uploading document: {os.path.basename(file_path)} to case {case_id}")
            
            # Prepare the file for upload
            with open(file_path, 'rb') as f:
                files = {
                    'file': (os.path.basename(file_path), f, 'application/pdf')
                }
            
                data = {
                    'document_type': document_type,
                    'upload_timestamp': datetime.now().isoformat()
                }
                
                # Use retry mechanism for upload
                response = self._make_request_with_retry('POST', url, files=files, data=data)
                
                if response:
                    result = response.json()
                    if result.get('document_id'):
                        logger.info(f"✅ Document uploaded successfully: {result['document_id']}")
                        return result
                    else:
                        logger.error(f"Upload failed - no document_id in response: {result}")
                        return None
                else:
                    logger.error("Failed to upload document - no response")
                    return None
                    
        except FileNotFoundError:
            logger.error(f"File not found: {file_path}")
            return None
        except PermissionError:
            logger.error(f"Permission denied accessing file: {file_path}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error uploading document: {str(e)}")
            return None
            
    def create_task(self, case_id: str, task_type: str, description: str) -> Optional[Dict]:
        """
        Create a task in Logics case with enhanced error handling
        
        Args:
            case_id (str): The Logics case ID
            task_type (str): Type of task
            description (str): Task description
            
        Returns:
            Optional[Dict]: Task details if created successfully, None otherwise
        """
        try:
            url = f"{self.base_url}/cases/{case_id}/tasks"
            
            data = {
                'task_type': task_type,
                'description': description,
                'created_timestamp': datetime.now().isoformat(),
                'priority': 'HIGH' if 'CP2000' in task_type else 'MEDIUM'
            }
            
            logger.info(f"Creating task '{task_type}' for case {case_id}")
            
            response = self._make_request_with_retry('POST', url, json=data)
            
            if response:
                result = response.json()
                if result.get('task_id'):
                    logger.info(f"✅ Task created successfully: {result['task_id']}")
                    return result
                else:
                    logger.error(f"Task creation failed - no task_id in response: {result}")
                    return None
            else:
                logger.error("Failed to create task - no response")
                return None
                
        except Exception as e:
            logger.error(f"Unexpected error creating task: {str(e)}")
            return None
    
    def get_case_details(self, case_id: str) -> Optional[Dict]:
        """
        Get detailed information about a case
        
        Args:
            case_id (str): The Logics case ID
            
        Returns:
            Optional[Dict]: Case details if found, None otherwise
        """
        try:
            url = f"{self.base_url}/cases/{case_id}"
            
            logger.info(f"Retrieving case details for: {case_id}")
            
            response = self._make_request_with_retry('GET', url)
            
            if response:
                result = response.json()
                logger.info(f"✅ Case details retrieved for: {case_id}")
                return result
            else:
                logger.error(f"Failed to retrieve case details for: {case_id}")
                return None
                
        except Exception as e:
            logger.error(f"Unexpected error retrieving case details: {str(e)}")
            return None
    
    def test_connection(self) -> bool:
        """
        Test the connection to Logics API
        
        Returns:
            bool: True if connection successful, False otherwise
        """
        try:
            url = f"{self.base_url}/health"  # Adjust endpoint as needed
            response = self._make_request_with_retry('GET', url)
            
            if response and response.status_code == 200:
                logger.info("✅ Logics API connection successful")
                return True
            else:
                logger.error("❌ Logics API connection failed")
                return False
                
        except Exception as e:
            logger.error(f"❌ Logics API connection test failed: {str(e)}")
            return False

def generate_document_name(original_filename: str, case_id: str) -> str:
    """
    Generate a new document name following the naming convention with enhanced logic
    
    Args:
        original_filename (str): Original filename
        case_id (str): Logics case ID
        
    Returns:
        str: New filename following the convention
    """
    try:
    # Extract components from original filename
        filename_stem = Path(original_filename).stem
        
        # Try to extract date from various patterns
        date_str = None
        
        # Pattern 1: DTD MM.DD.YYYY or DTD MM DD YYYY
        dtd_patterns = [
            r'DTD[_\s]+(\d{2})\.(\d{2})\.(\d{4})',      # DTD 07.15.2024
            r'DTD[_\s]+(\d{2})[\s\-](\d{2})[\s\-](\d{4})', # DTD 07-15-2024
        ]
        
        for pattern in dtd_patterns:
            import re
            matches = re.findall(pattern, filename_stem)
            if matches:
                month, day, year = matches[0]
                date_str = f"{month}.{day}.{year}"
                break
        
        # Pattern 2: Look for any date pattern
        if not date_str:
            date_patterns = [
                r'(\d{2})\.(\d{2})\.(\d{4})',  # MM.DD.YYYY
                r'(\d{2})[\s\-](\d{2})[\s\-](\d{4})',  # MM-DD-YYYY
            ]
            
            for pattern in date_patterns:
                matches = re.findall(pattern, filename_stem)
                if matches:
                    month, day, year = matches[0]
                    date_str = f"{month}.{day}.{year}"
                    break
        
        # Fallback to current date
        if not date_str:
            date_str = datetime.now().strftime('%m.%d.%Y')
            logger.warning(f"No date found in filename {original_filename}, using current date")
        
        # Create new filename: CaseID_CP2000_DateReceived.pdf
        new_filename = f"{case_id}_CP2000_{date_str}.pdf"
        
        logger.info(f"Generated filename: {original_filename} → {new_filename}")
        return new_filename
        
    except Exception as e:
        logger.error(f"Error generating document name: {e}")
        # Fallback naming
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        return f"{case_id}_CP2000_{timestamp}.pdf"

def main():
    """Test the enhanced Logics integration"""
    logger.info("Testing enhanced Logics integration...")
    
    # Test connection
    searcher = LogicsCaseSearcher()
    if searcher.test_connection():
        logger.info("✅ Logics API connection test passed")
    else:
        logger.error("❌ Logics API connection test failed")
        return
    
    # Test case search (example)
    test_result = searcher.search_case("1234", "SMITH", "JOHN")
    if test_result:
        logger.info(f"✅ Test case search successful: {test_result}")
    else:
        logger.info("ℹ️ Test case search returned no results (expected for test data)")
    
    logger.info("Enhanced Logics integration test complete")

if __name__ == "__main__":
    main()