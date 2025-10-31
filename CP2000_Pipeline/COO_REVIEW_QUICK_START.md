# COO Review - Quick Start Guide

**🚀 Get Started in 2 Minutes**

---

## Step 1: Generate Review Sheet

```bash
python3 daily_pipeline_orchestrator.py
```

**Output:** `COO_REVIEW/COO_REVIEW_MATCHED_CASES_[timestamp].xlsx`

**Pipeline PAUSES here** ⏸️

---

## Step 2: Review in Excel

1. Open the Excel file
2. Review each row
3. In **"Approval_Status"** column, type:
   - `APPROVE` ✅ (ready to upload)
   - `REJECT` ❌ (has errors)
   - `REVIEW` 🔍 (need more info)
4. Save the file

---

## Step 3: Upload Approved

```bash
python3 daily_pipeline_orchestrator.py --upload-approved
```

**Done!** ✅ Approved cases uploaded to Logiqs

---

## What Gets Reviewed?

| Column | What to Check |
|--------|---------------|
| **Case_ID** | Is this the right case? |
| **Proposed_Filename** | Does naming look correct? |
| **Taxpayer_Name** | Name match SSN? |
| **Tax_Year** | Year look reasonable? |
| **Notice_Date** | Date make sense? |

---

## Naming Convention

```
IRS_CORR_{Letter Type}_{Tax Year}_DTD_{Notice Date}_{Last Name}.pdf
```

**Example:**
```
IRS_CORR_CP2000_2023_DTD_10-15-2024_SMITH.pdf
```

---

## Time Estimate

- **Step 1:** 15 minutes (automatic)
- **Step 2:** 10-15 minutes (COO review)
- **Step 3:** 10 minutes (automatic)

**Total: ~35-40 minutes** (vs 5-6 hours manual!)

---

## Need Help?

📘 Full Guide: `COO_REVIEW_GUIDE.md`  
📧 Questions? Check the main README.md

---

**That's it! Simple 3-step process. 🎉**

