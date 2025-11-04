# 🌟 GOOGLE DRIVE MONITORING - COMPLETE GUIDE

## 📋 Overview

The Enhanced Auto Watcher now supports **automatic monitoring of Google Drive folders**! Upload a CP2000 PDF to your Google Drive folder and it will be automatically:

1. ✅ Detected within minutes
2. ✅ Downloaded securely
3. ✅ Processed & data extracted
4. ✅ Matched against Logics CRM
5. ✅ Added to your Google Sheet with timestamp
6. ✅ Cleaned up (temp files removed)
7. ✅ Tracked to prevent reprocessing

---

## 🚀 Quick Start

### **Basic Usage:**
```bash
cd "/Users/hemalathayalamanchi/Desktop/logicscase integration/CP2000_Pipeline"

# Start with Google Drive monitoring
./start_enhanced_watcher.sh SPREADSHEET_ID 300 DRIVE_FOLDER_ID
```

### **Example with Your Setup:**
```bash
./start_enhanced_watcher.sh 1_z6KrPLBRKlgJYQjmKKmvU6QfaAZ5q-ybD6Izp5sfr0 300 1CGl9pdVWqGssSS3ausbw88MoBWvS65zl
```

---

## 📁 Finding Your Google Drive Folder ID

1. **Open the folder in Google Drive**
   - Navigate to the folder you want to monitor
   - Example: https://drive.google.com/drive/folders/1CGl9pdVWqGssSS3ausbw88MoBWvS65zl

2. **Copy the Folder ID from the URL:**
   ```
   https://drive.google.com/drive/folders/FOLDER_ID
                                         ^^^^^^^^^^^
   ```

3. **Use it in the command:**
   ```bash
   ./start_enhanced_watcher.sh SHEET_ID 300 FOLDER_ID
   ```

---

## 🎯 Advanced Usage

### **Monitor Multiple Google Drive Folders:**
```bash
python3 enhanced_auto_watcher.py SPREADSHEET_ID \
  --drive-folders FOLDER_ID_1 FOLDER_ID_2 FOLDER_ID_3
```

### **Run Once (Test Mode):**
```bash
python3 enhanced_auto_watcher.py SPREADSHEET_ID \
  --drive-folders FOLDER_ID --once
```

### **Custom Check Interval:**
```bash
# Check every 60 seconds
./start_enhanced_watcher.sh SHEET_ID 60 FOLDER_ID

# Check every 10 minutes
./start_enhanced_watcher.sh SHEET_ID 600 FOLDER_ID
```

### **Monitor Local + Multiple Drive Folders:**
```bash
python3 enhanced_auto_watcher.py SHEET_ID \
  --interval 300 \
  --drive-folders PERSONAL_FOLDER SHARED_FOLDER TEAM_FOLDER
```

---

## 🔄 How It Works

### **Monitoring Loop:**
```
Every N seconds:
  1. Check local folders (CP2000, etc.)
     → Process any new local files
  
  2. Check Google Drive folders
     → List all PDF files
     → Identify new files (not in processed_files_tracking.json)
     → Download new files to TEMP_DRIVE_DOWNLOADS/
     → Process each file
     → Add to Google Sheet
     → Mark as processed
     → Clean up temp file
  
  3. Sleep and repeat
```

### **File Processing Flow:**
```
Google Drive PDF
  ↓
Download to TEMP_DRIVE_DOWNLOADS/
  ↓
Extract Data:
  - Taxpayer Name
  - SSN Last 4
  - Tax Year
  - Notice Date
  - Due Date
  - Letter Type
  ↓
Match Against Logics CRM
  ↓
Append to Google Sheet:
  - "Matched Cases" (if Case ID found)
  - "Unmatched Cases" (if no match)
  ↓
Add Processing Timestamp
  ↓
Mark Drive File ID as Processed
  ↓
Delete Temp File
  ↓
Log Everything
```

---

## 📊 State Tracking

The watcher maintains **two separate tracking lists** in `processed_files_tracking.json`:

### **Structure:**
```json
{
  "processed_files": {
    "local_file1.pdf": 1730678901.234,
    "local_file2.pdf": 1730679012.345
  },
  "google_drive_files": {
    "1abc...xyz": {
      "name": "IRS_CORR_CP2000_2024.pdf",
      "processed_time": "2025-11-03T21:52:27"
    },
    "2def...uvw": {
      "name": "test.pdf",
      "processed_time": "2025-11-03T21:52:28"
    }
  },
  "last_check": "2025-11-03T21:52:30.123456"
}
```

### **Key Features:**
- ✅ **Local files tracked by filename + modification time**
  - If file is modified, it will be reprocessed
- ✅ **Drive files tracked by unique Google Drive File ID**
  - Ensures no duplicates even with same filename
