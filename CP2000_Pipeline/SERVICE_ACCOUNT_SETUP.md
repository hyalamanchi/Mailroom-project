# 🔐 Google Drive Service Account Setup Guide

**Author:** Hemalatha Yalamanchi  
**Last Updated:** October 31, 2025

---

## Overview

This project uses **Google Service Account authentication** for automated Google Drive access. This is better than OAuth for production because:

✅ **No browser authentication needed**  
✅ **Works in automation/cron jobs**  
✅ **No token expiration issues**  
✅ **Better for production workflows**  
✅ **Can be shared across team members**  

---

## Current Configuration

### Service Account Details
- **Email:** `sheets-automation-sa@transcript-parsing-465614.iam.gserviceaccount.com`
- **Project:** `transcript-parsing-465614`
- **Key File:** `service-account-key.json` (already configured)

### Required Permissions
The service account needs access to your Google Drive folders:
- **CP2000 New Batch 2** (input folder)
- **CP2000_MATCHED** (output for matched cases)
- **CP2000_UNMATCHED** (output for unmatched cases)

---

## 🚀 Quick Setup

### Step 1: Share Google Drive Folders

You need to share your Google Drive folders with the service account email.

**For EACH folder:**

1. Go to Google Drive: https://drive.google.com
2. Right-click on the folder → **Share**
3. Add this email: `sheets-automation-sa@transcript-parsing-465614.iam.gserviceaccount.com`
4. Set permission to **Editor**
5. Click **Send** (or **Share**)

**Folders to share:**
- `CP2000 New Batch 2` (input)
- `CP2000_MATCHED` (output)
- `CP2000_UNMATCHED` (output)

---

### Step 2: Verify Setup

Run this command to test authentication:

```bash
cd "/Users/hemalathayalamanchi/Desktop/logicscase integration/CP2000_Pipeline"
python3 -c "
from google.oauth2 import service_account
from googleapiclient.discovery import build

creds = service_account.Credentials.from_service_account_file(
    'service-account-key.json',
    scopes=['https://www.googleapis.com/auth/drive.readonly']
)
service = build('drive', 'v3', credentials=creds)
print('✅ Service account authentication successful!')
"
```

---

### Step 3: Run Your Pipeline

Now you can run any script without browser authentication:

```bash
# Extract data from PDFs
python production_extractor.py

# Run daily pipeline
python daily_pipeline_orchestrator.py

# Test single upload
python test_single_upload.py

# Bulk upload to Logiqs
python upload_to_logiqs.py
```

---

## 🔒 Security Best Practices

### ✅ What We've Done

1. **Service account key is in `.gitignore`** - Won't be pushed to GitHub
2. **Using read-only scope where possible** - Minimizes security risk
3. **Proper file permissions** - Key file is protected

### ⚠️ Important Security Notes

- **NEVER commit** `service-account-key.json` to GitHub
- **NEVER share** the service account key publicly
- **Always use** `.gitignore` to exclude sensitive files
- **Rotate keys** periodically (every 90 days recommended)

---

## 📋 Files Modified

All these files now use service account authentication:

1. ✅ `daily_pipeline_orchestrator.py`
2. ✅ `production_extractor.py`
3. ✅ `upload_to_logiqs.py`
4. ✅ `test_single_upload.py`
5. ✅ `download_and_rename.py`

---

## 🗑️ Old Files (No Longer Needed)

You can safely delete these files:

```bash
# Old OAuth files (no longer used)
rm token.pickle
rm credentials.json
```

The service account authentication replaces these entirely.

---

## 🆘 Troubleshooting

### Error: `service-account-key.json not found`

**Solution:** Make sure the file is in the project root:
```bash
ls -la service-account-key.json
```

### Error: `HttpError 403: Insufficient Permission`

**Solution:** Share the Google Drive folders with the service account email:
`sheets-automation-sa@transcript-parsing-465614.iam.gserviceaccount.com`

### Error: `HttpError 404: File not found`

**Solution:** 
1. Verify folder IDs in your scripts match your Google Drive
2. Check that folders are shared with the service account

---

## 🔄 Migrating from OAuth to Service Account

### What Changed?

**Before (OAuth):**
```python
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow

# Required browser authentication
flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
creds = flow.run_local_server(port=0)
```

**After (Service Account):**
```python
from google.oauth2 import service_account

# No browser needed!
creds = service_account.Credentials.from_service_account_file(
    'service-account-key.json',
    scopes=SCOPES
)
```

---

## 📞 Support

If you encounter any issues:

1. Check that folders are shared with service account
2. Verify `service-account-key.json` exists in project root
3. Ensure file is not corrupted (should be valid JSON)
4. Check `.gitignore` includes the key file

---

## ✨ Benefits Summary

| Feature | OAuth | Service Account |
|---------|-------|-----------------|
| Browser Required | ✅ Yes | ❌ No |
| Token Expiration | ✅ Yes | ❌ No |
| Automation Friendly | ❌ No | ✅ Yes |
| Team Sharing | ❌ Hard | ✅ Easy |
| Production Ready | ⚠️ Limited | ✅ Yes |

---

**You're all set!** 🚀 Your pipeline now uses enterprise-grade service account authentication.

