# CP2000 Production Pipeline

## Overview
Production-ready pipeline for automated processing of CP2000 notices with Google Drive integration and Logics CRM matching.

## Directory Structure
```
CP2000_Production/
├── config/                  # Configuration files
│   ├── service-account-key.json  # Google Drive auth
│   ├── credentials.json     # API credentials
│   └── env.example         # Environment template
│
├── data/                   # Data storage
│   └── processing_history.json  # Processing records
│
├── logs/                   # Pipeline execution logs
│
├── Core Pipeline Files
│   ├── automated_pipeline.py     # Main orchestrator
│   ├── production_extractor.py   # Production extractor
│   ├── hundred_percent_accuracy_extractor.py  # Core engine
│   ├── logics_case_search.py    # Case matching
│   └── case_reviewer.py         # Review system
│
├── Processing Directories
│   ├── MATCHED_CASES/      # Successfully matched
│   ├── UNMATCHED_CASES/    # Need review
│   ├── QUALITY_REVIEW/     # Review files
│   ├── PROCESSED_FILES/    # Completed files
│   └── TEMP_PROCESSING/    # Temporary files
│
└── run_pipeline.sh         # Pipeline execution script
```

## Component Details

### 1. Core Pipeline Components

#### automated_pipeline.py
- Main orchestrator for the entire pipeline
- Monitors Google Drive folders for new CP2000 notices
- Coordinates processing and file movement
- Handles Google Drive integration
- Manages processing history

#### production_extractor.py
- Production-grade data extraction
- High-performance batch processing
- Incremental processing support
- Robust error handling
- Processing history tracking

#### hundred_percent_accuracy_extractor.py
- Core data extraction engine
- OCR processing with high accuracy
- Data validation and cleanup
- Pattern matching for data fields
- Quality checks

#### logics_case_search.py
- Case matching with Logics CRM
- API integration and error handling
- SSN and name matching logic
- Case validation
- Match confidence scoring

#### case_reviewer.py
- Case review interface
- Approval workflow management
- Quality control checks
- Review history tracking
- Batch processing support

### 2. Configuration Files

#### config/service-account-key.json
- Google Drive API authentication
- Service account credentials

#### config/credentials.json
- API credentials for various services
- Authentication configuration

#### config/.env
Required environment variables:
```bash
LOGICS_API_KEY=your_api_key
GOOGLE_DRIVE_FOLDER_ID=your_folder_id
```

### 3. Data Management

#### Processing Directories
- **MATCHED_CASES**: Successfully matched cases ready for upload
- **UNMATCHED_CASES**: Cases requiring manual review
- **QUALITY_REVIEW**: Review sheets and reports
- **PROCESSED_FILES**: Successfully processed documents
- **TEMP_PROCESSING**: Temporary processing directory

#### Logging
- Pipeline execution logs in `logs/`
- Error tracking and monitoring
- Performance metrics
- Processing statistics

## Usage

### 1. First-Time Setup
```bash
# Install dependencies
pip install -r requirements.txt

# Configure environment
cp config/env.example config/.env
# Edit .env with your credentials
```

### 2. Running the Pipeline

#### Normal Operation
```bash
./run_pipeline.sh
```

#### Test Mode
```bash
python automated_pipeline.py --test --limit 5
```

### 3. Review Process

1. Pipeline generates review files in QUALITY_REVIEW/
2. Review matched/unmatched cases
3. Approve or reject matches
4. Run case reviewer:
```bash
python case_reviewer.py
```

## Processing Flow

1. **File Detection**
   - Monitor Google Drive folders
   - Detect new CP2000 notices

2. **Data Extraction**
   - Extract data using hundred_percent_accuracy_extractor
   - Validate extracted information
   - Quality checks

3. **Case Matching**
   - Search Logics CRM
   - Match using SSN and name
   - Confidence scoring

4. **Review & Approval**
   - Generate review sheets
   - Manual approval process
   - Quality control

5. **Final Processing**
   - Upload approved documents
   - Create Logics tasks
   - Update processing history

## Maintenance

### Logs
- Check `logs/` directory for execution logs
- Monitor for errors and performance issues

### Cleanup
```bash
# Remove temporary files
rm -rf TEMP_PROCESSING/*

# Archive processed files (older than 30 days)
./archive_old_files.sh
```

### Monitoring
- Check processing history in data/processing_history.json
- Monitor QUALITY_REVIEW/ for pending reviews
- Check logs/ for errors

## Support

### Common Issues
1. **Authentication Errors**
   - Check config/service-account-key.json
   - Verify .env configuration

2. **Processing Errors**
   - Check logs/pipeline.log
   - Verify file permissions

3. **API Issues**
   - Check Logics API status
   - Verify API credentials

### Contact
For support, contact:
- Author: Hemalatha Yalamanchi
- Project: Mailroom Automation
- Repository: hyalamanchi/Mailroom-project