- ✅ **Persistent across restarts**
  - Watcher remembers what it's already processed

---

## 🔒 Security & Permissions

### **Required OAuth Scopes:**
```python
scopes = [
    'https://www.googleapis.com/auth/spreadsheets',       # Read/Write Sheets
    'https://www.googleapis.com/auth/drive.file',         # Access Drive files
]
```

### **Authentication:**
- Uses your existing `token.json` from Google OAuth setup
- No service account needed
- Files are accessed using **your** Google account permissions

### **Privacy:**
- ✅ Only accesses specified folder IDs
- ✅ Only reads PDF files
- ✅ Downloads are temporary and cleaned up
- ✅ No files uploaded back to Drive

---

## 📂 Folder Structure

```
CP2000_Pipeline/
├── enhanced_auto_watcher.py      # Main script with Drive support
├── start_enhanced_watcher.sh     # Startup script with Drive support
├── token.json                    # OAuth credentials (includes Drive)
├── processed_files_tracking.json # Tracks local + Drive files
├── enhanced_watcher.log          # Activity log
├── TEMP_DRIVE_DOWNLOADS/         # Temp folder for Drive downloads
│   └── (files auto-deleted after processing)
└── CP2000/                       # Local files still monitored
```

---

## 🧪 Testing

### **Test 1: Upload a File to Drive**
```bash
# 1. Upload a CP2000 PDF to your monitored Drive folder
# 2. Check the log:
tail -f enhanced_watcher.log

# You should see:
# [timestamp] 🆕 New Drive file: yourfile.pdf
# [timestamp] 📥 Downloaded: yourfile.pdf
# [timestamp] ✅ Added to 'Matched Cases' sheet
# [timestamp] 🗑️  Cleaned up: yourfile.pdf
```

### **Test 2: One-Time Run**
```bash
python3 enhanced_auto_watcher.py SHEET_ID \
  --drive-folders FOLDER_ID --once

# This will:
# - Check once
# - Process any new files
# - Exit (useful for testing)
```

### **Test 3: Verify State Tracking**
```bash
# Check processed Drive files
cat processed_files_tracking.json | jq '.google_drive_files'

# You should see file IDs and timestamps
```

---

## 🎨 Log Output

### **Successful Drive File Processing:**
```
[2025-11-03 21:52:14] ☁️  Found 3 new Drive file(s) to process
[2025-11-03 21:52:14]    🆕 New Drive file: IRS_CORR_CP2000_2024.pdf
[2025-11-03 21:52:16]    📥 Downloaded: IRS_CORR_CP2000_2024.pdf
[2025-11-03 21:52:18]    📄 Processing: IRS_CORR_CP2000_2024.pdf
[2025-11-03 21:52:20]    ✅ Matched to Case ID: 275743
[2025-11-03 21:52:21]    ✅ Added to 'Matched Cases' sheet at row A123:N123
[2025-11-03 21:52:21]    🗑️  Cleaned up: IRS_CORR_CP2000_2024.pdf
[2025-11-03 21:52:21] 
📊 Drive files processing complete:
[2025-11-03 21:52:21]    Total processed: 3/3
[2025-11-03 21:52:21]    Matched: 2
[2025-11-03 21:52:21]    Unmatched: 1
```

### **No New Drive Files:**
```
[2025-11-03 22:00:00] ✅ No new local files found
[2025-11-03 22:00:01] ✅ No new Drive files found
[2025-11-03 22:00:01] 💤 Next check in 300 seconds...
```

---

## ❓ FAQ

### **Q: Can I monitor multiple Drive folders?**
Yes! Use the `--drive-folders` argument with multiple IDs:
```bash
python3 enhanced_auto_watcher.py SHEET_ID \
  --drive-folders FOLDER1 FOLDER2 FOLDER3
```

### **Q: What happens if I upload the same file twice?**
The file will only be processed once. The watcher tracks Drive file IDs, so even if you delete and re-upload, it won't reprocess unless the file ID changes.

### **Q: Can I use shared Drive folders?**
Yes! As long as:
1. Your Google account has access to the folder
2. You use the correct folder ID

### **Q: What about files in subfolders?**
Currently, only files **directly in the specified folder** are monitored. Subfolders are not scanned.

### **Q: How do I stop monitoring a Drive folder?**
Stop the watcher and restart without the `--drive-folders` argument:
```bash
# Stop: Ctrl+C or kill the process
# Restart without Drive:
./start_enhanced_watcher.sh SHEET_ID
```

### **Q: Where are temporary downloads stored?**
In `TEMP_DRIVE_DOWNLOADS/` folder. Files are automatically deleted after processing.

### **Q: Can I monitor Drive folders without local folders?**
The watcher always monitors local folders. If you don't want local monitoring, you can remove folders from the `watch_folders` list in the code.

