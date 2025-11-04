# 🚀 Quick Start Guide

## Setup (One-Time)

```bash
# 1. Install dependencies
pip3 install -r requirements.txt

# 2. Add Google credentials
# Place credentials.json in this directory

# 3. Verify setup
python3 test_logics_search.py
```

## Run Workflow

### Option A: Interactive Shell Script (Easiest)
```bash
./run_case_workflow.sh
```

### Option B: Direct Python Command
```bash
# Complete workflow with manual approval
python3 complete_case_workflow.py

# Follow prompts to select mode
```

## Approval Process

1. **Open Google Sheet** (URL shown after workflow runs)
2. **Review cases** in the "Matched Cases" sheet
3. **Change Status column** to "Approve" for cases to process
4. **Run automation**:
   ```bash
   python3 sheet_approval_automation.py <SHEET_ID> once
   ```

## What Gets Created

- ✅ **Matched Cases Sheet** - Cases found in Logics (with approval workflow)
- 📝 **Unmatched Cases Sheet** - Cases not found (needs manual review)
- 📁 **Google Drive Folders** - Organized folder structure
- 🤖 **Automation Ready** - Task creation & document upload

## Status Options

| Status | Action |
|--------|--------|
| **Approve** | Auto-creates task + uploads document |
| **Reject** | Marked as rejected (no action) |
| **Review** | Default status (no action) |

## Monitoring

### Single Check (Run Once)
```bash
python3 sheet_approval_automation.py <SHEET_ID> once
```

### Continuous Monitoring (Checks every 60 seconds)
```bash
python3 sheet_approval_automation.py <SHEET_ID> monitor
```
Press `Ctrl+C` to stop

## Getting Spreadsheet ID

From Google Sheets URL:
```
https://docs.google.com/spreadsheets/d/1abc123xyz456/edit
                                        ^^^^^^^^^^^^^^
                                        This is the ID
```

## Common Commands

```bash
# Match cases with Logics
python3 case_id_extractor.py

# Create Google Sheets
python3 case_management_sheet.py

# Test API connection
python3 test_logics_search.py

# Run complete workflow
python3 complete_case_workflow.py
```

## Workflow Summary

```
1. Extract CP2000 Data → LOGICS_DATA_*.json
2. Match with Logics   → CASE_MATCHES_*.json  
3. Create Sheets       → Google Drive folders + sheets
4. Approve Cases       → Change status to "Approve"
5. Run Automation      → Tasks & docs uploaded to Logics
```

## Support

- 📖 Full guide: `CASE_MANAGEMENT_WORKFLOW_GUIDE.md`
- 🧪 Test results: `PRE_RELEASE_TEST_SUMMARY.md`
- 📝 Check logs for detailed error messages

## Troubleshooting

| Issue | Solution |
|-------|----------|
| No credentials.json | Add Google service account credentials file |
| API errors | Check LOGICS_API_KEY in .env or environment |
| No cases matched | Verify LOGICS_DATA_*.json exists |
| Sheet not updating | Refresh browser, check credentials permissions |

---

**Need Help?** Check the full documentation in `CASE_MANAGEMENT_WORKFLOW_GUIDE.md`


