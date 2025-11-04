from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
import logging

logger = logging.getLogger(__name__)

class GoogleSheetManager:
    def __init__(self, credentials):
        self.sheets_service = build('sheets', 'v4', credentials=credentials)

    def create_or_get_sheet(self, spreadsheet_name):
        """Create a new spreadsheet or get existing one"""
        try:
            # Check if spreadsheet exists
            result = self.sheets_service.spreadsheets().get(
                spreadsheetId=spreadsheet_name
            ).execute()
            return result['spreadsheetId']
        except:
            # Create new spreadsheet
            spreadsheet = {
                'properties': {
                    'title': spreadsheet_name
                },
                'sheets': [{
                    'properties': {
                        'title': 'Extracted Data',
                        'gridProperties': {
                            'rowCount': 1000,
                            'columnCount': 20
                        }
                    }
                }]
            }
            
            result = self.sheets_service.spreadsheets().create(
                body=spreadsheet
            ).execute()
            
            # Add headers
            headers = [
                ['File Name', 'SSN', 'Tax Year', 'Name', 'Address', 
                 'Proposed Balance Due', 'Status', 'Action']
            ]
            self.update_sheet(result['spreadsheetId'], 'A1:H1', headers)
            
            return result['spreadsheetId']

    def update_sheet(self, spreadsheet_id, range_name, values):
        """Update values in the spreadsheet"""
        body = {
            'values': values
        }
        result = self.sheets_service.spreadsheets().values().update(
            spreadsheetId=spreadsheet_id,
            range=range_name,
            valueInputOption='RAW',
            body=body
        ).execute()
        return result

    def append_row(self, spreadsheet_id, row_data):
        """Append a row of data to the spreadsheet"""
        range_name = 'Extracted Data!A:H'  # Adjust range based on your columns
        values = [[
            row_data['file_name'],
            row_data['ssn'],
            row_data['tax_year'],
            row_data['name'],
            row_data['address'],
            row_data['proposed_balance'],
            'Pending',
            '=HYPERLINK("#", "Review")'  # Add review button
        ]]
        
        body = {
            'values': values
        }
        
        result = self.sheets_service.spreadsheets().values().append(
            spreadsheetId=spreadsheet_id,
            range=range_name,
            valueInputOption='RAW',
            insertDataOption='INSERT_ROWS',
            body=body
        ).execute()
        return result