# 🔄 ENHANCED AUTO WATCHER GUIDE

## 🎯 Overview

The Enhanced Auto Watcher automatically monitors your CP2000 folders for new PDF files and **appends them to your existing Google Sheet** with timestamps. No more creating new sheets for each batch!

---

## ✨ Key Features

### ✅ **What It Does:**
1. **Monitors Local Folders** - Watches `CP2000/` and `CP2000 NEW BATCH 2/` folders
2. **Detects New Files** - Automatically finds new PDF files added to folders
3. **Processes & Matches** - Extracts data and matches against Logics CRM
4. **Appends to Sheet** - Adds new cases to your EXISTING Google Sheet
5. **Adds Timestamps** - Each case gets a "Processed_Timestamp" column
6. **Tracks Processed Files** - Prevents reprocessing the same files

### ❌ **What Changed from Old Watcher:**
- **OLD**: Created a NEW Google Sheet every time ❌
- **NEW**: Appends to EXISTING Google Sheet ✅
- **OLD**: Only monitored Google Drive ❌
- **NEW**: Monitors local CP2000 folders ✅
- **OLD**: No timestamps ❌
- **NEW**: Adds timestamp for each case ✅

---

## 📋 Prerequisites

1. **Initial Google Sheet** - Create once using:
   ```bash
   python3 create_review_workbook.py
   ```
   This creates a sheet with 2 tabs:
   - Matched Cases
   - Unmatched Cases
   
2. **Copy the Spreadsheet ID** from the URL:
   ```
   https://docs.google.com/spreadsheets/d/1abc123xyz456/edit
                                            ^^^^^^^^^^^^^^^^
                                            This is your ID
   ```

3. **Google Credentials** - Make sure `token.json` exists (created during setup)

---

## 🚀 How to Use

### **Option 1: Easy Start (Recommended)**

```bash
./start_enhanced_watcher.sh YOUR_SPREADSHEET_ID
```

Example:
```bash
./start_enhanced_watcher.sh 1abc123xyz456
```

### **Option 2: Custom Interval**

Check every 2 minutes (120 seconds):
```bash
./start_enhanced_watcher.sh YOUR_SPREADSHEET_ID 120
```

Check every 10 minutes (600 seconds):
```bash
./start_enhanced_watcher.sh YOUR_SPREADSHEET_ID 600
```

### **Option 3: One-Time Check**

