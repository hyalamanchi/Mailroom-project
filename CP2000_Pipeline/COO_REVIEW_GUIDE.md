# COO Review Process - Complete Guide

**Author:** Hemalatha Yalamanchi  
**Date:** October 31, 2025  
**Version:** 1.0

---

## 📋 Overview

The COO Review Process ensures **100% quality control** before any documents are uploaded to Logiqs CRM and sent to clients. This two-step workflow prevents errors and allows for human oversight of automated case matching.

---

## 🔄 Two-Step Workflow

### **Step 1: Generate Review Sheet**
Pipeline extracts data, matches cases, and **PAUSES** for COO approval.

### **Step 2: Upload Approved Cases**
Only COO-approved cases are uploaded to Logiqs automatically.

---

## 🚀 Step-by-Step Instructions

### **Step 1: Run the Pipeline (Generate Review Sheet)**

#### Command:
```bash
cd "/Users/hemalathayalamanchi/Desktop/logicscase integration/CP2000_Pipeline"
python3 daily_pipeline_orchestrator.py
```

#### What Happens:
1. ✅ Downloads PDFs from Google Drive CP2000 folders
2. ✅ Extracts data using OCR (100% accuracy)
3. ✅ Searches Logics API for case matches
4. ✅ Generates COO Review Excel file in `COO_REVIEW/` folder
5. ⏸️  **PIPELINE PAUSES** - Nothing uploaded yet!

#### Expected Output:
```
✅ COO Review Sheet Generated:
   📄 COO_REVIEW/COO_REVIEW_MATCHED_CASES_20251031_153045.xlsx
   📊 47 cases ready for review

⏸️  PIPELINE PAUSED FOR COO REVIEW

📋 NEXT STEPS:
   1. Open: COO_REVIEW/COO_REVIEW_MATCHED_CASES_20251031_153045.xlsx
   2. Review each matched case
   3. In 'Approval_Status' column, enter:
      • APPROVE - Will upload to Logiqs
      • REJECT - Will move to UNMATCHED folder
      • REVIEW - Needs additional review
   4. Save the file
   5. Run: python3 daily_pipeline_orchestrator.py --upload-approved
```

---

### **Step 2: COO Reviews and Approves Cases**

#### Open the Excel File:
Navigate to: `COO_REVIEW/COO_REVIEW_MATCHED_CASES_[timestamp].xlsx`

#### Review Sheet Columns:

| Column | Description |
|--------|-------------|
| **Case_ID** | Logiqs case ID (matched from Logics API) |
| **Original_Filename** | Original PDF filename from Google Drive |
| **Proposed_Filename** | New filename using naming convention |
| **Taxpayer_Name** | Full name extracted from document |
| **SSN_Last_4** | Last 4 digits of SSN |
| **Letter_Type** | Type of IRS letter (CP2000, CP2501, etc.) |
| **Tax_Year** | Tax year for the notice |
| **Notice_Date** | Date on the IRS notice |
| **Due_Date** | Response deadline |
| **Source_Folder** | Original Google Drive folder path |
| **Match_Confidence** | Confidence level (always "High" currently) |
| **Approval_Status** | 🔴 **COO FILLS THIS** |
| **COO_Notes** | Optional notes from COO |

#### Naming Convention Format:
```
IRS_CORR_{Letter Type}_{Tax Year}_DTD_{Date of Notice}_{Last Name}.pdf
```

**Example:**
```
IRS_CORR_CP2000_2023_DTD_10-15-2024_SMITH.pdf
```

#### COO Actions:

1. **Review Each Case:**
   - Verify Case ID is correct
   - Check taxpayer name matches SSN
   - Verify tax year and dates look reasonable
   - Review proposed filename

2. **In "Approval_Status" Column, Enter:**
   - ✅ **APPROVE** - Case looks good, ready to upload
   - ❌ **REJECT** - Case has errors (wrong case ID, bad data, etc.)
   - 🔍 **REVIEW** - Needs additional investigation

3. **Add Notes (Optional):**
   - Use "COO_Notes" column to explain rejections or concerns
   - Example: "Wrong case ID - SSN doesn't match"

