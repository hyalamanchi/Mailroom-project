# Pre-Release Test Plan
**Date:** October 31, 2025  
**Test Objective:** Verify end-to-end workflow with 10 files

---

## Test Scope
- Extract data from 10 PDFs
- Generate quality review Excel
- Approve 1 case manually
- Upload that 1 approved case to Logiqs
- Verify document appears in Logiqs

---

## Step 1: Run Pre-Release Test (Extract & Match)

```bash
cd "/Users/hemalathayalamanchi/Desktop/logicscase integration/CP2000_Pipeline"

# Run pipeline for 10 files (generates review sheet, pauses)
python3 daily_pipeline_orchestrator.py --limit=10
```

**Expected Output:**
```
📋 GENERATING QUALITY REVIEW SHEET
...
✅ Quality Review Sheet Generated:
   📄 QUALITY_REVIEW/QUALITY_REVIEW_MATCHED_CASES_[timestamp].xlsx
   📊 [X] cases ready for review

⏸️  PIPELINE PAUSED FOR QUALITY REVIEW
```

**Files Created:**
- `QUALITY_REVIEW/QUALITY_REVIEW_MATCHED_CASES_[timestamp].xlsx` ← Your output file

---

## Step 2: Review & Approve 1 Case

### 2.1 Open the Excel File
- Navigate to: `QUALITY_REVIEW/QUALITY_REVIEW_MATCHED_CASES_[timestamp].xlsx`
- Open in Excel or Google Sheets

### 2.2 Review the Sheet
Check these columns:
- **Case_ID** - Logiqs case ID
- **Proposed_Filename** - New naming convention
- **Taxpayer_Name** - Full name
- **SSN_Last_4** - Last 4 digits
- **Tax_Year** - Year
- **Notice_Date** - Date on notice
- **Due_Date** - Response deadline

### 2.3 Approve ONLY 1 Case
1. Find ONE matched case (any row after instruction rows)
2. In **"Status"** column, type: `APPROVE`
3. Leave all other rows blank or type `UNDER_REVIEW`
4. **Optional:** Add note in "Notes" column like "Pre-release test - approved 1 case"
5. **Save the file** (Ctrl+S or Cmd+S)

**Example:**

| Case_ID | Taxpayer_Name | SSN_Last_4 | Status | Notes |
|---------|---------------|------------|---------|-------|
| 12345 | JOHN SMITH | 1234 | **APPROVE** | Pre-release test |
| 12346 | JANE DOE | 5678 | UNDER_REVIEW | |
| 12347 | BOB JONES | 9012 | UNDER_REVIEW | |

---

## Step 3: Upload the Approved Case

```bash
python3 daily_pipeline_orchestrator.py --upload-approved
```

**Expected Output:**
```
📋 PROCESSING QUALITY APPROVALS
================================================================================

📊 Quality Review Summary:
   ✅ Approved: 1 (will upload)
   ❌ Rejected: 0 (moved to UNMATCHED)
   🔍 Under Review: [X] (requires additional review)

📤 UPLOADING MATCHED CASES TO LOGIQS
================================================================================

1/1 - Uploading to Case 12345
   📄 File: CP2000_SMITH_JOHN_2023.pdf
   ✅ Document uploaded successfully
   ✅ Task created (ID: 78901)

📊 Upload Summary:
   ✅ Uploaded: 1
   ❌ Failed: 0
```

---

## Step 4: Verify in Logiqs

### 4.1 Login to Logiqs
- Go to: https://tps.logiqs.com/
- Login with your credentials

### 4.2 Find the Case
- Search for Case ID: 12345 (or whatever case you approved)
- Navigate to the case details

### 4.3 Verify Document
Check:
- ✅ Document appears in case documents
- ✅ Filename follows naming convention: `IRS_CORR_CP2000_2023_DTD_[date]_SMITH.pdf`
- ✅ Document opens and shows correct PDF

### 4.4 Verify Task
Check:
- ✅ Task was created
- ✅ Task subject: "Review CP2000 Notice - [date]"
- ✅ Task due date matches IRS response deadline
- ✅ Task priority is High (2)

---

## Expected Results

### ✅ Success Criteria
- [  ] 10 files processed
- [  ] Quality review Excel generated
- [  ] 1 case marked as APPROVE
- [  ] Remaining cases marked as UNDER_REVIEW
- [  ] 1 document uploaded to Logiqs
- [  ] Document has correct filename
- [  ] Task created with correct details
- [  ] Under Review cases NOT uploaded
- [  ] No errors in console

### 📁 Files Generated
- `QUALITY_REVIEW/QUALITY_REVIEW_MATCHED_CASES_[timestamp].xlsx`
- `DAILY_REPORTS/MATCHED/matched_cases_[timestamp].xlsx`
- `DAILY_REPORTS/UNMATCHED/unmatched_cases_[timestamp].xlsx`
- `PROCESSING_HISTORY.json`

---

## Troubleshooting

### Issue: No matched cases found
**Cause:** API key invalid or files don't match in Logics  
**Action:** Check `.env` file for `LOGICS_API_KEY`

### Issue: Upload failed
**Cause:** Logiqs API key invalid or case ID doesn't exist  
**Action:** 
1. Check `.env` file for `LOGIQS_API_KEY` and `LOGIQS_SECRET_TOKEN`
2. Verify case ID exists in Logiqs

### Issue: Document not in Logiqs
**Cause:** Upload may have succeeded but document not visible yet  
**Action:** 
1. Check console output for "✅ Document uploaded successfully"
2. Refresh Logiqs page
3. Check case documents tab

### Issue: Task not created
**Cause:** Task API authentication issue  
**Action:** Check console for task creation error message

---

## Cleanup After Test

```bash
# Optional: Remove test review file
rm QUALITY_REVIEW/QUALITY_REVIEW_MATCHED_CASES_*.xlsx

# Optional: Clear processing history to retest
rm PROCESSING_HISTORY.json
```

---

## Ready for Production?

If all success criteria are met:
- ✅ **YES** - Proceed with full production run
- ❌ **NO** - Review errors and fix issues

---

## Production Run Command

After successful test:
```bash
python3 daily_pipeline_orchestrator.py
```

This will process ALL files from Google Drive.

---

**Test Completed:** _______________  
**Tester:** _______________  
**Result:** ☐ PASS  ☐ FAIL  
**Notes:** _______________

