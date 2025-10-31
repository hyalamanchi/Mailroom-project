# 📋 Daily Mail Room Workflow Guide

## 🔄 Complete Automated Workflow

### **Flow Diagram:**
```
┌─────────────────────────────────────────────────────────────────┐
│                    DAILY MAIL ROOM PIPELINE                     │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────┐
│   FOLDER A      │  ← New CP2000 letters arrive daily
│   (Incoming)    │     • cp2000_incoming
│                 │     • newbatch_incoming
│ 📥 New Files    │     • newbatch2_incoming
└────────┬────────┘
         │
         ↓
    ┌────────────┐
    │  PIPELINE  │
    │ PROCESSING │
    │            │
    │ 1. Extract │  ← OCR & Data Extraction
    │ 2. Match   │  ← Search in Logiqs CRM
    │ 3. Sort    │  ← Matched vs Unmatched
    └─────┬──────┘
          │
          ├────────────────┬─────────────────┐
          ↓                ↓                 ↓
┌─────────────────┐  ┌──────────────┐  ┌──────────────────┐
│   FOLDER B      │  │   FOLDER C   │  │  LOCAL REPORTS   │
│   (Matched)     │  │ (Unmatched)  │  │                  │
│                 │  │              │  │ • JSON files     │
│ ✅ Auto Upload  │  │ ⚠️ Manual    │  │ • Excel reports  │
│                 │  │    Review    │  │ • Statistics     │
└────────┬────────┘  └──────────────┘  └──────────────────┘
         │
         ↓
    ┌────────────┐
    │  LOGIQS    │
    │  UPLOAD    │
    │            │
    │ • Document │
    │ • Task     │
    └────────────┘
```

---

## 📂 Google Drive Folder Structure

### **Input Folders (Folder A):**
- **cp2000_incoming** - Original incoming folder
- **newbatch_incoming** - New batch folder 1
- **newbatch2_incoming** - New batch folder 2

### **Output Folders:**
- **CP2000_MATCHED** (Folder B) - Matched cases ready for auto-upload
- **CP2000_UNMATCHED** (Folder C) - Unmatched cases for manual review

---

## 🚀 Daily Pipeline Steps

### **Step 1: Download New Files** 📥
```bash
python3 daily_pipeline_orchestrator.py
```

**What happens:**
- Scans all input folders (A) for new CP2000 letters
- Downloads PDFs to local temporary folder
- Tracks source folder for each file

**Output:**
- All files downloaded locally for processing

---

### **Step 2: Extract & Match** 🔍

**What happens:**
- Extracts data from each PDF using OCR
  - SSN (last 4 digits)
  - Taxpayer name
  - Tax year
  - Notice date
  - Response due date
- Searches Logiqs CRM for matching case
- Categorizes as "matched" or "unmatched"

**Output:**
- Matched cases: Have Case ID
- Unmatched cases: No Case ID found

---

### **Step 3: Move Files** 📦

**What happens:**
- **Matched files** → Moved to `CP2000_MATCHED` (Folder B)
- **Unmatched files** → Moved to `CP2000_UNMATCHED` (Folder C)
- Files are **removed** from input folders (A)

