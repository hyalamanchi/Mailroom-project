#!/usr/bin/env python3
"""
Create a single Google Sheet workbook with two sheets:
1. Matched Cases (with dropdown for APPROVE/UNDER_REVIEW/REJECT)
2. Unmatched Cases

Author: Assistant
Date: November 2024
"""

import json
import os
from datetime import datetime
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError


def load_case_data():
    """Load the most recent case matches JSON file"""
    json_files = [f for f in os.listdir('.') if f.startswith('CASE_MATCHES_') and f.endswith('.json')]
    
    if not json_files:
        print("❌ No CASE_MATCHES_*.json files found")
        return None
    
    # Get the most recent file
    latest_file = sorted(json_files, reverse=True)[0]
    print(f"📄 Loading case data from: {latest_file}")
    
    with open(latest_file, 'r') as f:
        return json.load(f)


def format_date(date_str):
    """Format date to readable format"""
    if not date_str or date_str == 'N/A':
        return 'N/A'
    return date_str


def generate_proposed_filename(case):
    """Generate proposed filename from case data"""
    # Extract components
    letter_type = case.get('letter_type', 'CP2000')
    tax_year = case.get('tax_year', '')
    notice_date = case.get('notice_date', '')
    taxpayer_name = (case.get('taxpayer_name', '') or '').title()
    
    # Format the filename: IRS_CORR_CP2000_2022_DTD_September 9, 2024_Flax.pdf
    if notice_date and taxpayer_name:
        return f"IRS_CORR_{letter_type}_{tax_year}_DTD_{notice_date}_{taxpayer_name}.pdf"
    
    # Fallback to original filename
    return case.get('filename', 'N/A')


