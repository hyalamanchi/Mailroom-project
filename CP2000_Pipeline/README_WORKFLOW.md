# CP2000 Case Management System

## 🎯 Overview

Complete automated pipeline for processing CP2000 notices with Logics integration and Google Sheets approval workflow.

## ✨ Key Features

- 🔍 **Automatic Case Matching**: Matches CP2000 cases with Logics system (60.5% success rate)
- 📊 **Google Sheets Integration**: Interactive approval workflow with status dropdowns
- 🤖 **Automated Processing**: Creates tasks and uploads documents when approved
- 📁 **Organized Structure**: Auto-creates folder structure in Google Drive
- ✅ **Real-time Updates**: Status tracking and processing feedback

## 🚀 Quick Start

```bash
# 1. Install dependencies
pip3 install -r requirements.txt

# 2. Add Google credentials (credentials.json)

# 3. Run complete workflow
python3 complete_case_workflow.py

# OR use interactive script
./run_case_workflow.sh
```

## 📋 Workflow Steps

### 1. Case Matching
Automatically matches extracted CP2000 cases with Logics system using:
- SSN last 4 digits
- Taxpayer last name
- Supports both exact and fuzzy matching

**Result**: `CASE_MATCHES_YYYYMMDD_HHMMSS.json`

### 2. Google Sheets Creation
Creates two organized sheets:
- **Matched Cases**: With approval workflow (Approve/Reject/Review)
- **Unmatched Cases**: For manual review and case creation

**Result**: Interactive Google Sheets with validation and formatting

### 3. Approval Processing
When you set status to "Approve":
1. ✅ Creates CP2000 review task in Logics
2. 📤 Uploads PDF document to case
3. 📝 Updates processing status in sheet

**Result**: Automated task and document upload to Logics

## 📊 Google Sheet Features

### Matched Cases Sheet Columns

| Column | Description |
|--------|-------------|
| Status | Dropdown: Approve, Reject, Review |
| Case ID | Logics case identifier |
| Taxpayer Name | Full name from Logics |
| SSN Last 4 | Last 4 digits for privacy |
| Tax Year | Year of the CP2000 notice |
| Notice Date | Date of notice |
| Response Due | Deadline to respond |
| Days Remaining | Countdown to deadline |
| Urgency Level | CRITICAL/HIGH/MEDIUM |
| File Name | Original PDF filename |
| Processing Status | Real-time status |
| Upload Status | Document upload tracking |

**Features**:
- ✅ Color-coded status (green=approve, red=reject)
- ✅ Data validation dropdowns
- ✅ Frozen headers
- ✅ Auto-resized columns
- ✅ Public edit access

## 🔧 API Integration

### Endpoints Used

1. **Case Matching** ✅
   ```
   POST /case-data/api/case/match
   ```

2. **Task Creation** ✅
   ```
   POST /case-data/api/tasks/create
   ```

3. **Document Upload** ✅
   ```
   POST /case-data/api/documents/upload
   ```

## 📁 Project Structure

```
CP2000_Pipeline/
├── Core Workflow
│   ├── case_id_extractor.py          # Case matching
│   ├── case_management_sheet.py       # Sheet creation
│   ├── sheet_approval_automation.py   # Approval processing
│   └── complete_case_workflow.py      # Full orchestration
│
├── API Integration
│   ├── logics_case_search.py         # Case matching API
│   └── upload_to_logiqs.py           # Task/doc upload
│
├── Documentation
│   ├── CASE_MANAGEMENT_WORKFLOW_GUIDE.md  # Complete guide
│   ├── QUICK_START.md                     # Quick reference
│   ├── IMPLEMENTATION_SUMMARY.md          # Architecture
│   └── PRE_RELEASE_TEST_SUMMARY.md        # Test results
│
└── Scripts
    ├── run_case_workflow.sh          # Interactive runner
    └── test_logics_search.py         # API testing
```

## 🎨 Usage Examples

### Run Complete Workflow
```bash
python3 complete_case_workflow.py
```

### Match Cases Only
```bash
python3 case_id_extractor.py
```

### Create Sheets Only
```bash
python3 case_management_sheet.py
```

### Process Approvals (Single Check)
```bash
python3 sheet_approval_automation.py <SHEET_ID> once
```

### Continuous Monitoring
```bash
python3 sheet_approval_automation.py <SHEET_ID> monitor
```

## 📈 Test Results

- **Cases Processed**: 210
- **Matched**: 127 (60.5%)
- **Unmatched**: 83 (39.5%)
- **API Response**: ~200ms per case
- **Total Time**: ~42 seconds

## 🔒 Security

- Google credentials stored locally (`credentials.json`)
- API keys in environment variables
- Sheets have editor access via link
- No sensitive data in logs

## 🛠️ Troubleshooting

| Issue | Solution |
|-------|----------|
| No credentials.json | Add Google service account file |
| API 400 errors | Verify API key and parameters |
| Sheet not updating | Refresh browser, check permissions |
| Document not found | Verify file path in CP2000 folders |

## 📚 Documentation

- **Complete Guide**: `CASE_MANAGEMENT_WORKFLOW_GUIDE.md`
- **Quick Start**: `QUICK_START.md`
- **Architecture**: `IMPLEMENTATION_SUMMARY.md`
- **Test Results**: `PRE_RELEASE_TEST_SUMMARY.md`

## 🔄 Workflow Diagram

```
Extract CP2000s
     ↓
Match with Logics (60.5% success)
     ↓
Create Google Sheets
     ├── Matched Cases (127) → Approval Workflow
     └── Unmatched Cases (83) → Manual Review
     ↓
User Approves Cases
     ↓
Automation Detects "Approve"
     ↓
Create Task in Logics
     ↓
Upload Document to Case
     ↓
Update Sheet Status
```

## 🎯 Next Steps

1. ✅ Open matched cases sheet
2. ✅ Review case details
3. ✅ Set status to "Approve"
4. ✅ Run automation
5. ✅ Verify in Logics system

## 💡 Tips

- **Batch Processing**: Approve multiple cases, then run automation once
- **Monitoring Mode**: For large batches, use continuous monitoring
- **Manual Review**: Check unmatched cases for data quality issues
- **Logs**: Console output shows detailed progress and errors

## 📞 Support

Check logs for detailed error messages. Common issues and solutions are in the troubleshooting section above.

## 🚀 Recent Updates

**November 4, 2025**
- ✅ Fixed critical API bug (0% → 60.5% match rate)
- ✅ Implemented complete Google Sheets workflow
- ✅ Added automated task creation and document upload
- ✅ Created comprehensive documentation

---

**Version**: 1.0.0  
**Status**: Production Ready  
**Last Updated**: November 4, 2025


