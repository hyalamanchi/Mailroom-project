# CP2000 Mail Room Automation Pipeline

**Author:** Hemalatha Yalamanchi  
**Organization:** IRS Tax Resolution  
**Last Updated:** October 2025

**Specialized pipeline for processing CP2000 (Underreported Income Notice) letters**

## Overview

This pipeline is designed specifically for CP2000 letters with:
- ✅ Joint filer parsing (names with "&" or "AND")
- ✅ Filename fallback strategy (when OCR fails)
- ✅ Enhanced OCR garbage detection
- ✅ C/O line filtering
- ✅ Batch processing for multiple datasets

## Quick Start

### Process Both Batches (Original + New)
```bash
cd CP2000_Pipeline
python process_all_batches.py
```

### Process Single Batch
```bash
python cp2000_extractor.py "input_folder" "output_folder"
```

## Pipeline Features

### 1. Intelligent Name Extraction
- **Joint Filers**: Parses "ROBERTO MALAVE & KATHERINE A LYNCH" → extracts both persons
- **C/O Filtering**: Skips "C/O ELIZABETH CASTELLANOS" lines
- **Filename Fallback**: Uses "_LASTNAME.pdf" when OCR fails

### 2. OCR Garbage Detection
Rejects common OCR errors:
- Mixed case within words: "Rbertomalaer"
- Lowercase before uppercase: "uneung"
- 5+ consecutive consonants: "nsennnnrenee"
- Known OCR noise words: "thugs", "recelved", "mauna", etc.

### 3. Tax Year Extraction
- Pattern: `CP2000_YYYY_DTD` from filename
- More reliable than OCR text for poor quality scans

### 4. Address Cleaning
- Removes embedded SSN patterns
- Filters IRS headers from address blocks

## Data Sources

### Original Batch (10 files)
Location: `../CP2000_extracted/CP2000/`
- CP2000 files from initial processing
- Files: ALBA, BOYD, COWAN, CUMMINGS, LUNA, MARTINEZ, NEALE, PARRISH, SANDOVAL, STEVENS

### New Batch (10 files)
Location: `../CP2000 NEW BATCH/`
- Recent CP2000 batch with joint filers
- Files: BECERRA, BRUCE, FRIES, HOOD, LYNCH, MALAVE, MARSHALL, SHENK, WARRICK, WILSON

## Output Structure

```
CP2000_Pipeline/
├── output/
│   ├── original_batch/
│   │   └── combined.json          # Original batch results
│   ├── new_batch/
│   │   └── combined.json          # New batch results
│   └── unified/
│       ├── all_cp2000_combined.json   # All batches merged
│       └── batch_summary.json         # Statistics report
├── cp2000_extractor.py            # Core extraction logic
├── process_all_batches.py         # Batch processor
└── README.md                      # This file
```

## Extracted Fields

Each record contains:
- **Letter Details**: letter_type, notice_date, tax_year
- **Primary Taxpayer**: first_name, last_name
- **Spouse** (if joint): spouse_first_name, spouse_last_name
- **Tax Info**: taxpayer_tin, taxpayer_tin_1, taxpayer_tin_2
- **Address**: address_street, address_city, address_state, address_zip, address_full
- **Financial**: amount_due, payment_deadline, penalty_amount, interest_amount
- **Raw OCR**: taxpayer_name_1, taxpayer_name_2 (for debugging)

## Known Issues & Solutions

### Issue: Joint Filers Not Parsing
**Example**: "ROBERTO MALAVE & KATHERINE A LYNCH" → only extracts last name

**Solution**: Enhanced `parse_name()` function splits on "&" or "AND"
- First person: "ROBERTO MALAVE" → first_name="Roberto Malave", last_name="Lynch"
- Spouse: "KATHERINE A LYNCH" → spouse_first_name="Katherine A", spouse_last_name="Lynch"

### Issue: C/O Lines Extracted as Names
**Example**: "C/O ELIZABETH CASTELLANOS" extracted as taxpayer

**Solution**: Skip lines starting with "C/O" in `extract_taxpayer_name_from_raw()`

### Issue: OCR Garbage Passing Validation
**Example**: "Rbertomalaer Katherea Lich" passes as valid name

**Solution**: `looks_like_real_name()` checks:
1. Mixed case patterns (case changes > 2)
2. Lowercase before uppercase (OCR artifact)
3. Consecutive consonants (5+ is suspicious)
4. Blacklist of known OCR noise words

### Issue: Poor OCR Quality on Some Scans
**Example**: Name completely garbled but filename is clear

**Solution**: Filename fallback strategy
- Extract last name from "_LASTNAME.pdf" pattern
- Extract tax year from "CP2000_YYYY_DTD" pattern
- Use OCR only when reliable

## Accuracy Metrics

### Target Accuracy (Production)
- ✅ Last Names: 100% (critical for case matching)
- ⚠️ First Names: 80%+ (joint filers may need manual review)
- ✅ Tax Years: 100% (from filename)
- ✅ Amounts: 80%+ (OCR dependent)

### Current Status (20 files total)
Results after running pipeline:
- Last Names: TBD
- First Names: TBD
- Tax Years: TBD
- Joint Filers Detected: TBD

## Usage Examples

### Example 1: Process New Batch Only
```bash
python cp2000_extractor.py "../CP2000 NEW BATCH" "output/new_batch_v2"
```

### Example 2: Process Original Batch Only
```bash
python cp2000_extractor.py "../CP2000_extracted/CP2000" "output/original_batch_v2"
```

### Example 3: Process All Batches
```bash
python process_all_batches.py
```

## Next Steps

1. **Run Pipeline**: Execute `python process_all_batches.py`
2. **Review Results**: Check `output/unified/all_cp2000_combined.json`
3. **Manual Corrections**: Identify edge cases needing manual review
4. **SSN Extraction**: Add SSN last-4 extraction for case matching
5. **Case Matching**: Integrate with Logics API for CaseID lookup

## Troubleshooting

### No PDF files found
- Check input directory path
- Ensure PDFs are in root of input folder (not subdirectories)

### Low accuracy on names
- Review `taxpayer_name_1` and `taxpayer_name_2` in output (raw OCR)
- Check if OCR quality is poor → add to noise word list
- Verify filename pattern matches expected format

### Missing tax years
- Check filename pattern: `CP2000_YYYY_DTD`
- Verify date format in filename (should have 4-digit year)

### Import errors
- Ensure running from `CP2000_Pipeline/` directory
- Check parent directory has `src/pipeline.py` and `src/document_manager.py`

## Support

For issues or questions:
1. Check `output/unified/batch_summary.json` for statistics
2. Review individual record's `taxpayer_name_1` and `taxpayer_name_2` for raw OCR
3. Compare filename vs extracted data to identify pattern issues
