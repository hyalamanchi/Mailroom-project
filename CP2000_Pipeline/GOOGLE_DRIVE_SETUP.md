# Google Drive Setup Instructions

1. Go to [Google Cloud Console](https://console.cloud.google.com)
2. Create a new project called "cp2000-pipeline"
3. Enable the Google Drive API:
   - Search for "Google Drive API" in the search bar
   - Click "Enable"

4. Create a Service Account:
   - Go to "IAM & Admin" > "Service Accounts"
   - Click "Create Service Account"
   - Name: cp2000-pipeline-sa
   - Description: Service account for CP2000 Pipeline
   - Click "Create"
   - Add Role: "Editor"
   - Click "Continue"
   - Click "Done"

5. Create and download credentials:
   - Click on the service account you just created
   - Go to "Keys" tab
   - Click "Add Key" > "Create new key"
   - Choose "JSON"
   - Save the downloaded file as `google_credentials.json` in the project root

6. Share Google Drive folders:
   - Open your Google Drive
   - Go to each folder used by the pipeline:
     - Source folder
     - CP2000_UNMATCHED folder
   - Click "Share"
   - Add the service account email (ends with @project-id.iam.gserviceaccount.com)
   - Give "Editor" access
   - Click "Send"

The service account email will be in the downloaded credentials file. Look for the "client_email" field.