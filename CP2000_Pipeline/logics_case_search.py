import os
import json
import logging
from datetime import datetime
from typing import Dict, Optional
import requests
import time

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class LogicsCaseSearcher:
    def __init__(self, max_retries: int = 3, retry_delay: float = 2.0):
        # Use the API key for TI Parser
        self.api_key = os.environ.get('LOGICS_API_KEY', "sk_BIWGmwZeahwOyI9ytZNMnZmM_mY1SOcpl4OXlmFpJvA")
        
        # Set the base URL and full endpoint for case matching
        self.base_url = "https://tiparser-dev.onrender.com"
        self.match_endpoint = f"{self.base_url}/case-data/api/case/match"

        # Set up API Key authentication with the correct headers
        self.headers = {
            "Content-Type": "application/json",
            "X-API-Key": self.api_key  # TI Parser expects X-API-Key header
        }
        
        logger.info(f"✓ Found API Key (first 10 chars): {self.api_key[:10]}...")
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.session = requests.Session()
        self.session.headers.update(self.headers)
        
        logger.info("✅ LogicsCaseSearcher initialized with enhanced error handling")

    def _make_request_with_retry(self, method: str, url: str, **kwargs) -> Optional[requests.Response]:
        """Make HTTP request with retry logic"""
        for attempt in range(self.max_retries):
            try:
                logger.debug(f"Making {method} request to {url}")
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
                logger.warning(f"Attempt {attempt + 1} failed: {str(e)}")
                if attempt < self.max_retries - 1:
                    delay = self.retry_delay * (2 ** attempt)  # Exponential backoff
                    logger.info(f"Retrying in {delay} seconds...")
                    time.sleep(delay)
                else:
                    logger.error("Maximum retries exceeded")
                    break
                    
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
            Optional[Dict]: Case details if found, None otherwise
        """
        try:
            # Use the specific case match endpoint
            logger.info(f"🔍 Searching for case with SSN: ***-**-{ssn_last_4}, Name: {last_name}")
            logger.debug(f"   Endpoint: {self.match_endpoint}")
            
            # Prepare search parameters with all available information
            params = {
                'lastName': last_name.strip().upper(),  # Ensure uppercase for matching
                'last4SSN': ssn_last_4.strip(),  # Using last4SSN field as required by the API
            }
            
            # Add first name if available
            if first_name:
                params['firstName'] = first_name.strip().upper()
            
            # Add any additional search criteria from file_info if available
            if file_info:
                if 'tax_year' in file_info:
                    params['taxYear'] = file_info['tax_year']
            
            logger.debug(f"   Request Parameters: {json.dumps(params, indent=2)}")
            
            # Make the POST request to the case match endpoint
            response = self._make_request_with_retry('POST', self.match_endpoint, json=params)
            
            if response:
                try:
                    # Parse the response
                    data = response.json()
                    logger.debug(f"   Response Data: {json.dumps(data, indent=2)}")
                    
                    if isinstance(data, dict):
                        # Check if match was found
                        if data.get('status') == 'success' and data.get('matchFound', False):
                            # Extract case data from the nested structure
                            case_data_wrapper = data.get('caseData', {})
                            if case_data_wrapper.get('status') == 'success':
                                case_info = case_data_wrapper.get('data', {})
                                case_id = case_info.get('CaseID')  # API returns CaseID, not caseId
                                
                                if case_id:
                                    match_data = {
                                        'case_data': {
                                            'caseId': case_id,
                                            'taxpayerName': f"{case_info.get('FirstName', '')} {case_info.get('LastName', '')}".strip(),
                                            'ssn': case_info.get('SSN', ''),
                                            'status': case_info.get('StatusName', 'active'),
                                            'matchConfidence': data.get('nameSimilarity', 1.0),
                                            'matchType': data.get('matchType', 'exact'),
                                            'type': case_info.get('TAX_RELIEF_TAX_TYPE', ''),
                                            'assignedTo': case_info.get('SetOfficer', ''),
                                            'email': case_info.get('Email', ''),
                                            'phone': case_info.get('CellPhone', ''),
                                            'address': case_info.get('Address', ''),
                                            'city': case_info.get('City', ''),
                                            'state': case_info.get('State', ''),
                                            'zip': case_info.get('Zip', '')
                                        }
                                    }
                                    
                                    logger.info(f"✅ Found matching case: {case_id}")
                                    return match_data
                        
                        # No match found
                        if data.get('status') == 'success' and not data.get('matchFound', False):
                            logger.info(f"ℹ️ {data.get('message', 'No matching cases found')}")
                            return None
                        
                        # Error in response
                        if 'error' in data or data.get('status') == 'error':
                            error_msg = data.get('message', data.get('error', {}).get('message', 'Unknown error'))
                            logger.warning(f"⚠️ API Error: {error_msg}")
                            return None
                    
                    logger.info("ℹ️ No matching cases found")
                    return None
                        
                except json.JSONDecodeError as je:
                    logger.error(f"❌ Failed to parse API response: {str(je)}")
                    return None
                    
            else:
                logger.error("❌ Failed to get response from Logics API")
                return None
                
        except Exception as e:
            logger.error(f"❌ Unexpected error searching case: {str(e)}")
            return None
    
    def test_connection(self) -> bool:
        """Test the connection to Logics API and validate response format"""
        try:
            # Use the search endpoint with test data
            test_params = {
                'lastName': 'TEST',
                'last4SSN': '0000'
            }
            
            response = self._make_request_with_retry('POST', self.match_endpoint, json=test_params)
            
            if response:
                try:
                    data = response.json()
                    
                    # Check if response has expected structure
                    if isinstance(data, dict):
                        if data.get('status') == 'success':  # Valid response format
                            logger.info("✅ TI Parser API connection successful and response format valid")
                            if data.get('matchFound'):
                                logger.info(f"   Test case matched (unexpected but OK)")
                            else:
                                logger.info(f"   No match for test data (expected)")
                            return True
                    
                    logger.warning("⚠️ Logics API connected but response format unexpected")
                    logger.debug(f"Response data: {json.dumps(data, indent=2)}")
                    return False
                    
                except json.JSONDecodeError:
                    logger.error("❌ Logics API response not valid JSON")
                    return False
            else:
                logger.error("❌ Failed to get response from Logics API")
                return False
                
        except Exception as e:
            logger.error(f"❌ Logics API connection test failed: {str(e)}")
            return False

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
    
    # Test case search with test data
    test_cases = [
        ("1234", "TEST"),
        ("5678", "DEMO")
    ]
    
    for ssn, last in test_cases:
        logger.info(f"\nTesting search with: Last={last}, SSN=xxx-xx-{ssn}")
        test_result = searcher.search_case(ssn, last)
        if test_result:
            logger.info(f"✅ Test case search successful: {test_result}")
        else:
            logger.info(f"ℹ️ No results found for {last} (xxx-xx-{ssn})")
    
    logger.info("Enhanced Logics integration test complete")

if __name__ == "__main__":
    main()