4. **Save the File:**
   - Press `Ctrl+S` (Windows) or `Cmd+S` (Mac)
   - Close Excel

#### Example Review:

| Case_ID | Taxpayer_Name | SSN_Last_4 | Proposed_Filename | **Approval_Status** | **COO_Notes** |
|---------|---------------|------------|-------------------|---------------------|---------------|
| 12345 | JOHN SMITH | 1234 | IRS_CORR_CP2000_2023_DTD_10-15-2024_SMITH.pdf | **APPROVE** | Looks good |
| 12346 | JANE DOE | 5678 | IRS_CORR_CP2000_2022_DTD_09-20-2024_DOE.pdf | **APPROVE** | |
| 12347 | BOB JONES | 9012 | IRS_CORR_CP2000_2023_DTD_10-01-2024_JONES.pdf | **REJECT** | Wrong case ID |
| 12348 | MARY BROWN | 3456 | IRS_CORR_CP2000_2021_DTD_08-15-2024_BROWN.pdf | **REVIEW** | Verify year |

---

### **Step 3: Upload Approved Cases (Automatic)**

#### Command:
```bash
python3 daily_pipeline_orchestrator.py --upload-approved
```

This command:
- Reads the most recent COO review file
- Automatically finds: `COO_REVIEW/COO_REVIEW_MATCHED_CASES_[latest].xlsx`

#### What Happens Automatically:

For **APPROVED** cases:
1. ✅ Uploads PDF to Logiqs CRM
2. ✅ Creates task with due date
3. ✅ Renames file using approved naming convention
4. ✅ Moves to `CP2000_MATCHED` folder in Google Drive

For **REJECTED** cases:
1. ❌ Moves to `CP2000_UNMATCHED` folder
2. ❌ No upload to Logiqs
3. 📝 COO notes saved in report

For **REVIEW** cases:
1. 🔍 Stays in place (not uploaded)
2. 🔍 Requires COO to change status to APPROVE or REJECT
3. 🔍 Can be processed in a later run

#### Expected Output:
```
📋 PROCESSING COO APPROVALS
================================================================================

📊 COO Review Summary:
   ✅ Approved: 45 (will upload)
   ❌ Rejected: 1 (moved to UNMATCHED)
   🔍 Needs Review: 1 (requires additional review)

⚠️  WARNING: 1 cases still need review
   These will NOT be uploaded until approved
   • Case 12348: CP2000_BROWN_2021.pdf

📤 UPLOADING MATCHED CASES TO LOGIQS
================================================================================

1/45 - Uploading to Case 12345
   📄 File: CP2000_SMITH_2023.pdf
   ✅ Document uploaded successfully
   ✅ Task created (ID: 78901)

2/45 - Uploading to Case 12346
   📄 File: CP2000_DOE_2022.pdf
   ✅ Document uploaded successfully
   ✅ Task created (ID: 78902)

...

📊 Upload Summary:
   ✅ Uploaded: 45
   ❌ Failed: 0
```

---

## 🔍 Common Scenarios

### **Scenario 1: All Cases Look Good**
**Action:** Mark all as **APPROVE** → Run `--upload-approved`  
**Result:** All 47 cases uploaded to Logiqs

### **Scenario 2: One Case Has Wrong Case ID**
**Action:** Mark as **REJECT** with note "Wrong case ID"  
**Result:** 46 cases uploaded, 1 moved to UNMATCHED for manual fixing

### **Scenario 3: Unsure About a Case**
**Action:** Mark as **REVIEW** with note "Need to verify with team"  
**Result:** 46 cases uploaded, 1 stays pending until you decide

### **Scenario 4: Need to Re-Review Later**
**Action:** Close Excel without saving  
**Result:** Run Step 3 later when ready (review file still available)

---

## ⚠️ Important Notes

### **Nothing Uploads Without COO Approval**
- Step 1 only generates the review sheet
- No documents go to clients until Step 3
- Safe to run during business hours

### **Review Files Are Saved**
- All review sheets saved in `COO_REVIEW/` folder
- Timestamp in filename for easy tracking
- Can review previous batches anytime

