# CP2000 Case Management Workflow Guide

## 🎯 Overview

This automated workflow system:
1. ✅ Matches extracted CP2000 cases with Logics system
2. 📁 Creates organized folder structure in Google Drive
3. 📊 Generates Google Sheets for matched and unmatched cases
4. 🤖 Automates task creation and document upload when cases are approved

## 📋 Features

### Matched Cases Sheet
- **Status Column**: Dropdown with `Approve`, `Reject`, `Review` options
- **Automatic Processing**: When status is set to "Approve":
  - ✅ Creates task in Logics using Task Creation API
  - 📤 Uploads CP2000 document to case using Document Upload API
  - 📝 Updates processing status in real-time
- **Complete Case Information**: Case ID, taxpayer details, urgency levels, contact info
- **Color-Coded**: Green for approved, red for rejected, yellow for review

### Unmatched Cases Sheet
- Lists cases not found in Logics system
- Manual Case ID entry column for linking
- Action required indicators
- Notes field for tracking

## 🚀 Quick Start

### Prerequisites

1. **Google Credentials**
   ```bash
   # Ensure credentials.json is in the CP2000_Pipeline directory
   ls credentials.json
   ```

2. **Python Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Environment Variables** (optional)
   ```bash
   export LOGICS_API_KEY="your_api_key_here"
   ```

### Running the Workflow

#### Option 1: Complete Automated Workflow (Recommended)

```bash
python3 complete_case_workflow.py
```

This will:
1. Match cases with Logics
2. Create folder structure
3. Generate Google Sheets
4. Ask if you want continuous monitoring

#### Option 2: Step-by-Step Approach

**Step 1: Match Cases**
```bash
python3 case_id_extractor.py
```

**Step 2: Create Google Sheets**
```bash
python3 case_management_sheet.py
```

**Step 3: Process Approvals**
```bash
# Single check (process approved cases once)
python3 sheet_approval_automation.py <SPREADSHEET_ID> once

# Continuous monitoring (checks every 60 seconds)
python3 sheet_approval_automation.py <SPREADSHEET_ID> monitor
```

## 📊 Google Sheet Structure

### Matched Cases Sheet Columns

| Column | Name | Description |
|--------|------|-------------|
| A | Status | **Approve/Reject/Review** (dropdown) |
| B | Case ID | Logics case ID |
| C | Taxpayer Name | Full name from Logics |
| D | SSN Last 4 | Last 4 digits |
| E | Full SSN | Complete SSN |
| F | Letter Type | CP2000 |
| G | Tax Year | Year of the notice |
| H | Notice Date | Date of CP2000 notice |
| I | Response Due Date | Deadline to respond |
| J | Days Remaining | Days until deadline |
| K | Urgency Level | CRITICAL/HIGH/MEDIUM |
| L | Notice Ref Number | IRS reference number |
| M | File Name | Original PDF filename |
| N | Match Confidence | 0.0 to 1.0 |
| O | Match Type | exact/fuzzy |
| P | Assigned To | Case officer |
| Q | Email | Contact email |
| R | Phone | Contact phone |
| S | Processing Status | Pending/Processing/Completed |
| T | Upload Status | Not Uploaded/Uploaded |

## 🤖 Automation Workflow

### When You Approve a Case:

1. **Set Status to "Approve"** in Column A
2. **Automation detects** the approval (checks every 60 seconds in monitor mode)
3. **Creates Task** in Logics:
   ```json
   {
     "caseId": 12345,
     "taskType": "CP2000_REVIEW",
     "priority": "HIGH",
     "dueDate": "2024-10-15",
     "title": "CP2000 Notice Review - Tax Year 2022",
     "details": {
       "taxYear": "2022",
       "noticeDate": "2024-09-15",
       "referenceNumber": "12345-6789",
       "noticeType": "CP2000",
       "status": "NEW"
     }
   }
   ```

4. **Uploads Document** to Logics:
   - Finds the CP2000 PDF file
   - Uploads to the matched case ID
   - Sets document type as "CP2000"
   - Adds tax year metadata

5. **Updates Sheet**:
   - Processing Status → "Completed"
   - Upload Status → "Uploaded Successfully"

## 📁 Folder Structure Created

```
Google Drive:
└── CP2000_Batch_YYYYMMDD/
    ├── MATCHED_CASES/
    │   └── CP2000 Matched Cases - YYYYMMDD_HHMMSS.xlsx
    └── UNMATCHED_CASES/
        └── CP2000 Unmatched Cases - YYYYMMDD_HHMMSS.xlsx
```

## 🔧 API Endpoints Used

### 1. Task Creation Endpoint
```
POST https://tiparser-dev.onrender.com/case-data/api/tasks/create

Headers:
  X-API-Key: sk_BIWGmwZeahwOyI9ytZNMnZmM_mY1SOcpl4OXlmFpJvA
  Content-Type: application/json

Body:
  {
    "caseId": 12345,
    "taskType": "CP2000_REVIEW",
    "dueDate": "2024-10-15",
    "title": "CP2000 Notice Review",
    "details": { ... }
  }
```