Run once and exit (doesn't keep monitoring):
```bash
python3 enhanced_auto_watcher.py YOUR_SPREADSHEET_ID --once
```

---

## 📊 What Happens Step-by-Step

```
┌─────────────────────────────────────────────────────────────┐
│ STEP 1: YOU ADD NEW PDF                                      │
│  You drop "CP2000_New_Case.pdf" into CP2000/ folder         │
└───────────────────┬─────────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────────────────┐
│ STEP 2: WATCHER DETECTS (within 5 minutes)                  │
│  🔍 Checking folders...                                      │
│  🆕 New file: CP2000_New_Case.pdf                          │
└───────────────────┬─────────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────────────────┐
│ STEP 3: EXTRACTION                                           │
│  📄 Extracting data from PDF...                             │
│  ✅ Extracted: Name, SSN, Tax Year, Dates, etc.            │
└───────────────────┬─────────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────────────────┐
│ STEP 4: LOGICS MATCHING                                      │
│  🔍 Searching Logics for match...                           │
│  ✅ Matched to Case ID: 12345  OR  ⚠️ No match found      │
└───────────────────┬─────────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────────────────┐
│ STEP 5: APPEND TO SHEET                                      │
│  📊 Adding to Google Sheet...                               │
│  ✅ Row added to "Matched Cases" (or "Unmatched Cases")    │
│  🕐 Timestamp: 2024-11-04 14:30:15                          │
└─────────────────────────────────────────────────────────────┘
```

---

## 📁 Folder Structure

The watcher monitors these folders:

```
CP2000_Pipeline/
├── CP2000/                         ← Monitored ✓
│   ├── existing_file_1.pdf
│   └── NEW_FILE.pdf               ← Will be detected!
│
├── CP2000 NEW BATCH 2/            ← Monitored ✓
│   └── another_new_file.pdf      ← Will be detected!
│
└── ../CP2000_Production/
    └── CP2000 NEW BATCH 2/        ← Monitored ✓
```

---

## 📝 Google Sheet Structure

### **Columns in the Sheet:**

| Column | Name | Description |
|--------|------|-------------|
| A | Case_ID | Logics Case ID (if matched) |
| B | Original_Filename | Name of the PDF file |
| C | Proposed_Filename | Suggested new filename |
| D | Taxpayer_Name | Taxpayer full name |
| E | SSN_Last_4 | Last 4 digits of SSN |
| F | Letter_Type | CP2000, CP2501, etc. |
| G | Tax_Year | Tax year of the notice |
| H | Notice_Date | Date on the notice |
| I | Due_Date | Response due date |
| J | Source_Folder | Where file came from |
| K | Match_Confidence | High/Medium/Low/Unmatched |
| L | Status | APPROVE/UNDER_REVIEW/REJECT |
| M | Notes | Manual notes/processing status |
| N | Processed_Timestamp | When case was added ⭐ NEW! |

### **Example Row:**

```
12345 | CP2000_123.pdf | IRS_CORR_CP2000_2023... | John Doe | 5678 | 
CP2000 | 2023 | 2024-09-15 | 2024-10-15 | TEMP_PROCESSING | High | 
[dropdown] | [notes] | 2024-11-04 14:30:15
```

---

## 🔄 Workflow

### **Day 1: Initial Setup**

1. Create initial sheet:
   ```bash
   python3 create_review_workbook.py
   ```
   Output: `https://docs.google.com/spreadsheets/d/1abc123xyz456/edit`

2. Start watcher:
   ```bash
   ./start_enhanced_watcher.sh 1abc123xyz456
   ```

3. Leave it running in the background

### **Day 2+: Adding New Files**

1. Drop new PDFs into `CP2000/` folder
2. Wait ~5 minutes (or your configured interval)
3. Check Google Sheet - new rows appear with timestamps!
4. Review and approve cases as needed

### **Approval Process:**

1. Open Google Sheet
2. Check new rows (look at timestamps)
3. Click Status dropdown → Select "APPROVE"
4. Run approval automation (separate script):
   ```bash
   python3 run_approval_automation.py 1abc123xyz456 once
   ```

---

## 📊 Logs and Tracking

### **Log File:**
- Location: `enhanced_watcher.log`
- Contains: All activity, errors, processing details
- Example:
  ```
  [2024-11-04 14:30:00] 🔍 Checking folders...
  [2024-11-04 14:30:01] 🆕 New file: CP2000_New.pdf
  [2024-11-04 14:30:05] ✅ Matched to Case ID: 12345
  [2024-11-04 14:30:06] ✅ Added to 'Matched Cases' sheet
  ```

### **State File:**
- Location: `processed_files_tracking.json`
- Purpose: Tracks which files have been processed
- Format:
  ```json
  {
    "processed_files": {
      "CP2000_123.pdf": 1699123456.789,
      "CP2000_456.pdf": 1699123789.123
    },
    "last_check": "2024-11-04T14:30:00"
  }
  ```

### **To Reprocess a File:**

1. Stop the watcher (Ctrl+C)
2. Edit `processed_files_tracking.json`
3. Remove the file from `processed_files`
4. Restart watcher

---

## ⚙️ Configuration

### **Change Check Interval:**

Default is 300 seconds (5 minutes). To change:

```bash
# Check every 2 minutes
./start_enhanced_watcher.sh SPREADSHEET_ID 120

# Check every 30 seconds (fast)
./start_enhanced_watcher.sh SPREADSHEET_ID 30

# Check every 10 minutes (slow)
./start_enhanced_watcher.sh SPREADSHEET_ID 600
```

### **Add More Folders to Monitor:**

Edit `enhanced_auto_watcher.py` line 42:

```python
self.watch_folders = [
    'CP2000',
    'CP2000 NEW BATCH 2',
    '../CP2000_Production/CP2000 NEW BATCH 2',
    'YOUR_NEW_FOLDER_HERE'  # Add here
]
```

---

## 🐛 Troubleshooting

### **❌ "No new files found" but I added files**

**Solutions:**
1. Check file extension - must be `.pdf` (lowercase)
2. Check folder location - file must be in monitored folders
3. Check state file - file might be already marked as processed
4. Wait for next check cycle (default 5 minutes)

### **❌ "Failed to connect to Google Sheets"**

**Solutions:**
1. Check `token.json` exists
2. Re-run `create_review_workbook.py` to refresh credentials
3. Check internet connection

### **❌ "Failed to append to sheet"**

**Solutions:**
1. Verify spreadsheet ID is correct
2. Check you have edit access to the sheet
3. Ensure sheet tabs are named exactly: "Matched Cases" and "Unmatched Cases"

### **❌ Files processed but not appearing in sheet**

**Solutions:**
1. Check the log file: `enhanced_watcher.log`
2. Verify extraction succeeded
3. Check if row was added to "Unmatched Cases" tab instead
4. Refresh your Google Sheet

---

## 🎯 Best Practices

### **1. Keep Watcher Running**

Run in background or as a service:
```bash
# Run in background
nohup ./start_enhanced_watcher.sh SPREADSHEET_ID > watcher_output.log 2>&1 &

# Check if running
ps aux | grep enhanced_auto_watcher
```

### **2. Regular Reviews**

- Check Google Sheet daily
- Review new rows (sort by Processed_Timestamp)
- Approve valid cases promptly

### **3. Backup State File**

Periodically backup `processed_files_tracking.json` to avoid reprocessing

### **4. Monitor Logs**

Check `enhanced_watcher.log` for errors:
```bash
tail -f enhanced_watcher.log
```

### **5. Clean Up Old Files**

After processing and approving, move files to archive:
```bash
mkdir PROCESSED_ARCHIVE
mv CP2000/*.pdf PROCESSED_ARCHIVE/
```

---

## 📈 Performance

### **Processing Speed:**
- Single file: ~5-10 seconds
- Batch of 10 files: ~60 seconds
- Batch of 100 files: ~10 minutes

### **Resource Usage:**
- CPU: Low (only during processing)
- Memory: ~100-200 MB
- Network: Minimal (only Google Sheets API calls)

---

## 🆚 Comparison: Old vs New

| Feature | Old Watcher | Enhanced Watcher |
|---------|-------------|------------------|
| Output | New sheet each time ❌ | Append to existing ✅ |
| Monitor | Google Drive only | Local folders ✅ |
| Timestamps | No ❌ | Yes ✅ |
| File Tracking | Limited | Full state tracking ✅ |
| Duplicate Prevention | No | Yes ✅ |
| Logs | Basic | Comprehensive ✅ |

---

## 🎉 Summary

**What you get:**
- ✅ Automatic file detection
- ✅ Automatic data extraction
- ✅ Automatic Logics matching
- ✅ Automatic sheet updates
- ✅ Timestamp tracking
- ✅ No duplicate processing

**What you do:**
- Drop PDFs in CP2000 folders
- Review new rows in Google Sheet
- Approve valid cases

**That's it!** The system handles everything else automatically.

---

## 📞 Need Help?

Check these files:
- `enhanced_watcher.log` - Activity log
- `processed_files_tracking.json` - State tracking
- Google Sheet - Processing results

Common commands:
```bash
# Start watcher
./start_enhanced_watcher.sh SPREADSHEET_ID

# Check logs
tail -f enhanced_watcher.log

# One-time run
python3 enhanced_auto_watcher.py SPREADSHEET_ID --once

# View processed files
cat processed_files_tracking.json
```

