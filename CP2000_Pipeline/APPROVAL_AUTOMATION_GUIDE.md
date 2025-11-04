# 🤖 APPROVAL AUTOMATION GUIDE

## How It Works - Step by Step

### **MANUAL PROCESS (You do this):**

1. **Open the Google Sheet** 
   - The sheet created by `create_review_workbook.py`

2. **Go to "Matched Cases" tab**
   - Review each case carefully

3. **For each case you want to approve:**
   - Click on the **Status column (Column L)** for that row
   - A dropdown will appear
   - Select **"APPROVE"** from the dropdown

4. **That's it!** 
   - The automation will detect it and process automatically

---

### **AUTOMATED PROCESS (Script does this):**

The automation script monitors the sheet and:

```
┌─────────────────────────────────────────────────────────────┐
│  1. Monitors Google Sheet every 60 seconds                   │
└─────────────────┬───────────────────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────────────────┐
│  2. Reads "Matched Cases" tab                                │
│     Checks each row starting from row 8 (first data row)    │
└─────────────────┬───────────────────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────────────────┐
│  3. Checks Status column (Column L) for each row             │
│     ❓ Is it "APPROVE"?                                      │
│        ❌ NO  → Skip this row, check next row               │
│        ✅ YES → Process this case!                          │
└─────────────────┬───────────────────────────────────────────┘
                  │ (ONLY when APPROVE)
                  ▼
┌─────────────────────────────────────────────────────────────┐
│  4. FOR APPROVED CASES ONLY:                                 │
│     a. Extract case data (Case ID, filename, etc)            │
│     b. Create task in Logics API                             │
│     c. Upload PDF document to Logics                         │
│     d. Update Notes column with result                       │
└─────────────────────────────────────────────────────────────┘
```

---

## ⚙️ **Configuration**

### **What triggers processing?**
- **ONLY** when Status column = "APPROVE" (exact match, case-insensitive)

### **What does NOT trigger processing?**
- Status = "" (empty)
- Status = "UNDER_REVIEW"
- Status = "REJECT"
- Status = any other value

### **Duplicate protection:**
- Each processed row is tracked
- Once processed, won't be processed again (even if you change it back to APPROVE)
- To re-process: Restart the automation script

---

## 🚀 **How to Run the Automation**

### **Option 1: Interactive Mode (Easiest)**
```bash
cd CP2000_Pipeline
python3 run_approval_automation.py
```
- It will ask for the Spreadsheet ID
- It will ask for mode (monitor or once)

### **Option 2: Command Line**
```bash
python3 run_approval_automation.py <spreadsheet_id> monitor
```

### **Option 3: Single Check (No monitoring)**
```bash
python3 run_approval_automation.py <spreadsheet_id> once
```

---

## 📊 **Example Workflow**

### **Step 1: You review the sheet**
```
Row 8:  Case_ID: 12345 | Status: [empty]        → Not processed
Row 9:  Case_ID: 12346 | Status: UNDER_REVIEW  → Not processed
Row 10: Case_ID: 12347 | Status: APPROVE       → WILL BE PROCESSED! ✅
Row 11: Case_ID: 12348 | Status: REJECT         → Not processed
```

### **Step 2: Automation detects APPROVE**
```
🔍 Checking sheet...
✅ APPROVED case found in row 10
📋 Case Details:
   Case ID: 12347
   Name: John Doe
   File: CP2000_2023_123.pdf
   Tax Year: 2023
📝 Creating task in Logics...
✅ Task created successfully for Case 12347
📤 Uploading document to Logics...
📁 Found document at: CP2000/CP2000_2023_123.pdf
✅ Document uploaded successfully for Case 12347
✅ Case processing completed successfully!
```

### **Step 3: Notes column updated**
```
Row 10: Case_ID: 12347 | Status: APPROVE | Notes: ✅ Completed - Task Created & Document Uploaded
```

---

## 🎯 **Key Features**

### **1. Status Column Dropdown**
- Column L has data validation
- Click to see dropdown with 3 options:
  - APPROVE (green when selected)
  - UNDER_REVIEW (yellow when selected)
  - REJECT (red when selected)

### **2. Color Coding**
- **Green** = APPROVE (will be processed)
- **Yellow** = UNDER_REVIEW (will NOT be processed)
- **Red** = REJECT (will NOT be processed)

### **3. Notes Column**
- Automatically updated with processing status
- Shows success or error messages

---

## ⚠️ **Important Notes**

1. **Only "APPROVE" triggers processing**
   - Must be spelled exactly: "APPROVE"
   - Case doesn't matter: "approve", "Approve", "APPROVE" all work
   - But typos won't work: "Approved", "Aprove", etc.

2. **Processing is one-time**
   - Once processed, won't be processed again in the same session
   - To re-process: Stop and restart the automation

3. **Monitoring interval**
   - Checks every 60 seconds
   - Changes you make will be detected within 1 minute

4. **Files must be accessible**
   - PDF files must be in one of the search folders
   - If file not found, document upload will fail
   - Task will still be created even if upload fails

---

## 🔧 **Troubleshooting**

### **Case not being processed?**
✅ Check that Status column says exactly "APPROVE"
✅ Check that automation script is running
✅ Wait 60 seconds for next check
✅ Check the terminal logs for errors

### **Document upload failed?**
✅ Make sure PDF file exists in CP2000 folders
✅ Check filename matches exactly (case-sensitive)
✅ Check Logics API is accessible

### **Task creation failed?**
✅ Check Case ID is valid in Logics
✅ Check Logics API endpoint is working
✅ Check API key is correct

---

## 📝 **Summary**

**YOU DO:**
- Review cases in Google Sheet
- Click Status dropdown
- Select "APPROVE" for cases you want to process

**AUTOMATION DOES:**
- Monitors sheet continuously
- Only processes rows where Status = "APPROVE"
- Creates tasks in Logics
- Uploads documents to Logics
- Updates Notes with results

**IT WILL NOT:**
- Process cases with empty status
- Process cases with "UNDER_REVIEW"
- Process cases with "REJECT"
- Process the same case twice
- Do anything until you explicitly set Status to "APPROVE"

---

## 🎉 **That's It!**

The automation is **completely safe** - it only acts when you explicitly approve a case by setting the Status column to "APPROVE".

