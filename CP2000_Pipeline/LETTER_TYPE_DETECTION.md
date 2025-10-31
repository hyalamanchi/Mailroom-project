# Letter Type Detection System

**Author:** Hemalatha Yalamanchi  
**Last Updated:** October 31, 2025  
**Status:** Production Ready

---

## Overview

The Mail Room Pipeline now supports **automatic detection of ALL IRS letter types**, not just CP2000. This enables processing multiple types of IRS notices in a single Google Drive folder with accurate classification and naming.

---

## Supported Letter Types

### CP Series (Computerized Paragraph Notices)

| Code | Description | Purpose |
|------|-------------|---------|
| **CP2000** | Underreported Income | Most common - income mismatch |
| **CP2501** | Underreported Income (Simplified) | Similar to CP2000 but simpler |
| **CP3219/CP3219A** | Notice of Deficiency | 90-day letter to Tax Court |
| **CP504** | Intent to Levy | Final notice before levy |
| **CP566** | AUR Response | Additional Underreported  Income response |
| **CP14** | Unpaid Taxes | Balance due notice |
| **CP501** | Balance Due Reminder | First reminder |
| **CP503** | Urgent Balance Due | Second reminder |
| **CP505** | Tax Lien Intent | Before filing lien |
| **CP71/CP71A** | Annual Reminder | Yearly balance notification |
| **CP90** | Final Notice Intent to Levy | Last warning |
| **CP91** | Final Notice FICA | FICA taxes |
| **CP92** | Notice of Levy on SSA | Social Security levy |
| **CP297** | Lien Removal | We removed your lien |

### LTR Series (Letter Notices)

| Code | Description |
|------|-------------|
| **LTR3172** | Potential Third Party Contact |
| **LTR11** | Final Notice Before Levy |
| **LTR1058** | Final Notice Intent to Levy |
| **LTR226/LTR226J** | Disallowed Refund/Credit |
| **LTR525** | General 30-day Letter |

### Form Series

| Code | Description |
|------|-------------|
| **FORM4549** | Income Tax Examination Changes |
| **FORM668/668A** | Notice of Federal Tax Lien |

### Generic Fallback

- Any `CP` followed by 3-4 digits (e.g., CP123, CP1234)
- Any `LTR` followed by 4 digits (e.g., LTR9999)
- Any `FORM` followed by 4 digits (e.g., FORM8888)

---

## How It Works

### 1. Detection Process

```
PDF → OCR Text Extraction → Pattern Matching → Error Correction 
→ Normalization → Validation → Letter Type
```

### 2. Pattern Matching (Priority Order)

1. **Specific Patterns First**
   - Looks for exact codes: CP2000, CP2501, LTR3172, etc.
   - Highest confidence

2. **Context-Aware Patterns**
   - "Notice CP2000", "Letter LTR3172", etc.
   - Adds context validation

3. **Generic Patterns (Fallback)**
   - Any CP####, LTR####, FORM####
   - Catches unknown types

### 3. OCR Error Correction

Automatically fixes common OCR misreads:

| Detected | Corrected To | Reason |
|----------|--------------|--------|
| CP7000 | CP2000 | 2 misread as 7 |
| CP0000 | CP2000 | 2 misread as 0 |
| CP2900 | CP2000 | 0 misread as 9 |
| CP20O0 | CP2000 | 0 misread as O |

### 4. Normalization

Standardizes format:
- `LT1058` → `LTR1058` (adds R)
- `CP 2000` → `CP2000` (removes spaces)
- `cp2000` → `CP2000` (uppercase)

### 5. Validation

Checks if letter type matches known IRS patterns:
- Direct match with known types
- Pattern validation (`CP\d{2,4}`, `LTR\d{4}`, etc.)
- Returns validated letter type

---

## Code Implementation

### Main Function: `extract_letter_type()`

Location: `hundred_percent_accuracy_extractor.py`

```python
def extract_letter_type(self, text: str) -> Optional[str]:
    """Extract letter type with support for ALL IRS notice types"""
    
    # Try patterns in priority order
    for pattern in self.letter_patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        if matches:
            letter_type = re.sub(r'\s+', '', matches[0].upper())
            
            # OCR error corrections
            if letter_type in ['CP7000', 'CP0000', 'CP2900', ...]:
                letter_type = 'CP2000'
            
            # Normalize and validate
            letter_type = self._normalize_letter_type(letter_type)
            
            if self._is_valid_letter_type(letter_type):
                print(f"    📄 Letter type detected: {letter_type}")
                return letter_type
    
    return None
```

### Helper Functions

**Normalization:**
```python
def _normalize_letter_type(self, letter_type: str) -> str:
    """Standardizes letter type format"""
    letter_type = re.sub(r'\s+', '', letter_type.upper())
    
    # LT to LTR
    if letter_type.startswith('LT') and not letter_type.startswith('LTR'):
        if re.match(r'LT\d+', letter_type):
            letter_type = 'LTR' + letter_type[2:]
    
    return letter_type
```

**Validation:**
```python
def _is_valid_letter_type(self, letter_type: str) -> bool:
    """Validates against known IRS patterns"""
    valid_types = {
        'CP2000', 'CP2501', 'LTR3172', ...
    }
    
    if letter_type in valid_types:
        return True
    
    # Pattern validation
    if re.match(r'CP\d{2,4}[A-Z]?$', letter_type):
        return True
    # ... more patterns
    
    return False
```

---

## Usage Examples

