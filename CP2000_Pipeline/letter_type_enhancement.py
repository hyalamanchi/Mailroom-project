"""
Enhanced Letter Type Detection - To be integrated into hundred_percent_accuracy_extractor.py

This module provides comprehensive IRS letter type detection for all common notice types.
"""

import re
from typing import Optional

# Enhanced letter patterns for ALL IRS notice types
ENHANCED_LETTER_PATTERNS = [
    # Specific patterns first (most common IRS notices)
    r'(?:Notice|Letter|Form)\s+(CP\s*2000)\b',  # CP2000 with context (highest priority)
    r'\b(CP\s*2000)\b',                          # CP2000 - Underreported Income
    r'\b(CP\s*2501)\b',                          # CP2501 - Underreported Income (simplified)
    r'\b(CP\s*3219[A-Z]?)\b',                    # CP3219/CP3219A - Notice of Deficiency
    r'\b(CP\s*504)\b',                           # CP504 - Intent to Levy
    r'\b(CP\s*566)\b',                           # CP566 - AUR Response
    r'\b(CP\s*14)\b',                            # CP14 - Unpaid Taxes
    r'\b(CP\s*501)\b',                           # CP501 - Balance Due Reminder
    r'\b(CP\s*503)\b',                           # CP503 - Urgent Balance Due
    r'\b(CP\s*505)\b',                           # CP505 - Federal Tax Lien Intent
    r'\b(CP\s*71[A-Z]?)\b',                      # CP71/CP71A - Annual Reminder
    r'\b(CP\s*90)\b',                            # CP90 - Final Notice of Intent to Levy
    r'\b(CP\s*91)\b',                            # CP91 - Final Notice FICA
    r'\b(CP\s*92)\b',                            # CP92 - Notice of Levy on SSA
    r'\b(CP\s*297)\b',                           # CP297 - We Removed Lien
    r'\b(LTR\s*3172)\b',                         # LTR3172 - Potential Third Party Contact
    r'\b(LT\s*11)\b',                            # LT11/LTR11 - Final Notice
    r'\b(LTR\s*11)\b',                           # LTR11 (full format)
    r'\b(LT\s*1058)\b',                          # LT1058/LTR1058 - Final Notice Intent to Levy
    r'\b(LTR\s*1058)\b',                         # LTR1058 (full format)
    r'\b(LTR\s*226[J]?)\b',                      # LTR226/226J - Disallowed Refund
    r'\b(FORM\s*4549)\b',                        # Form 4549 - Income Tax Examination Changes
    r'\b(FORM\s*668[A-Z]?)\b',                   # Form 668 - Notice of Levy
    # Generic patterns (fallback - must be last)
    r'\b(CP\s*\d{3,4})\b',                       # Any CP code
    r'\b(LT\s*\d{4})\b',                         # Any LT code
    r'\b(LTR\s*\d{4})\b',                        # Any LTR code
]

# Known valid IRS letter types
VALID_LETTER_TYPES = {
    'CP2000', 'CP2501', 'CP3219', 'CP3219A', 'CP504', 'CP566',
    'CP14', 'CP501', 'CP503', 'CP505', 'CP71', 'CP71A', 'CP90', 'CP91', 'CP92', 'CP297',
    'LTR3172', 'LT11', 'LTR11', 'LT1058', 'LTR1058', 'LTR226', 'LTR226J',
    'FORM4549', 'FORM668', 'FORM668A'
}

def extract_letter_type_enhanced(text: str, letter_patterns: list) -> Optional[str]:
    """
    Extract letter type with support for ALL IRS notice types
    
    Args:
        text: OCR text from the document
        letter_patterns: List of regex patterns to try
        
    Returns:
        Detected letter type or None
    """
    # Try patterns in priority order
    for pattern in letter_patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        if matches:
            letter_type = re.sub(r'\s+', '', matches[0].upper())
            
            # Common OCR error corrections for CP2000
            if letter_type in ['CP7000', 'CP0000', 'CPOOO0', 'CP2900', 'CP29OO', 'CP20O0']:
                print(f"    ⚠️  OCR error detected: {letter_type} -> correcting to CP2000")
                letter_type = 'CP2000'
            
            # Normalize letter types
            letter_type = normalize_letter_type(letter_type)
            
            # Validate it's a known IRS letter type
            if is_valid_letter_type(letter_type):
                print(f"    📄 Letter type detected: {letter_type}")
                return letter_type
            else:
                print(f"    ⚠️  Unknown letter type: {letter_type} (will use as-is)")
                return letter_type  # Still return it, might be valid
    
    return None

def normalize_letter_type(letter_type: str) -> str:
    """Normalize letter type format"""
    # Remove spaces
    letter_type = re.sub(r'\s+', '', letter_type.upper())
    
    # Normalize LT to LTR
    if letter_type.startswith('LT') and not letter_type.startswith('LTR'):
        if re.match(r'LT\d+', letter_type):
            letter_type = 'LTR' + letter_type[2:]
    
    return letter_type

def is_valid_letter_type(letter_type: str) -> bool:
    """Check if letter type is in known valid types"""
    # Direct match
    if letter_type in VALID_LETTER_TYPES:
        return True
    
    # Check if it matches known patterns
    if re.match(r'CP\d{2,4}[A-Z]?$', letter_type):
        return True
    if re.match(r'LTR\d{4}[A-Z]?$', letter_type):
        return True
    if re.match(r'FORM\d{4}[A-Z]?$', letter_type):
        return True
    
    return False

# Example usage and testing
if __name__ == "__main__":
    test_texts = [
        "This is a CP2000 Notice",
        "You received a CP2501 letter",
        "Notice LTR3172",
        "Form 4549",
        "CP566 response required",
        "Final Notice LT1058",
    ]
    
    print("Testing enhanced letter type detection:")
    print("=" * 60)
    for text in test_texts:
        result = extract_letter_type_enhanced(text, ENHANCED_LETTER_PATTERNS)
        print(f"Text: '{text}' -> {result}")
        print()

