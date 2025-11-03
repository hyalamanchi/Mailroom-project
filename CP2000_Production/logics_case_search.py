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

# Import robust API utilities (TRA_API pattern)
from api_utils import run_resiliently, resilient_api_call

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()
# Support multiple environment variable names because the project has both
# LOGICS_API_KEY and LOGIQS_API_KEY used in different places / docs.
LOGICS_API_KEY = os.getenv('LOGICS_API_KEY') or os.getenv('LOGIQS_API_KEY') or os.getenv('LOGIQS_SECRET_TOKEN')

class LogicsCaseSearcher:
    def __init__(self, max_retries: int = 3, retry_delay: float = 2.0):
        # Get API key from environment variables, checking all possible names
        self.api_key = os.getenv('LOGIQS_API_KEY') or os.getenv('LOGICS_API_KEY') or os.getenv('LOGIQS_SECRET_TOKEN')
        if not self.api_key:
            error_msg = "No Logics API key found in environment variables"
            logger.error(f"❌ {error_msg}")
            logger.error("Please set LOGIQS_API_KEY or LOGICS_API_KEY environment variable")
            raise ValueError(error_msg)

        self.base_url = "https://tps.logiqs.com/publicapi/V3"

        # Set up API Key authentication (simpler)
        self.headers = {
                "Content-Type": "application/json",
                "Accept": "application/json",
                "X-Api-Key": self.api_key  # Use X-Api-Key as that's the most common format
            }
        logger.info(f"✓ Found API Key (first 10 chars): {self.api_key[:10]}...")
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.session = requests.Session()
        self.session.headers.update(self.headers)
        
        # Validate API key (log but don't raise so the pipeline can still run offline)
        if not self.api_key:
            logger.warning("LOGICS_API_KEY / LOGIQS_API_KEY not set - Logics matching will be disabled")
        
        logger.info("✅ LogicsCaseSearcher initialized with enhanced error handling")

    def _make_request_with_retry(self, method: str, url: str, **kwargs) -> Optional[requests.Response]:
        """
        Make HTTP request with retry logic using run_resiliently.
        
        This is a wrapper around the robust run_resiliently pattern from TRA_API,
        which handles quota errors, rate limiting, network issues, and timeouts.
        
        Args:
            method: HTTP method (GET, POST, etc.)
            url: Request URL
            **kwargs: Additional request parameters
            
        Returns:
            Response object or None if all retries failed
        """
        def _request_internal():
            """Internal request function wrapped by run_resiliently"""
            logger.debug(f"Making {method} request to {url}")
            response = self.session.request(method, url, **kwargs)
            
            # Check for rate limiting
            if response.status_code == 429:
                retry_after = int(response.headers.get('Retry-After', self.retry_delay))
                logger.warning(f"Rate limited. Waiting {retry_after} seconds...")
                time.sleep(retry_after)
                # Raise to trigger retry
                raise Exception(f"Rate limited (429), retry after {retry_after}s")
            
            # Raise for other error status codes to trigger retry
            response.raise_for_status()
            return response
        
        try:
            # Use run_resiliently for automatic retry with backoff
            return run_resiliently(
                _request_internal,
                max_retries=self.max_retries,
                initial_delay=self.retry_delay,
                backoff_factor=2.0,
                max_delay=60.0
            )
        except Exception as e:
            logger.error(f"All retry attempts failed for {method} {url}: {str(e)}")
            return None

    def search_case(self, ssn_last_4: str, last_name: str, first_name: Optional[str] = None, file_info: Optional[Dict] = None) -> Optional[Dict]:
        """
        Search for a case using SSN last 4 digits and name with enhanced error handling
        
        Args:
            ssn_last_4 (str): Last 4 digits of SSN
            last_name (str): Last name of taxpayer
            first_name (Optional[str]): First name of taxpayer if available
            file_info (Optional[Dict]): Information about the source file
            
        Returns:
            Optional[Dict]: Case details and output file path if found, None otherwise
        """
        try:
            # Use Case/FindCase endpoint
            url = f"{self.base_url}/Case/FindCase"
            
            # Prepare search parameters based on test_logics_api.py
            params = {
                'LastName': last_name.strip(),
                'Last4SSN': ssn_last_4,  # Just use the last 4 digits
                'ActiveOnly': True  # Only get active cases
            }
            if first_name:
                params['FirstName'] = first_name.strip()

            logger.info(f"Searching Logics for SSN: ***-**-{ssn_last_4}, Name: {last_name}")
            logger.debug(f"   Request URL: {url}")
            logger.debug(f"   Parameters: {params}")
            
            # Use POST request for Case search
            response = self._make_request_with_retry('POST', url, json=params, headers=self.headers)
            
            if response:
                # Log response status for debugging
                logger.debug(f"   Response Status: {response.status_code}")
                
                # Check for specific error responses
                if response.status_code == 403:
                    error_data = response.json()
                    error_msg = error_data.get('detail', 'Access forbidden')
                    
                    if 'Invalid or expired API Key' in error_msg:
                        logger.error("❌ Logics API Key is invalid or expired")
                        logger.error("   Please contact Logics admin to verify API key permissions")
                        logger.error(f"   API Key (first 10 chars): {self.api_key[:10]}...")
                    elif 'X-API-Key header is missing' in error_msg:
                        logger.error("❌ X-API-Key header not being sent correctly")
                    else:
                        logger.error(f"❌ API returned 403: {error_msg}")
                    
                    return None

                # Enhanced response debugging
                logger.info("\n=== Response Debug Info ===")
                logger.info(f"Status Code: {response.status_code}")
                logger.info(f"Content-Type: {response.headers.get('content-type', 'not specified')}")
                
                # First try to get raw content
                try:
                    content = response.text[:2000]
                    logger.info(f"\nRaw Content (truncated to 2000 chars):\n{content}")
                except Exception as e:
                    logger.error(f"Could not get raw content: {str(e)}")
                    
                # Then try to parse as JSON if possible
                try:
                    data = response.json()
                    logger.info(f"\nJSON Response:\n{json.dumps(data, indent=2)}")
                except Exception as e:
                    logger.error(f"Failed to parse response as JSON: {str(e)}")
                    if "<!DOCTYPE html>" in response.text:
                        logger.error("Received HTML response instead of JSON")
                    elif "<?xml" in response.text:
                        logger.error("Received XML response instead of JSON")
                        
                logger.info("=== End Response Debug Info ===\n")
                
                # Success - parse response
                data = response.json()
                
                # Log full response for debugging
                logger.debug(f"   Full API Response: {json.dumps(data, indent=2)[:500]}")
                
                                                # Enhanced response validation with case output handling
                from case_output_handler import CaseOutputHandler
                output_handler = CaseOutputHandler()
                
                if isinstance(data, dict):
                    # Check for new API format with matchFound
                    if data.get('matchFound') == True:
                        case_data = data.get('caseData', {})
                        if case_data and case_data.get('data'):
                            case_id = case_data['data'].get('CaseID')
                            if case_id:
                                logger.info(f"✅ Case found: CaseID {case_id}")
                                
                                # Format and save case output with action buttons
                                # Use provided file_info or create empty dict
                                file_info = file_info or {
                                    'filename': '',
                                    'filepath': '',
                                    'date_received': datetime.now().strftime('%Y-%m-%d')
                                }
                                
                                formatted_output = output_handler.format_case_output(case_data['data'], file_info)
                                output_path = output_handler.save_case_output(formatted_output)
                                logger.info(f"✅ Case output saved with action buttons: {output_path}")
                                
                                return {'case_data': data, 'output_file': output_path}
                            else:
                                logger.warning("matchFound=true but no CaseID in response")
                                return None
                        else:
                            logger.warning("matchFound=true but no caseData in response")
                            return None
                    elif data.get('matchFound') == False:
                        logger.info("ℹ️ No matching cases found (matchFound=false)")
                        return None
                    # Fallback: Check for old API format with direct case_id
                    elif data.get('case_id'):
                        logger.info(f"✅ Case found (old format): {data['case_id']}")
                        return data
                    elif data.get('cases') and len(data['cases']) > 0:
                        # Handle multiple cases returned (old format)
                        case = data['cases'][0]  # Take first match
                        logger.info(f"✅ Multiple cases found (old format), using first: {case.get('case_id')}")
                        return case
                    else:
                        logger.info("ℹ️ No matching cases found (no matchFound field)")
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
            
            url = f"{self.base_url}/Documents/CaseDocument"
            
            logger.info(f"Uploading document: {os.path.basename(file_path)} to case {case_id}")
            
            # Prepare the file for upload
            with open(file_path, 'rb') as f:
                files = {
                    'File': (os.path.basename(file_path), f, 'application/pdf')
                }
                
                data = {
                    'CaseID': case_id,
                    'Comment': document_type,
                    'FileCategoryID': None  # Optional
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
            url = f"{self.base_url}/Case/CaseInfo"
            
            logger.info(f"Retrieving case details for: {case_id}")
            
            params = {'CaseID': case_id}
            response = self._make_request_with_retry('GET', url, params=params)
            
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
            # Use Case/GetStatus endpoint for health check
            url = f"{self.base_url}/Case/GetStatus"
            params = {}  # No parameters needed, but keep consistent with other methods
            response = self._make_request_with_retry('GET', url, params=params)
            
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
    
    # Test case search with more realistic test data
    test_cases = [
        ("5678", "JONES", "MARY"),  # More common name format
        ("9012", "GARCIA-LOPEZ", None),  # Hyphenated name, no first name
        ("3456", "O'CONNOR", "PATRICK"),  # Name with apostrophe
    ]
    
    for ssn, last, first in test_cases:
        logger.info(f"\nTesting search with: Last={last}, First={first}, SSN=xxx-xx-{ssn}")
        test_result = searcher.search_case(ssn, last, first)
        if test_result:
            logger.info(f"✅ Test case search successful: {test_result}")
        else:
            logger.info(f"❌ No results found for {last}, {first if first else ''} (xxx-xx-{ssn})")
    
    logger.info("Enhanced Logics integration test complete")

if __name__ == "__main__":
    main()