### Example 1: Mixed Letter Types in Folder

**Google Drive Folder Contains:**
```
SMITH_CP2000_2023.pdf
JONES_CP2501_2022.pdf
BROWN_LTR3172_2023.pdf
DAVIS_CP566_2021.pdf
WILSON_FORM4549_2022.pdf
```

**Pipeline Output:**
```
Processing SMITH_CP2000_2023.pdf...
   📄 Letter type detected: CP2000

Processing JONES_CP2501_2022.pdf...
   📄 Letter type detected: CP2501

Processing BROWN_LTR3172_2023.pdf...
   📄 Letter type detected: LTR3172

Processing DAVIS_CP566_2021.pdf...
   📄 Letter type detected: CP566

Processing WILSON_FORM4549_2022.pdf...
   📄 Letter type detected: FORM4549
```

### Example 2: Generated Filenames

**Naming Convention:** `IRS_CORR_{Letter Type}_{Tax Year}_DTD {Date}_{Last Name}.pdf`

**Results:**
```
IRS_CORR_CP2000_2023_DTD 05.06.2024_SMITH.pdf
IRS_CORR_CP2501_2022_DTD 03.15.2024_JONES.pdf
IRS_CORR_LTR3172_2023_DTD 06.01.2024_BROWN.pdf
IRS_CORR_CP566_2021_DTD 04.20.2024_DAVIS.pdf
IRS_CORR_FORM4549_2022_DTD 07.10.2024_WILSON.pdf
```

### Example 3: OCR Error Correction

**OCR Reads:** "This is a CP7000 Notice"  
**Pipeline Detects:** CP7000  
**Pipeline Corrects:** CP2000  
**Output:** `Letter type detected: CP2000`

---

## Testing

### Quick Test

```bash
cd "/Users/hemalathayalamanchi/Desktop/logicscase integration/CP2000_Pipeline"
python3 daily_pipeline_orchestrator.py --test --limit=5
```

### Create Test Files

Upload PDFs with these naming patterns to your Google Drive folder:
- `CP2000_TEST_2023.pdf`
- `CP2501_SAMPLE_2022.pdf`
- `LTR3172_NOTICE_2023.pdf`
- `CP566_RESPONSE_2021.pdf`

### Verify Detection

Check terminal output for:
```
📄 Letter type detected: CP2501
📄 Letter type detected: LTR3172
📄 Letter type detected: CP566
```

Check JSON/Excel reports for correct `letter_type` field.

---

## Key Benefits

### ✅ Multi-Type Support
- Process CP2000, CP2501, LTR3172, etc. in same folder
- No manual sorting required

### ✅ Accurate Classification
- Smart pattern matching with priority order
- OCR error correction for common misreads

### ✅ Proper Naming
- Generates correct filenames for each letter type
- Maintains professional naming convention

### ✅ Future-Proof
- Generic fallback patterns catch unknown types
- Easy to add new letter types

### ✅ Better Organization
- Sort and filter by actual letter type
- Track metrics per letter type
- Accurate reporting to Logiqs

---

## Integration with Pipeline

### Files Updated

1. **hundred_percent_accuracy_extractor.py**
   - Enhanced `extract_letter_type()` function
   - Added `_normalize_letter_type()` helper
   - Added `_is_valid_letter_type()` validator

2. **production_extractor.py**
   - Uses enhanced letter type detection
   - Passes letter type to results

3. **generate_upload_list.py**
   - Uses detected letter type in naming convention
   - Defaults to CP2000 if not detected

4. **daily_pipeline_orchestrator.py**
   - Reports letter type statistics
   - Groups by letter type

---

## Reference

See `letter_type_enhancement.py` for:
- Complete list of patterns
- Testing functions
- Usage examples
- Pattern documentation

---

## Troubleshooting

### Issue: Letter Type Not Detected

**Symptoms:**
- Terminal shows no "Letter type detected" message
- Results show `letter_type: null` or missing

**Solutions:**
1. Check if PDF has OCR text (might be image-only)
2. Verify letter type appears in document
3. Check filename for letter type clues
4. Review `letter_patterns` for missing pattern

### Issue: Wrong Letter Type Detected

**Symptoms:**
- CP2501 detected as CP2000
- LT1058 not normalized to LTR1058

**Solutions:**
1. Check OCR quality (may need re-scan)
2. Verify pattern priority in `letter_patterns`
3. Add specific correction to OCR error list
4. Update normalization rules

### Issue: Unknown Letter Type

**Symptoms:**
- Terminal shows "Letter type detected (unknown): CP999"
- New IRS notice type

**Solutions:**
1. Add pattern to `letter_patterns` list
2. Add to `valid_types` set
3. Update documentation
4. Test with sample file

---

## Future Enhancements

### Planned Features

1. **Filename Fallback**
   - Extract letter type from filename if OCR fails
   - Already implemented in `production_extractor.py`

2. **Confidence Scoring**
   - Rate detection confidence (high/medium/low)
   - Flag low-confidence detections for review

3. **Multi-Page Validation**
   - Check letter type on multiple pages
   - Ensure consistency

4. **Letter Type Statistics**
   - Track frequency of each letter type
   - Generate breakdown reports

---

## Contact

For questions or issues with letter type detection:

**Author:** Hemalatha Yalamanchi  
**Project:** Mail Room Automation Pipeline  
**Repository:** https://github.com/hyalamanchi/Mailroom-project

---

**Last Updated:** October 31, 2025  
**Version:** 2.0 - Multi-Type Support

