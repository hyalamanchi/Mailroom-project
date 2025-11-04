# 🚀 Setup Google Sheet Automation

## Overview

This guide shows you how to set up automatic processing when you approve cases in Google Sheets.

## 📋 Two Methods

### Method 1: Google Apps Script + Manual Trigger (Recommended)
### Method 2: Continuous Python Monitoring

---

## 🎯 Method 1: Google Apps Script (Easy & Interactive)

### Step 1: Add Apps Script to Your Sheet

1. **Open your Matched Cases sheet**:
   - https://docs.google.com/spreadsheets/d/1OzWx6vQ7OB5cBnZmn6GfJqliESd_nqX29g6sT9wTpfc/edit

2. **Go to Extensions > Apps Script**

3. **Delete any existing code**

4. **Copy and paste** the entire contents of `GOOGLE_APPS_SCRIPT.js`

5. **Click Save** (disk icon) and name it "CP2000 Automation"

6. **Click Run** and authorize the script when prompted

7. **Refresh your Google Sheet**

### Step 2: Use the Custom Menu

You'll now see a new menu: **🤖 CP2000 Automation**

#### Quick Actions:
- **✅ Mark Selected as Approve**: Select rows and mark them as approved
- **❌ Mark Selected as Reject**: Reject selected cases
- **📋 Mark Selected as Review**: Mark for review
- **📊 Show Approval Summary**: See counts of each status

#### Processing:
- **✅ Process All Approved Cases**: Queue approved cases for processing
- **🔄 Enable Auto-Processing**: Auto-check every 5 minutes

### Step 3: Approve and Process Cases

**Option A: Manual Selection (Easiest)**
```
1. Select the rows you want to approve (click row numbers)
2. Go to: 🤖 CP2000 Automation > ✅ Mark Selected as Approve
3. Rows will turn green and be marked "Approve"
4. Go to: 🤖 CP2000 Automation > ✅ Process All Approved Cases
5. Confirm when prompted
6. Cases will be queued for processing
```

**Option B: Edit Directly**
```
1. Click on Status cell
2. Select "Approve" from dropdown
3. Cell automatically turns green
4. Go to: 🤖 CP2000 Automation > ✅ Process All Approved Cases
```

### Step 4: Run Python Automation

After using "Process All Approved Cases" in the sheet menu:

```bash
cd "/Users/hemalathayalamanchi/Desktop/logicscase integration/CP2000_Pipeline"

# Process once
python3 sheet_approval_automation.py 1OzWx6vQ7OB5cBnZmn6GfJqliESd_nqX29g6sT9wTpfc once
```

The automation will:
- ✅ Find all "Queued for Processing" cases
- ✅ Create tasks in Logics
- ✅ Upload documents
- ✅ Update status to "Completed"

---

## 🔄 Method 2: Continuous Python Monitoring (Full Automation)

### Step 1: Start Monitoring Script

```bash
cd "/Users/hemalathayalamanchi/Desktop/logicscase integration/CP2000_Pipeline"

# Start continuous monitoring (checks every 60 seconds)
python3 sheet_approval_automation.py 1OzWx6vQ7OB5cBnZmn6GfJqliESd_nqX29g6sT9wTpfc monitor
```

### Step 2: Approve Cases in Sheet

1. Open your sheet
2. Change Status to "Approve" for any cases
3. The monitoring script will automatically detect and process them
4. Watch the terminal for real-time progress
5. Check the sheet - status will update to "Completed"

### Step 3: Keep It Running

To keep monitoring in the background:

```bash
# Run in background
nohup python3 sheet_approval_automation.py 1OzWx6vQ7OB5cBnZmn6GfJqliESd_nqX29g6sT9wTpfc monitor > automation.log 2>&1 &

# Check if it's running
ps aux | grep sheet_approval_automation

# View logs
tail -f automation.log

# Stop it
pkill -f sheet_approval_automation
```

---

## 🎨 Visual Indicators

### Status Colors (Automatic)

| Status | Color | Meaning |
|--------|-------|---------|
| **Approve** | 🟢 Green | Ready to process |
| **Reject** | 🔴 Red | Will not process |
| **Review** | 🟡 Yellow | Needs review |