### **Q: What if the Drive download fails?**
The error is logged, and the file is NOT marked as processed, so it will be retried on the next check.

---

## 🛠️ Troubleshooting

### **Error: "Failed to connect to Google Drive"**
**Solution:**
1. Check that `token.json` exists and is valid
2. Re-authenticate if needed:
   ```bash
   python3 test_google_oauth.py
   ```
3. Ensure your OAuth credentials include Drive API access

### **Error: "Error checking Google Drive folder [ID]"**
**Solutions:**
- Verify the folder ID is correct
- Check that your Google account has access to the folder
- Ensure the folder hasn't been deleted or unshared

### **Files not being detected:**
**Check:**
1. Are files directly in the folder (not subfolders)?
2. Are files PDF format?
3. Check `processed_files_tracking.json` - file might already be tracked
4. Check logs for errors: `tail -50 enhanced_watcher.log`

### **"BrokenPipeError" in logs:**
This is usually harmless. It happens when the shell closes but the process tries to write to stdout. The log file still captures everything.

---

## 📈 Performance

### **Recommended Settings:**
```bash
# Light usage (1-10 files/day): Check every 5 minutes
./start_enhanced_watcher.sh SHEET_ID 300 FOLDER_ID

# Heavy usage (50+ files/day): Check every 1 minute
./start_enhanced_watcher.sh SHEET_ID 60 FOLDER_ID

# Moderate (10-50 files/day): Check every 2 minutes
./start_enhanced_watcher.sh SHEET_ID 120 FOLDER_ID
```

### **Resource Usage:**
- **CPU:** Minimal when idle, moderate during processing
- **Memory:** ~50-100MB typical
- **Network:** Only when downloading files
- **Disk:** Temporary downloads cleaned up automatically

---

## 🎯 Complete Example Workflow

```bash
# 1. Get your Google Sheet ID
# Open sheet → Copy from URL
SHEET_ID="1_z6KrPLBRKlgJYQjmKKmvU6QfaAZ5q-ybD6Izp5sfr0"

# 2. Get your Google Drive folder ID
# Open folder → Copy from URL
FOLDER_ID="1CGl9pdVWqGssSS3ausbw88MoBWvS65zl"

# 3. Start the watcher
cd "/Users/hemalathayalamanchi/Desktop/logicscase integration/CP2000_Pipeline"
./start_enhanced_watcher.sh $SHEET_ID 300 $FOLDER_ID

# 4. Upload a CP2000 PDF to that Drive folder

# 5. Within 5 minutes, check your Google Sheet
# → New row will appear with all extracted data + timestamp

# 6. Approve cases directly in the sheet
# → Change "Status" column to "APPROVE"
# → Triggers Logics API (task creation + document upload)

# 7. Check logs anytime
tail -f enhanced_watcher.log
```

---

## 🔗 Related Documentation

- **[ENHANCED_AUTO_WATCHER_GUIDE.md](./ENHANCED_AUTO_WATCHER_GUIDE.md)** - Complete watcher documentation
- **[QUICK_REFERENCE.txt](./QUICK_REFERENCE.txt)** - Quick command reference
- **[SETUP_GOOGLE_SHEET_AUTOMATION.md](./SETUP_GOOGLE_SHEET_AUTOMATION.md)** - Sheet approval automation

---

## 📞 Support

If you encounter issues:

1. **Check logs:**
   ```bash
   tail -100 enhanced_watcher.log
   ```

2. **Check state file:**
   ```bash
   cat processed_files_tracking.json | jq
   ```

3. **Test Drive connection:**
   ```bash
   python3 -c "
   from google.oauth2.credentials import Credentials
   from googleapiclient.discovery import build
   creds = Credentials.from_authorized_user_file('token.json')
   service = build('drive', 'v3', credentials=creds)
   results = service.files().list(pageSize=10, fields='files(id, name)').execute()
   print('✅ Drive connection successful!')
   print('Files:', results.get('files', []))
   "
   ```

4. **Re-authenticate if needed:**
   ```bash
   python3 test_google_oauth.py
   ```

---

## ✅ Summary

✅ **Automatic Google Drive monitoring** - Upload and forget  
✅ **Secure OAuth authentication** - Uses your Google account  
✅ **Tracks file IDs** - Prevents duplicate processing  
✅ **Cleans up temp files** - No disk bloat  
✅ **Detailed logging** - Always know what's happening  
✅ **Multi-folder support** - Monitor personal + shared folders  
✅ **Works alongside local monitoring** - Best of both worlds  

**Your CP2000 workflow is now fully automated from Drive to Sheet to Logics!** 🚀

---

*Last Updated: November 3, 2025*