### **Cases Marked REVIEW**
- Will NOT upload automatically
- Stay in pending state
- Change to APPROVE or REJECT in next run
- Or manually process in Logiqs

### **Rejected Cases**
- Go to UNMATCHED folder
- COO notes saved in report
- Can be manually matched later
- Won't be reprocessed automatically

---

## 🧪 Test Mode (Optional)

To test the pipeline without affecting production:

```bash
python3 daily_pipeline_orchestrator.py --test --limit=5
```

**Test Mode Features:**
- Processes only 5 files
- No uploads to Logiqs
- No file movement in Google Drive
- Generates test reports
- Safe for validation

---

## 🚨 Emergency: Skip Review (NOT RECOMMENDED)

If you need to bypass COO review temporarily:

```bash
python3 daily_pipeline_orchestrator.py --skip-review
```

**WARNING:**
- Uploads ALL matched cases immediately
- No human oversight
- Only use in emergencies
- 5-second countdown with cancel option

---

## 📊 Reports Generated

After upload completion:

### **Excel Reports:**
- `DAILY_REPORTS/MATCHED/matched_cases_[timestamp].xlsx`
  - All approved and uploaded cases
  - Document IDs
  - Task IDs
  
- `DAILY_REPORTS/UNMATCHED/unmatched_cases_[timestamp].xlsx`
  - Rejected cases
  - Cases with missing data
  - Manual review needed

### **JSON Reports:**
- Complete data export
- Machine-readable format
- Audit trail

---

## 📞 Support & Troubleshooting

### **No Review File Generated**
**Cause:** No matched cases found  
**Solution:** Check if files are in Google Drive input folders

### **Can't Find Review File**
**Location:** `COO_REVIEW/COO_REVIEW_MATCHED_CASES_[timestamp].xlsx`  
**Tip:** Sort by date modified to find latest

### **Excel File Won't Open**
**Cause:** File may be locked  
**Solution:** Close all Excel instances and try again

### **Upload Failed for Some Cases**
**Check:** Error messages in console output  
**Common Issues:**
- Case ID doesn't exist in Logiqs
- PDF file size too large (>6MB)
- Network connection issues

### **Need to Re-Run Upload**
**Solution:** Edit review file, change statuses, run `--upload-approved` again  
**Safe:** Already uploaded cases are tracked in history

---

## 📝 Best Practices

1. **Review Promptly**
   - Review sheet generated → Upload same day
   - Clients expect timely responses

2. **Check Edge Cases**
   - Unusual tax years (very old or future)
   - Duplicate names
   - Missing or partial data

3. **Document Rejections**
   - Always add COO notes for REJECT status
   - Helps team understand issues

4. **Track REVIEW Cases**
   - Keep a list of pending review cases
   - Follow up before next pipeline run

5. **Verify First Run**
   - For first production run, spot-check a few uploads in Logiqs
   - Confirm documents appear correctly

---

## 📅 Daily Workflow Example

**Morning (9:00 AM):**
```bash
python3 daily_pipeline_orchestrator.py
```
- Generates review sheet
- Takes ~15 minutes for 100 files

**Morning (9:30 AM):**
- COO reviews Excel file
- Marks approvals/rejections
- Takes ~10-15 minutes

**Morning (10:00 AM):**
```bash
python3 daily_pipeline_orchestrator.py --upload-approved
```
- Uploads approved cases
- Takes ~10 minutes for 100 cases

**Total Time:** ~35-40 minutes (vs. 5-6 hours manual)

---

## ✅ Checklist

### Before Step 1:
- [ ] All PDFs uploaded to Google Drive
- [ ] Service account has access to folders
- [ ] `.env` file configured

### Before Step 2:
- [ ] Review file opened in Excel
- [ ] All cases reviewed
- [ ] Approval statuses entered
- [ ] File saved

### Before Step 3:
- [ ] Review file completed
- [ ] Ready to upload to clients
- [ ] Logiqs credentials in `.env`

---

**Questions? Issues? Contact the development team or review the main README.md**

**Happy Processing! 🚀**

