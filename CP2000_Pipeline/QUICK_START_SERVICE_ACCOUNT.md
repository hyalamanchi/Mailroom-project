# 🚀 Quick Start - Service Account

**For:** Hemalatha Yalamanchi  
**Date:** October 31, 2025

---

## ⚡ 3-Step Setup (5 minutes)

### Step 1: Share Google Drive Folders

Share with: `sheets-automation-sa@transcript-parsing-465614.iam.gserviceaccount.com`

**Folders to share (as "Editor"):**
- CP2000 New Batch 2
- CP2000_MATCHED  
- CP2000_UNMATCHED

---

### Step 2: Test Authentication

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
print('✅ Service account works!')
"
```

Expected output: `✅ Service account works!`

---

### Step 3: Push to GitHub

```bash
# Pull remote changes
git pull origin main --allow-unrelated-histories

# Push your code
git push -u origin main
```

When prompted:
- **Username:** `hyalamanchi`
- **Password:** [Your GitHub token]

---

## 🎯 Run Your Pipeline

```bash
# Test with 2 files first
python3 daily_pipeline_orchestrator.py --test --limit=2

# Full production run
python3 daily_pipeline_orchestrator.py

# Upload to Logiqs
python3 upload_to_logiqs.py
```

---

## 📚 Full Documentation

- **Setup Guide:** [SERVICE_ACCOUNT_SETUP.md](SERVICE_ACCOUNT_SETUP.md)
- **Migration Details:** [MIGRATION_TO_SERVICE_ACCOUNT.md](MIGRATION_TO_SERVICE_ACCOUNT.md)
- **Daily Workflow:** [DAILY_WORKFLOW_GUIDE.md](DAILY_WORKFLOW_GUIDE.md)

---

## ✅ Checklist

- [ ] Shared 3 Google Drive folders with service account
- [ ] Tested authentication (Step 2)
- [ ] Pulled remote changes from GitHub
- [ ] Pushed code to GitHub
- [ ] Ran test pipeline
- [ ] Ready for production! 🚀

---

**That's it!** You're ready to go. 🎉