### Processing Status

| Status | Meaning |
|--------|---------|
| **Pending** | Not yet processed |
| **Queued for Processing** | Marked by Apps Script |
| **Processing...** | Currently being processed |
| **Completed** | Task created & doc uploaded |
| **Task Created** | Task created but upload failed |
| **Error: ...** | Error occurred |

### Upload Status

| Status | Meaning |
|--------|---------|
| **Not Uploaded** | Waiting |
| **Uploaded Successfully** | Document uploaded to case |
| **Upload Failed** | Document upload failed |

---

## 📊 Workflow Comparison

### Manual Workflow (Without Automation)
```
1. Open sheet
2. Review cases
3. Mark as "Approve" manually
4. Open terminal
5. Run python command
6. Wait for completion
7. Check sheet for results
```

### Automated Workflow (With Apps Script)
```
1. Open sheet
2. Select rows
3. Click: 🤖 CP2000 Automation > ✅ Mark Selected as Approve
4. Click: 🤖 CP2000 Automation > ✅ Process All Approved Cases
5. Run python command once
6. Done! Check sheet for updates
```

### Fully Automated Workflow (With Monitoring)
```
1. Start monitoring script once (keeps running)
2. Open sheet anytime
3. Change status to "Approve"
4. Done! Script processes automatically
5. Check sheet for updates
```

---

## 🔧 Advanced: Enable Auto-Processing Every 5 Minutes

1. **In your sheet**, go to: **🤖 CP2000 Automation > 🔄 Enable Auto-Processing**

2. **Confirm** when prompted

3. **This creates a time-based trigger** that checks every 5 minutes

4. **Keep the Python monitoring script running** to process queued cases

5. **Result**: Fully automated end-to-end processing!

---

## ⚙️ Configuration Options

### Change Check Interval

Edit the monitoring script interval:

```python
# In sheet_approval_automation.py
automation.monitor_sheet(spreadsheet_id, check_interval=30)  # Check every 30 seconds
```

### Add Email Notifications

You can enhance the Apps Script to send emails:

```javascript
function sendEmailNotification(count) {
  MailApp.sendEmail({
    to: 'your-email@example.com',
    subject: '✅ CP2000 Cases Processed',
    body: `${count} case(s) have been processed successfully!`
  });
}
```

---

## 🎯 Recommended Setup

For the best experience:

1. ✅ **Add the Apps Script** to your sheet (one-time setup)
2. ✅ **Use the menu buttons** to approve cases in bulk
3. ✅ **Run Python script** manually when you have approved cases
4. ✅ **Optional**: Enable auto-processing for continuous monitoring

This gives you:
- ✅ Easy bulk approval with buttons
- ✅ Visual feedback (green/red colors)
- ✅ Status tracking in real-time
- ✅ Control over when processing happens
- ✅ Clear audit trail

---

## 🆘 Troubleshooting

### Apps Script Not Showing Menu
- Refresh the sheet
- Check if script is authorized (Extensions > Apps Script > Run)
- Clear browser cache

### Cases Not Processing
- Check if Python script is running
- Verify spreadsheet ID is correct
- Check terminal logs for errors
- Ensure cases are marked "Approve" not "approve"

### Status Not Updating
- Check network connection
- Verify credentials are valid
- Refresh the sheet
- Check Python script logs

---

## 📞 Quick Reference

**Your Sheet ID**: `1OzWx6vQ7OB5cBnZmn6GfJqliESd_nqX29g6sT9wTpfc`

**Process Once**:
```bash
python3 sheet_approval_automation.py 1OzWx6vQ7OB5cBnZmn6GfJqliESd_nqX29g6sT9wTpfc once
```

**Monitor Continuously**:
```bash
python3 sheet_approval_automation.py 1OzWx6vQ7OB5cBnZmn6GfJqliESd_nqX29g6sT9wTpfc monitor
```

**Sheet URL**: https://docs.google.com/spreadsheets/d/1OzWx6vQ7OB5cBnZmn6GfJqliESd_nqX29g6sT9wTpfc/edit

---

**Last Updated**: November 4, 2025  
**Version**: 2.0


