# CP2000 Mail Room Automation Pipeline

> Automated IRS CP2000 document processing and case management system

![Python Version](https://img.shields.io/badge/python-3.9+-blue.svg)
![Status](https://img.shields.io/badge/status-production-success.svg)
![License](https://img.shields.io/badge/license-Proprietary-red.svg)

## 📋 Overview

An intelligent automation pipeline for processing IRS CP2000 (Underreported Income Notice) letters. This system extracts taxpayer information using OCR, matches cases to Logiqs CRM, organizes documents automatically, and creates review tasks for the tax resolution team.

**Key Benefits:**
- ⏱️ **Time Savings:** 4.5 hours per day (from 5-6 hours to 20-25 minutes)
- 🎯 **Match Rate:** 83-87% automatic case matching
- 📊 **Processing:** 100-150 files per day
- ✅ **Accuracy:** Enhanced OCR with validation

## 🚀 Features

### Core Capabilities
- **Automated OCR Extraction** - Extracts SSN, taxpayer names, tax years, notice dates
- **Smart Case Matching** - Fuzzy matching with name variations and SSN corrections
- **Google Drive Integration** - Automatic file organization and movement
- **Logiqs CRM Integration** - Document upload with automatic task creation
- **Intelligent Routing** - Matched cases → auto-upload, Unmatched → manual review
- **Comprehensive Reporting** - Excel and JSON reports for team coordination

### Workflow Automation
```
Input Folders → Extract Data → Match Cases → Organize Files
                                            ↓
                              Matched → Auto Upload to Logiqs
                              Unmatched → Manual Review Queue
```

## 📂 Project Structure

```
CP2000_Pipeline/
├── daily_pipeline_orchestrator.py    # Main automation script
├── production_extractor.py           # OCR and data extraction
├── logics_case_search.py            # Logiqs API integration
├── upload_to_logiqs.py               # Document upload with tasks
├── enhanced_case_matcher.py          # Advanced matching strategies
├── generate_upload_list.py           # Naming convention generator
├── hundred_percent_accuracy_extractor.py  # Core OCR engine
├── requirements.txt                  # Python dependencies
├── DAILY_WORKFLOW_GUIDE.md          # Complete workflow documentation
└── README.md                         # Technical documentation
```

## ⚙️ Installation

### Prerequisites
- Python 3.9 or higher
- Google Cloud Project with Drive API enabled
- Logiqs CRM API access
- Tesseract OCR installed

### Setup Steps

1. **Clone the repository**
```bash
git clone https://github.com/TaxReliefAdvocates/CP2000_Pipeline.git
cd CP2000_Pipeline
```

2. **Install dependencies**
```bash
pip install -r requirements.txt
```

3. **Configure Google Drive API**
   - Place `credentials.json` in the project root
   - Run authentication on first use (creates `token.pickle`)

4. **Configure environment variables**
```bash
# Create .env file
LOGIQS_API_KEY=your_api_key_here
LOGIQS_SECRET_TOKEN=your_secret_token_here
```

## 🎯 Usage

### Daily Workflow

**Step 1: Process New Files (5-10 minutes)**
```bash
python3 daily_pipeline_orchestrator.py
```
- Downloads files from Google Drive input folders
- Extracts data using OCR
- Matches to Logiqs CRM
- Organizes into matched/unmatched folders
- Generates daily reports

**Step 2: Upload Matched Cases (10-15 minutes)**
```bash
python3 upload_to_logiqs.py
```
- Uploads matched documents to Logiqs
- Creates review tasks automatically
- Generates upload reports

**Step 3: Review Unmatched Cases**
- Open `DAILY_REPORTS/UNMATCHED/*.xlsx`
- Process manually as needed

### Test Mode

Test with 5 files before production:
```bash
python3 daily_pipeline_orchestrator.py --test
```
- Processes only 5 files
- No files moved in Google Drive
- Safe for testing

## 📊 Expected Results

**Daily Processing (150 files):**
- ✅ Matched: 125 files (83%) → Auto-uploaded
- ⚠️ Unmatched: 25 files (17%) → Manual review
- ⏱️ Total Time: 20-25 minutes
- 💾 Time Saved: 4.5 hours per day

## 🔧 Configuration

### Google Drive Folders
Configure folder IDs in `daily_pipeline_orchestrator.py`:
```python
self.folders = {
    'input_cp2000': 'YOUR_FOLDER_ID',
    'input_newbatch': 'YOUR_FOLDER_ID',
    'output_matched': 'YOUR_FOLDER_ID',
    'output_unmatched': 'YOUR_FOLDER_ID'
}
```

### API Configuration
Logiqs API endpoints are configured in `logics_case_search.py` and `upload_to_logiqs.py`.

## 📈 Performance Metrics

| Metric | Value |
|--------|-------|
| Processing Speed | 100-150 files in 5-10 min |
| Match Rate | 83-87% |
| Upload Success | >95% |
| Time Savings | 4.5 hours/day |
| Files per Second | 0.3-0.5 |

## 🛠️ Technical Stack

- **Language:** Python 3.9+
- **OCR:** Tesseract, PyMuPDF, OpenCV
- **APIs:** Google Drive API, Logiqs CRM API
- **Data Processing:** Pandas, NumPy
- **Authentication:** OAuth 2.0, Basic Auth

## 📝 Documentation

- [DAILY_WORKFLOW_GUIDE.md](DAILY_WORKFLOW_GUIDE.md) - Complete daily workflow
- [TASK_CREATION_SUCCESS.md](TASK_CREATION_SUCCESS.md) - Task API integration
- [FOLDER_STRUCTURE_VISUAL.txt](FOLDER_STRUCTURE_VISUAL.txt) - Folder organization
- [README.md](README.md) - Technical documentation

## 🔒 Security Notes

- API credentials stored in `.env` (not tracked in git)
- Google OAuth tokens in `token.pickle` (not tracked in git)
- All sensitive data excluded via `.gitignore`

## 🤝 Contributing

This is a proprietary project for Tax Relief Advocates. Internal contributions only.

## 📞 Support

**Author:** Hemalatha Yalamanchi  
**Email:** [Your Email]  
**Organization:** Tax Relief Advocates

## 📄 License

Proprietary - All Rights Reserved  
© 2025 Tax Relief Advocates

## 🎉 Achievements

- ✅ 100% automated workflow
- ✅ 83-87% match rate
- ✅ 4.5 hours saved daily
- ✅ Production-ready system
- ✅ Comprehensive error handling
- ✅ Full audit trail

---

**Built with ❤️ by Hemalatha Yalamanchi for Tax Relief Advocates**