**Result:**
- Input folders are now empty (ready for tomorrow's batch)
- Output folders contain organized files

---

### **Step 4: Generate Reports** 📊

**Local Reports Created:**

**Matched Cases Report:**
- Location: `DAILY_REPORTS/MATCHED/`
- Files:
  - `matched_cases_YYYYMMDD_HHMMSS.json` (detailed data)
  - `matched_cases_YYYYMMDD_HHMMSS.xlsx` (Excel for review)
- Contains: Filename, Case ID, Name, SSN, Tax Year, Status

**Unmatched Cases Report:**
- Location: `DAILY_REPORTS/UNMATCHED/`
- Files:
  - `unmatched_cases_YYYYMMDD_HHMMSS.json` (detailed data)
  - `unmatched_cases_YYYYMMDD_HHMMSS.xlsx` (Excel for manual review)
- Contains: Filename, Name, SSN, Tax Year, Reason, Action Needed

**Daily Summary:**
- Location: `DAILY_REPORTS/`
- File: `daily_summary_YYYYMMDD_HHMMSS.json`
- Contains: Statistics, folder IDs, processing details

---

### **Step 5: Upload Matched Cases** ⬆️

**After pipeline completes, run:**
```bash
python3 upload_to_logiqs.py
```

**What happens:**
- Reads matched cases from Folder B (CP2000_MATCHED)
- Downloads each file from Google Drive
- Renames with new convention
- Uploads to Logiqs with Case ID
- Creates task for each document
- Generates upload reports

**Output:**
- Documents uploaded to Logiqs
- Tasks created in Logiqs
- Upload success/failure reports

---

## 📋 Complete Daily Workflow

### **Morning Routine (Automated):**

```bash
# 1. Process new files (5-10 minutes)
python3 daily_pipeline_orchestrator.py

# This will:
# - Download new files from Folder A
# - Extract data and match to Logiqs
# - Move matched → Folder B
# - Move unmatched → Folder C
# - Generate daily reports

# 2. Upload matched cases (10-15 minutes)
python3 upload_to_logiqs.py

# This will:
# - Upload all matched files to Logiqs
# - Create tasks automatically
# - Generate upload reports
```

**Total Time:** ~20-25 minutes (vs. 5-6 hours manual!)

---

## 📊 Example Daily Report

### **Processing Summary:**
```
Date: October 31, 2025 09:00:00

Total Files Processed: 150
  ✅ Matched: 125 (83%)
  ⚠️  Unmatched: 25 (17%)

File Distribution:
  Folder B (Matched): 125 files → Ready for auto-upload
  Folder C (Unmatched): 25 files → Manual review needed
```

### **Unmatched Cases (Manual Review):**
| Filename | Name | SSN | Reason | Action |
|----------|------|-----|--------|--------|
| CP2000_Smith.pdf | Smith | 1234 | No case found | Create case manually |
| CP2000_Jones.pdf | Jones | 5678 | Extraction failed | Review PDF quality |
| CP2000_Brown.pdf | Brown | 9012 | Missing SSN | Extract SSN manually |

---

## 🔄 File Movement Details

### **How Files Move:**

**Input (Folder A):**
```
Before: 150 files in cp2000_incoming/
After:  0 files (all processed and moved)
```

**Output (Folder B - Matched):**
```
Before: 0 files
After:  125 files ready for upload
Files: Matched cases with Case IDs
```

**Output (Folder C - Unmatched):**
```
Before: 0 files
After:  25 files needing manual review
Files: Cases without matching Case IDs
```

---

## 🛠️ Manual Review Process

### **For Unmatched Cases (Folder C):**

1. **Open Excel Report:**
   ```
   DAILY_REPORTS/UNMATCHED/unmatched_cases_YYYYMMDD.xlsx
   ```

2. **Review Each Case:**
   - Check reason for no match
   - Verify extracted data quality
   - Search Logiqs manually if needed

3. **Take Action:**
   - **If case exists in Logiqs:**
     - Find Case ID manually
     - Add to matched list
     - Move file to Folder B
   
   - **If case doesn't exist:**
     - Create new case in Logiqs
     - Note Case ID
     - Process file separately

4. **Weekly Cleanup:**
   - Review all unmatched cases from the week
   - Identify patterns (common OCR errors)
   - Improve extraction rules if needed

---

## 📈 Success Metrics

### **Target KPIs:**
- **Match Rate:** >80% automated matching
- **Processing Time:** <20 minutes for 100 files
- **Upload Success:** >95% successful uploads
- **Manual Review:** <20 cases per day

### **Actual Results (Expected):**
- **Match Rate:** 83-87% (based on current data)
- **Processing Time:** 15-25 minutes for 100-150 files
- **Upload Success:** 95-98%
- **Time Saved:** 4.5 hours per day

---

## 🎯 Folder Configuration

### **To Configure Your Folders:**

1. **Create Output Folders in Google Drive:**
   - Create: `CP2000_MATCHED` folder
   - Create: `CP2000_UNMATCHED` folder

2. **Get Folder IDs:**
   - Open folder in browser
   - Copy ID from URL: `https://drive.google.com/drive/folders/{FOLDER_ID}`

3. **Update Script (if needed):**
   ```python
   # In daily_pipeline_orchestrator.py
   self.folders = {
       'output_matched': 'YOUR_MATCHED_FOLDER_ID',
       'output_unmatched': 'YOUR_UNMATCHED_FOLDER_ID'
   }
   ```

**Note:** The script will auto-create these folders if they don't exist!

---

## 🔧 Troubleshooting

### **No Files Downloaded:**
- Check if input folders have new files
- Verify Google Drive authentication
- Check folder IDs are correct

### **Low Match Rate (<50%):**
- Review extraction quality
- Check OCR accuracy
- Verify Logiqs API is working
- Review unmatched report for patterns

### **Upload Failures:**
- Check API key is valid
- Verify network connectivity
- Review error logs in upload report
- Check file size (<6MB per file)

---

## 📝 Best Practices

### **Daily Operations:**
1. ✅ Run pipeline first thing in morning
2. ✅ Review daily summary before upload
3. ✅ Upload matched cases immediately
4. ✅ Flag unmatched for afternoon review
5. ✅ Clean up reports weekly

### **Weekly Review:**
1. ✅ Analyze match rate trends
2. ✅ Review common unmatched reasons
3. ✅ Update extraction rules if needed
4. ✅ Archive old reports

### **Monthly Review:**
1. ✅ Overall statistics
2. ✅ Performance improvements
3. ✅ System optimizations
4. ✅ Process refinements

---

## 🚨 Important Notes

1. **File Movement is Permanent:**
   - Files are moved (not copied) from Folder A
   - Ensure pipeline completes before manual intervention

2. **Manual Review Required:**
   - Always review unmatched cases within 24 hours
   - Don't let Folder C accumulate files

3. **Backup:**
   - Google Drive keeps file history
   - Local reports are saved daily
   - Can restore files if needed

4. **Permissions:**
   - Script needs Google Drive write access
   - Ensure token.pickle has proper scopes

---

## ✅ Success Checklist

**Before Running Pipeline:**
- [ ] New files are in Folder A (input folders)
- [ ] Google Drive authenticated (token.pickle exists)
- [ ] Folder B and C exist (or script will create them)
- [ ] Logiqs API key is valid

**After Running Pipeline:**
- [ ] All files moved from Folder A
- [ ] Matched files in Folder B
- [ ] Unmatched files in Folder C
- [ ] Daily reports generated
- [ ] Summary reviewed

**After Upload:**
- [ ] All matched files uploaded to Logiqs
- [ ] Tasks created for each document
- [ ] Upload report reviewed
- [ ] Failed uploads documented

---

**Status:** ✅ READY FOR PRODUCTION  
**Author:** Hemalatha Yalamanchi  
**Last Updated:** October 30, 2025  
**Version:** 1.0