### 2. Document Upload Endpoint
```
POST https://tiparser-dev.onrender.com/case-data/api/documents/upload

Headers:
  X-API-Key: sk_BIWGmwZeahwOyI9ytZNMnZmM_mY1SOcpl4OXlmFpJvA

Form Data:
  file: [PDF binary]
  caseId: 12345
  documentType: "CP2000"
  taxYear: "2022"
  description: "CP2000 Notice"
  category: "IRS_CORRESPONDENCE"
```

## 📝 Usage Examples

### Example 1: Run Complete Workflow
```bash
# Navigate to directory
cd "/Users/hemalathayalamanchi/Desktop/logicscase integration/CP2000_Pipeline"

# Run complete workflow
python3 complete_case_workflow.py

# Select option 1 for manual approval or 2 for auto-monitoring
```

### Example 2: Process Specific Sheet
```bash
# Get spreadsheet ID from URL
# https://docs.google.com/spreadsheets/d/1abc123xyz456/edit
# Spreadsheet ID: 1abc123xyz456

# Process approvals once
python3 sheet_approval_automation.py 1abc123xyz456 once

# Or start continuous monitoring
python3 sheet_approval_automation.py 1abc123xyz456 monitor
```

### Example 3: Create Sheets Only
```bash
# Just create Google Sheets from existing match data
python3 case_management_sheet.py
```

## 🎨 Sheet Features

### Conditional Formatting
- ✅ **Green**: Approved cases
- ❌ **Red**: Rejected cases
- 📋 **Default**: Cases under review

### Data Validation
- Status column has dropdown: Approve, Reject, Review
- Prevents typos and ensures consistent data

### Frozen Headers
- Header row stays visible when scrolling
- Easy to reference column names

### Auto-Resize Columns
- Columns automatically sized for readability

## 🔒 Permissions

Sheets are created with:
- **Editor access** for anyone with the link
- Stored in dedicated Google Drive folders
- Can be moved to shared drives if needed

## 📊 Monitoring Output

When monitoring is active, you'll see:
```
🔍 Starting to monitor sheet: 1abc123xyz456
⏱️ Check interval: 60 seconds

============================================================
✅ APPROVED case found in row 5
📋 Case Details:
   Case ID: 632150
   Name: Jeffrey Flax
   File: IRS CORR_CP2000_2022_DTD 09.09.2024_FLAX.pdf
📝 Creating task in Logics...
✅ Task created successfully for Case 632150
📤 Uploading document to Logics...
✅ Document uploaded successfully for Case 632150
✅ Case processing completed successfully!

✓ Check completed at 16:30:45
```

## 🛠️ Troubleshooting

### Issue: Credentials not found
**Solution**: Ensure `credentials.json` is in the CP2000_Pipeline directory

### Issue: No cases matched
**Solution**: 
- Check that LOGICS_DATA_*.json file exists
- Verify API key is correct
- Run `python3 test_logics_search.py` to test API

### Issue: Document upload fails
**Solution**:
- Verify PDF file exists in CP2000 folders
- Check file permissions
- Ensure file isn't corrupted

### Issue: Sheet not updating
**Solution**:
- Check Google API quotas
- Verify credentials have spreadsheet edit permissions
- Refresh the sheet in browser

## 📈 Success Metrics

After running the workflow, you'll see:
```
📊 Summary:
   Total Matched Cases: 127 (60.5%)
   Total Unmatched Cases: 83 (39.5%)
   Matched Sheet: https://docs.google.com/spreadsheets/d/...
   Unmatched Sheet: https://docs.google.com/spreadsheets/d/...
```

## 🔄 Workflow Files Generated

- `CASE_MATCHES_YYYYMMDD_HHMMSS.json` - Match results
- `WORKFLOW_SUMMARY_YYYYMMDD_HHMMSS.json` - Workflow execution summary
- Google Sheets in Drive (with timestamp in name)

## 💡 Best Practices

1. **Review before approving**: Check case details in the sheet
2. **Batch approvals**: Approve multiple cases, then run automation once
3. **Monitor logs**: Watch console output for any errors
4. **Backup data**: Keep CASE_MATCHES_*.json files
5. **Regular checks**: Run workflow daily for new batches

## 🎯 Next Steps

1. Open the matched cases Google Sheet
2. Review the cases in "Review" status
3. Change status to "Approve" for cases to process
4. Run automation to process approved cases
5. Check Logics system to verify tasks and documents

## 📞 Support

For issues or questions about:
- **API Endpoints**: Contact Logics API team
- **Google Sheets**: Check Google API documentation
- **Workflow Issues**: Review logs and error messages

---

**Last Updated**: November 4, 2025  
**Version**: 1.0.0