def create_review_workbook():
    """Create a single workbook with matched and unmatched sheets"""
    
    print("🚀 Starting workbook creation...")
    
    # Load credentials
    creds = Credentials.from_authorized_user_file('token.json')
    sheets_service = build('sheets', 'v4', credentials=creds)
    drive_service = build('drive', 'v3', credentials=creds)
    
    # Load case data
    case_data = load_case_data()
    if not case_data:
        return
    
    matched_cases = case_data.get('matched_cases', [])
    unmatched_cases = case_data.get('unmatched_cases', [])
    
    print(f"✅ Found {len(matched_cases)} matched cases")
    print(f"✅ Found {len(unmatched_cases)} unmatched cases")
    
    # Create timestamp for filename
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    workbook_title = f"CP2000_Case_Review_{timestamp}"
    
    # Create the spreadsheet
    spreadsheet = {
        'properties': {
            'title': workbook_title
        },
        'sheets': [
            {
                'properties': {
                    'title': 'Matched Cases',
                    'gridProperties': {
                        'frozenRowCount': 3,
                        'frozenColumnCount': 1
                    }
                }
            },
            {
                'properties': {
                    'title': 'Unmatched Cases',
                    'gridProperties': {
                        'frozenRowCount': 3,
                        'frozenColumnCount': 1
                    }
                }
            }
        ]
    }
    
    print("📝 Creating spreadsheet...")
    spreadsheet = sheets_service.spreadsheets().create(body=spreadsheet).execute()
    spreadsheet_id = spreadsheet['spreadsheetId']
    spreadsheet_url = f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}"
    
    print(f"✅ Spreadsheet created: {spreadsheet_url}")
    
    # Get sheet IDs
    matched_sheet_id = spreadsheet['sheets'][0]['properties']['sheetId']
    unmatched_sheet_id = spreadsheet['sheets'][1]['properties']['sheetId']
    
    # Define headers
    headers = [
        'Case_ID',
        'Original_Filename',
        'Proposed_Filename',
        'Taxpayer_Name',
        'SSN_Last_4',
        'Letter_Type',
        'Tax_Year',
        'Notice_Date',
        'Due_Date',
        'Source_Folder',
        'Match_Confidence',
        'Status',
        'Notes'
    ]
    
    # Prepare data for matched cases
    matched_data = []
    # Add instruction rows
    matched_data.append(['', '', '', '', '', '', '', '', '', '', '', '', ''])
    matched_data.append([
        'Review each matched case below',
        '', '', '', '', '', '', '', '', '', '', '', ''
    ])
    matched_data.append([
        'In Status column, enter: APPROVE, UNDER_REVIEW, or REJECT',
        '', '', '', '', '', '', '', '', '', '', '', ''
    ])
    matched_data.append(['', '', '', '', '', '', '', '', '', '', '', '', ''])
    matched_data.append([
        'Add any notes in Notes column',
        '', '', '', '', '', '', '', '', '', '', '', ''
    ])
    matched_data.append(['', '', '', '', '', '', '', '', '', '', '', '', ''])
    # Add header row
    matched_data.append(headers)
    
    # Add matched case data
    for case in matched_cases:
        # Get case ID from logics_case_id field
        case_id = case.get('logics_case_id', 'N/A')
        
        # Get confidence from logics_case_data if available
        match_confidence = 'High'
        if 'logics_case_data' in case:
            conf = case['logics_case_data'].get('matchConfidence', 1.0)
            if conf >= 0.9:
                match_confidence = 'High'
            elif conf >= 0.7:
                match_confidence = 'Medium'
            else:
                match_confidence = 'Low'
        
        row = [
            str(case_id),
            case.get('filename', 'N/A'),
            generate_proposed_filename(case),
            (case.get('taxpayer_name', 'N/A') or 'N/A').title(),
            str(case.get('ssn_last_4', 'N/A')),
            case.get('letter_type', 'N/A'),
            str(case.get('tax_year', 'N/A')),
            format_date(case.get('notice_date', 'N/A')),
            format_date(case.get('response_due_date', 'N/A')),
            'TEMP_PROCESSING',
            match_confidence,
            '',  # Status - empty for user to fill
            ''   # Notes - empty for user to add
        ]
        matched_data.append(row)
    
    # Prepare data for unmatched cases
    unmatched_data = []
    # Add instruction rows
    unmatched_data.append(['', '', '', '', '', '', '', '', '', '', '', '', ''])
    unmatched_data.append([
        'These cases could not be automatically matched in Logics',
        '', '', '', '', '', '', '', '', '', '', '', ''
    ])
    unmatched_data.append([
        'Please review and manually match or create new cases',
        '', '', '', '', '', '', '', '', '', '', '', ''
    ])
    unmatched_data.append(['', '', '', '', '', '', '', '', '', '', '', '', ''])
    unmatched_data.append([
        'In Status column, enter: APPROVE, UNDER_REVIEW, or REJECT',
        '', '', '', '', '', '', '', '', '', '', '', ''
    ])
    unmatched_data.append(['', '', '', '', '', '', '', '', '', '', '', '', ''])
    # Add header row
    unmatched_data.append(headers)
    
    # Add unmatched case data
    for case in unmatched_cases:
        row = [
            'N/A',  # No case ID for unmatched
            case.get('filename', 'N/A'),
            generate_proposed_filename(case),
            (case.get('taxpayer_name', 'N/A') or 'N/A').title(),
            str(case.get('ssn_last_4', 'N/A')),
            case.get('letter_type', 'N/A'),
            str(case.get('tax_year', 'N/A')),
            format_date(case.get('notice_date', 'N/A')),
            format_date(case.get('response_due_date', 'N/A')),
            'TEMP_PROCESSING',
            'Unmatched',
            '',  # Status - empty for user to fill
            ''   # Notes - empty for user to add
        ]
        unmatched_data.append(row)
    
    # Update both sheets with data
    print("📊 Updating sheet data...")
    
    batch_update_values = [
        {
            'range': 'Matched Cases!A1',
            'values': matched_data
        },
        {
            'range': 'Unmatched Cases!A1',
            'values': unmatched_data
        }
    ]
    
    body = {
        'valueInputOption': 'USER_ENTERED',
        'data': batch_update_values
    }
    
    sheets_service.spreadsheets().values().batchUpdate(
        spreadsheetId=spreadsheet_id,
        body=body
    ).execute()
    
    print("✅ Data updated")
    
    # Apply formatting
    print("🎨 Applying formatting...")
    
    # Header row is at row 7 (index 6)
    header_row_index = 6
    
    requests = []
    
    # Format both sheets
    for sheet_id, sheet_name in [(matched_sheet_id, 'Matched'), (unmatched_sheet_id, 'Unmatched')]:
        
        # 1. Format header row (row 7)
        requests.append({
            'repeatCell': {
                'range': {
                    'sheetId': sheet_id,
                    'startRowIndex': header_row_index,
                    'endRowIndex': header_row_index + 1,
                },
                'cell': {
                    'userEnteredFormat': {
                        'backgroundColor': {'red': 0.2, 'green': 0.4, 'blue': 0.7},
                        'textFormat': {
                            'foregroundColor': {'red': 1.0, 'green': 1.0, 'blue': 1.0},
                            'fontSize': 11,
                            'bold': True
                        },
                        'horizontalAlignment': 'CENTER',
                        'verticalAlignment': 'MIDDLE'
                    }
                },
                'fields': 'userEnteredFormat(backgroundColor,textFormat,horizontalAlignment,verticalAlignment)'
            }
        })
        
        # 2. Format instruction rows (rows 1-6) - light yellow background
        requests.append({
            'repeatCell': {
                'range': {
                    'sheetId': sheet_id,
                    'startRowIndex': 0,
                    'endRowIndex': 6,
                },
                'cell': {
                    'userEnteredFormat': {
                        'backgroundColor': {'red': 1.0, 'green': 0.95, 'blue': 0.8},
                        'textFormat': {
                            'fontSize': 10,
                            'italic': True
                        }
                    }
                },
                'fields': 'userEnteredFormat(backgroundColor,textFormat)'
            }
        })
        
        # 3. Alternate row colors for data rows (starting from row 8)
        requests.append({
            'addConditionalFormatRule': {
                'rule': {
                    'ranges': [{
                        'sheetId': sheet_id,
                        'startRowIndex': header_row_index + 1,
                        'endRowIndex': 1000
                    }],
                    'booleanRule': {
                        'condition': {
                            'type': 'CUSTOM_FORMULA',
                            'values': [{'userEnteredValue': '=MOD(ROW(),2)=0'}]
                        },
                        'format': {
                            'backgroundColor': {'red': 0.95, 'green': 0.95, 'blue': 0.95}
                        }
                    }
                },
                'index': 0
            }
        })
        
        # 4. Add data validation for Status column (column L = index 11)
        num_data_rows = len(matched_data) if sheet_id == matched_sheet_id else len(unmatched_data)
        
        requests.append({
            'setDataValidation': {
                'range': {
                    'sheetId': sheet_id,
                    'startRowIndex': header_row_index + 1,
                    'endRowIndex': num_data_rows,
                    'startColumnIndex': 11,  # Status column
                    'endColumnIndex': 12
                },
                'rule': {
                    'condition': {
                        'type': 'ONE_OF_LIST',
                        'values': [
                            {'userEnteredValue': 'APPROVE'},
                            {'userEnteredValue': 'UNDER_REVIEW'},
                            {'userEnteredValue': 'REJECT'}
                        ]
                    },
                    'showCustomUi': True,
                    'strict': False
                }
            }
        })
        
        # 5. Conditional formatting for Status column
        # Green for APPROVE
        requests.append({
            'addConditionalFormatRule': {
                'rule': {
                    'ranges': [{
                        'sheetId': sheet_id,
                        'startRowIndex': header_row_index + 1,
                        'endRowIndex': num_data_rows,
                        'startColumnIndex': 11,
                        'endColumnIndex': 12
                    }],
                    'booleanRule': {
                        'condition': {
                            'type': 'TEXT_EQ',
                            'values': [{'userEnteredValue': 'APPROVE'}]
                        },
                        'format': {
                            'backgroundColor': {'red': 0.7, 'green': 0.9, 'blue': 0.7},
                            'textFormat': {'bold': True}
                        }
                    }
                },
                'index': 1
            }
        })
        
        # Yellow for UNDER_REVIEW
        requests.append({
            'addConditionalFormatRule': {
                'rule': {
                    'ranges': [{
                        'sheetId': sheet_id,
                        'startRowIndex': header_row_index + 1,
                        'endRowIndex': num_data_rows,
                        'startColumnIndex': 11,
                        'endColumnIndex': 12
                    }],
                    'booleanRule': {
                        'condition': {
                            'type': 'TEXT_EQ',
                            'values': [{'userEnteredValue': 'UNDER_REVIEW'}]
                        },
                        'format': {
                            'backgroundColor': {'red': 1.0, 'green': 0.9, 'blue': 0.6},
                            'textFormat': {'bold': True}
                        }
                    }
                },
                'index': 2
            }
        })
        
        # Red for REJECT
        requests.append({
            'addConditionalFormatRule': {
                'rule': {
                    'ranges': [{
                        'sheetId': sheet_id,
                        'startRowIndex': header_row_index + 1,
                        'endRowIndex': num_data_rows,
                        'startColumnIndex': 11,
                        'endColumnIndex': 12
                    }],
                    'booleanRule': {
                        'condition': {
                            'type': 'TEXT_EQ',
                            'values': [{'userEnteredValue': 'REJECT'}]
                        },
                        'format': {
                            'backgroundColor': {'red': 0.95, 'green': 0.7, 'blue': 0.7},
                            'textFormat': {'bold': True}
                        }
                    }
                },
                'index': 3
            }
        })
        
        # 6. Auto-resize columns
        requests.append({
            'autoResizeDimensions': {
                'dimensions': {
                    'sheetId': sheet_id,
                    'dimension': 'COLUMNS',
                    'startIndex': 0,
                    'endIndex': 13
                }
            }
        })
    
    # Execute all formatting requests
    body = {'requests': requests}
    sheets_service.spreadsheets().batchUpdate(
        spreadsheetId=spreadsheet_id,
        body=body
    ).execute()
    
    print("✅ Formatting applied")
    
    # Move to the specified project folder
    project_folder_id = '18e8lj66Mdr7PFGhJ7ySYtsnkNgiuczmx'
    
    print("📁 Moving to Mail Room Project folder...")
    
    try:
        # Get current parents
        file = drive_service.files().get(
            fileId=spreadsheet_id,
            fields='parents'
        ).execute()
        
        previous_parents = ",".join(file.get('parents', []))
        
        # Move to project folder
        drive_service.files().update(
            fileId=spreadsheet_id,
            addParents=project_folder_id,
            removeParents=previous_parents,
            fields='id, parents'
        ).execute()
        
        print("✅ Moved to project folder")
        
    except HttpError as error:
        print(f"⚠️  Could not move file: {error}")
    
    # Print summary
    print("\n" + "="*70)
    print("✅ WORKBOOK CREATED SUCCESSFULLY!")
    print("="*70)
    print(f"\n📊 Workbook: {workbook_title}")
    print(f"🔗 URL: {spreadsheet_url}")
    print(f"\n📝 Sheet 1: Matched Cases ({len(matched_cases)} cases)")
    print(f"📝 Sheet 2: Unmatched Cases ({len(unmatched_cases)} cases)")
    print("\n" + "="*70)
    print("\n📋 INSTRUCTIONS:")
    print("1. Open the spreadsheet using the URL above")
    print("2. Go to 'Matched Cases' tab to review matched cases")
    print("3. Go to 'Unmatched Cases' tab to review unmatched cases")
    print("4. Click on any cell in the Status column to see the dropdown")
    print("5. Select APPROVE, UNDER_REVIEW, or REJECT for each case")
    print("6. Add any notes in the Notes column")
    print("\n💡 The Status column has:")
    print("   • Dropdown validation (click to see options)")
    print("   • Color coding: Green (APPROVE), Yellow (UNDER_REVIEW), Red (REJECT)")
    print("\n🚀 After review, approved cases can be processed automatically")
    print("="*70)
    
    return spreadsheet_id, spreadsheet_url


if __name__ == '__main__':
    try:
        create_review_workbook()
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

