#!/usr/bin/env python3
"""
Pre-Flight Setup Validation Script

Validates that all required configuration and dependencies are in place
before running the Mail Room Automation Pipeline.

Author: Hemalatha Yalamanchi
Created: October 31, 2025
Version: 1.0
"""

import os
import sys
from pathlib import Path

def print_header(text):
    """Print formatted header"""
    print("\n" + "=" * 80)
    print(f"  {text}")
    print("=" * 80)

def print_status(check, status, message=""):
    """Print check status"""
    status_icon = "✅" if status else "❌"
    print(f"{status_icon} {check:<50} {'PASS' if status else 'FAIL'}")
    if message and not status:
        print(f"   💡 {message}")

def validate_environment():
    """Validate environment configuration"""
    print_header("1️⃣  ENVIRONMENT CONFIGURATION")
    
    all_passed = True
    
    # Check .env file exists
    env_exists = Path('.env').exists()
    print_status(
        ".env file exists",
        env_exists,
        "Run: cp env.example .env and edit with your credentials"
    )
    all_passed &= env_exists
    
    if env_exists:
        from dotenv import load_dotenv
        load_dotenv()
        
        # Check required environment variables
        required_vars = {
            'LOGIQS_API_KEY': 'Logiqs CRM API key for document upload',
            'LOGIQS_SECRET_TOKEN': 'Logiqs CRM secret token',
            'LOGICS_API_KEY': 'Logics API key for case search'
        }
        
        for var, description in required_vars.items():
            value = os.getenv(var)
            has_value = bool(value and value != f'your_{var.lower()}_here')
            print_status(
                f"{var} is set",
                has_value,
                f"Set in .env: {description}"
            )
            all_passed &= has_value
    
    return all_passed

def validate_google_drive():
    """Validate Google Drive service account"""
    print_header("2️⃣  GOOGLE DRIVE SERVICE ACCOUNT")
    
    all_passed = True
    
    # Check service account file
    sa_file = Path('service-account-key.json')
    sa_exists = sa_file.exists()
    print_status(
        "service-account-key.json exists",
        sa_exists,
        "Place your Google service account JSON in project root"
    )
    all_passed &= sa_exists
    
    if sa_exists:
        try:
            import json
            with open(sa_file) as f:
                sa_data = json.load(f)
            
            # Validate structure
            required_keys = ['type', 'project_id', 'private_key', 'client_email']
            has_all_keys = all(key in sa_data for key in required_keys)
            print_status(
                "Service account JSON is valid",
                has_all_keys,
                "File structure is incomplete or corrupted"
            )
            all_passed &= has_all_keys
            
            if has_all_keys:
                print(f"   📧 Service Account: {sa_data['client_email']}")
                print(f"   📋 Project: {sa_data['project_id']}")
        except Exception as e:
            print_status("Service account JSON is valid", False, str(e))
            all_passed = False
    
    return all_passed

def validate_dependencies():
    """Validate Python dependencies"""
    print_header("3️⃣  PYTHON DEPENDENCIES")
    
    all_passed = True
    
    dependencies = {
        'requests': 'HTTP requests',
        'pandas': 'Data processing',
        'pytesseract': 'OCR functionality',
        'google.oauth2.service_account': 'Google authentication',
        'googleapiclient.discovery': 'Google Drive API',
        'cv2': 'Image processing (opencv-python)',
        'fitz': 'PDF processing (PyMuPDF)',
        'dotenv': 'Environment variables (python-dotenv)',
        'dateutil': 'Date parsing (python-dateutil)'
    }
    
    for module, description in dependencies.items():
        try:
            if module == 'google.oauth2.service_account':
                from google.oauth2 import service_account
            elif module == 'googleapiclient.discovery':
                from googleapiclient.discovery import build
            elif module == 'cv2':
                import cv2
            elif module == 'fitz':
                import fitz
            elif module == 'dotenv':
                from dotenv import load_dotenv
            elif module == 'dateutil':
                from dateutil import parser
            else:
                __import__(module)
            
            print_status(f"{module:<30}", True)
        except ImportError:
            print_status(
                f"{module:<30}",
                False,
                f"Install: pip install -r requirements.txt ({description})"
            )
            all_passed = False
    
    return all_passed

