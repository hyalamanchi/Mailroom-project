# CP2000 Pipeline Project

## Overview
This project handles the automation of CP2000 document processing using LogicsCase integration and Google Drive for file management.

## Setup Instructions

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Google Drive Service Account Setup

#### Create a Google Cloud Project
1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Click "Select a project" → "New Project"
3. Name your project and click "Create"

#### Enable the Google Drive API
1. In your project dashboard, go to "APIs & Services" → "Library"
2. Search for "Google Drive API"
3. Click "Enable"

#### Create Service Account
1. Go to "APIs & Services" → "Credentials"
2. Click "Create Credentials" → "Service Account"
3. Fill in:
   - Name: `cp2000-pipeline`
   - Role: "Editor" (or custom role with needed permissions)
   - Click "Done"

#### Create and Download Service Account Key
1. In the Service Accounts list, click on your new service account
2. Go to "Keys" tab
3. Click "Add Key" → "Create new key"
4. Choose "JSON" format
5. Click "Create"
   - The key file will download automatically
6. Rename the downloaded file to `google_credentials.json`
7. Move it to your project root directory

#### Share Target Folders
1. Go to your Google Drive
2. Right-click on the folders you need to access
3. Click "Share"
4. Add the service account email (it looks like: `name@project.iam.gserviceaccount.com`)
5. Give "Editor" access
6. Click "Share"

### 3. Test the Setup
Run the test suites:
```bash
# Test LogicsCase integration
python3 -m unittest test_logics_search.py

# Test Google Drive integration
python3 -m unittest test_google_drive_handler.py
```

## Project Structure
- `logics_case_search.py`: LogicsCase API integration
- `google_drive_handler.py`: Google Drive operations management
- `hundred_percent_accuracy_extractor.py`: Document data extraction
- `production_extractor.py`: Production pipeline implementation
- `test_logics_search.py`: LogicsCase integration tests
- `test_google_drive_handler.py`: Google Drive integration tests

## Common Issues and Solutions

### Insufficient Drive Permissions
If you get "insufficientFilePermissions" errors:
1. Double-check that you shared the folders with the correct service account email
2. Ensure the service account has "Editor" access
3. Verify the credentials file is correctly placed and named

### LogicsCase Integration Issues
If you get "Unexpected response format" warnings:
1. Verify your credentials in `credentials.json`
2. Check the API endpoint status
3. Run the test suite for detailed diagnostics

### Authentication Failed
If authentication fails:
1. Verify the credentials files are valid JSON
2. Check if the service account email matches the shared folder permissions
3. Regenerate the keys if needed

## Important Notes
- Keep your credential files (`google_credentials.json` and `credentials.json`) secure
- Never commit credential files to version control
- Add both credential files to your `.gitignore`
- The service account needs explicit sharing for each folder it needs to access
- Consider using environment variables for credential paths in production