def validate_directories():
    """Validate required directories"""
    print_header("4️⃣  DIRECTORY STRUCTURE")
    
    all_passed = True
    
    directories = [
        'DAILY_REPORTS/MATCHED',
        'DAILY_REPORTS/UNMATCHED',
        'UPLOAD_RESULTS',
        'UPLOAD_READY'
    ]
    
    for directory in directories:
        dir_path = Path(directory)
        exists = dir_path.exists()
        
        if not exists:
            try:
                dir_path.mkdir(parents=True, exist_ok=True)
                print_status(f"{directory:<40}", True, "Created")
            except Exception as e:
                print_status(f"{directory:<40}", False, str(e))
                all_passed = False
        else:
            print_status(f"{directory:<40}", True)
    
    return all_passed

def test_service_account_auth():
    """Test service account authentication"""
    print_header("5️⃣  GOOGLE DRIVE AUTHENTICATION TEST")
    
    try:
        from google.oauth2 import service_account
        from googleapiclient.discovery import build
        
        creds = service_account.Credentials.from_service_account_file(
            'service-account-key.json',
            scopes=['https://www.googleapis.com/auth/drive.readonly']
        )
        
        service = build('drive', 'v3', credentials=creds)
        print_status("Service account authentication", True)
        print("   💡 Remember to share Google Drive folders with:")
        
        # Get service account email
        with open('service-account-key.json') as f:
            import json
            sa_email = json.load(f)['client_email']
        print(f"      {sa_email}")
        
        return True
        
    except FileNotFoundError:
        print_status("Service account authentication", False, "service-account-key.json not found")
        return False
    except Exception as e:
        print_status("Service account authentication", False, str(e))
        return False

def main():
    """Run all validation checks"""
    print("\n" + "╔" + "═" * 78 + "╗")
    print("║" + " " * 78 + "║")
    print("║" + "  CP2000 MAIL ROOM AUTOMATION - PRE-FLIGHT VALIDATION".center(78) + "║")
    print("║" + " " * 78 + "║")
    print("╚" + "═" * 78 + "╝")
    
    results = []
    
    # Run all validations
    results.append(("Environment", validate_environment()))
    results.append(("Google Drive", validate_google_drive()))
    results.append(("Dependencies", validate_dependencies()))
    results.append(("Directories", validate_directories()))
    
    # Test authentication if other checks passed
    if all(r[1] for r in results):
        results.append(("Authentication", test_service_account_auth()))
    else:
        print_header("5️⃣  GOOGLE DRIVE AUTHENTICATION TEST")
        print("⏭️  Skipped - Fix above errors first")
    
    # Final summary
    print_header("📊 VALIDATION SUMMARY")
    
    for check, passed in results:
        print_status(check, passed)
    
    all_passed = all(r[1] for r in results)
    
    if all_passed:
        print("\n" + "=" * 80)
        print("✅ ALL CHECKS PASSED - READY FOR PRODUCTION!")
        print("=" * 80)
        print("\n🚀 Next Steps:")
        print("   1. Test with 2 files: python3 daily_pipeline_orchestrator.py --test --limit=2")
        print("   2. Review test results in DAILY_REPORTS/")
        print("   3. Run full pipeline: python3 daily_pipeline_orchestrator.py")
        print("=" * 80)
        return 0
    else:
        print("\n" + "=" * 80)
        print("❌ VALIDATION FAILED - Please fix the errors above")
        print("=" * 80)
        print("\n📚 Documentation:")
        print("   • Quick Start: QUICK_START_SERVICE_ACCOUNT.md")
        print("   • Setup Guide: SERVICE_ACCOUNT_SETUP.md")
        print("   • Full README: README.md")
        print("=" * 80)
        return 1

if __name__ == "__main__":
    sys.exit(main())

