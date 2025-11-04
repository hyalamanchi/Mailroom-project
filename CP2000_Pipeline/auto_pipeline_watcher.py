#!/usr/bin/env python3
"""
AUTO PIPELINE WATCHER
Automatically triggers the CP2000 pipeline when new files are detected.

FEATURES:
- Monitors Google Drive folder for new PDF files
- Automatically runs case extraction and matching
- Generates updated Google Sheets with matched/unmatched cases
- Runs every 5 minutes (configurable)
- Logs all activities

USAGE:
    python3 auto_pipeline_watcher.py
    python3 auto_pipeline_watcher.py --interval 300  # Check every 5 minutes
    python3 auto_pipeline_watcher.py --once  # Run once then exit

Author: Assistant
Date: November 2024
"""

import os
import sys
import time
import json
import subprocess
import argparse
from datetime import datetime
from pathlib import Path
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

class AutoPipelineWatcher:
    """Watches for new files and automatically triggers the pipeline"""
    
    def __init__(self, check_interval=300):
        self.check_interval = check_interval  # seconds
        self.state_file = 'pipeline_watcher_state.json'
        self.log_file = 'pipeline_watcher.log'
        self.processed_files = self.load_state()
        
        # Google Drive folder to monitor
        self.drive_folder_id = '18e8lj66Mdr7PFGhJ7ySYtsnkNgiuczmx'
        
        # Initialize Google Drive
        self.drive_service = self.init_google_drive()
    
    def init_google_drive(self):
        """Initialize Google Drive API"""
        try:
            creds = Credentials.from_authorized_user_file('token.json')
            service = build('drive', 'v3', credentials=creds)
            self.log("✅ Connected to Google Drive")
            return service
        except Exception as e:
            self.log(f"❌ Failed to connect to Google Drive: {e}")
            return None
    
    def load_state(self):
        """Load the last processed state"""
        if os.path.exists(self.state_file):
            with open(self.state_file, 'r') as f:
                return json.load(f)
        return {'last_check': None, 'processed_file_ids': []}
    
    def save_state(self):
        """Save the current state"""
        self.processed_files['last_check'] = datetime.now().isoformat()
        with open(self.state_file, 'w') as f:
            json.dump(self.processed_files, f, indent=2)
    
    def log(self, message):
        """Log message to console and file"""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        log_message = f"[{timestamp}] {message}"
        print(log_message)
        
        with open(self.log_file, 'a') as f:
            f.write(log_message + '\n')
    
    def check_for_new_files(self):
        """Check Google Drive for new PDF files"""
        if not self.drive_service:
            self.log("⚠️  No Drive connection, skipping check")
            return []
        
        try:
            # Search for PDF files in the monitored folder
            query = f"'{self.drive_folder_id}' in parents and trashed=false and mimeType='application/pdf'"
            
            results = self.drive_service.files().list(
                q=query,
                fields='files(id, name, createdTime, modifiedTime)',
                orderBy='createdTime desc',
                pageSize=100
            ).execute()
            
            all_files = results.get('files', [])
            
            # Filter for new files (not in processed list)
            processed_ids = set(self.processed_files.get('processed_file_ids', []))
            new_files = [f for f in all_files if f['id'] not in processed_ids]
            
            if new_files:
                self.log(f"🆕 Found {len(new_files)} new file(s)")
                for file in new_files:
                    self.log(f"   - {file['name']}")
            else:
                self.log(f"✅ No new files (checked {len(all_files)} total files)")
            
            return new_files
            
        except Exception as e:
            self.log(f"❌ Error checking for new files: {e}")
            return []
    
    def run_pipeline(self):
        """Execute the full CP2000 pipeline"""
        self.log("🚀 Starting pipeline execution...")
        
        try:
            # Step 1: Run case extraction and matching
            self.log("  📄 Running case extraction...")
            result = subprocess.run(
                ['python3', 'case_id_extractor.py'],
                capture_output=True,
                text=True,
                timeout=1800  # 30 minute timeout
            )
            
            if result.returncode != 0:
                self.log(f"  ❌ Case extraction failed: {result.stderr}")
                return False
            
            self.log("  ✅ Case extraction completed")
            
            # Step 2: Generate review workbook
            self.log("  📊 Generating review workbook...")
            result = subprocess.run(
                ['python3', 'create_review_workbook.py'],
                capture_output=True,
                text=True,
                timeout=600  # 10 minute timeout
            )
            
            if result.returncode != 0:
                self.log(f"  ❌ Workbook generation failed: {result.stderr}")
                return False
            
            self.log("  ✅ Review workbook created")
            
            # Extract the spreadsheet URL from output
            for line in result.stdout.split('\n'):
                if 'https://docs.google.com/spreadsheets/' in line:
                    self.log(f"  🔗 {line.strip()}")
            
            return True
            
        except subprocess.TimeoutExpired:
            self.log("  ❌ Pipeline execution timed out")
            return False
        except Exception as e:
            self.log(f"  ❌ Pipeline execution error: {e}")
            return False
    
    def mark_files_processed(self, files):
        """Mark files as processed"""
        for file in files:
            if file['id'] not in self.processed_files['processed_file_ids']:
                self.processed_files['processed_file_ids'].append(file['id'])
        self.save_state()
    
    def watch(self, run_once=False):
        """Main watch loop"""
        self.log("="*70)
        self.log("🔍 AUTO PIPELINE WATCHER STARTED")
        self.log(f"   Check interval: {self.check_interval} seconds")
        self.log(f"   Monitoring folder: {self.drive_folder_id}")
        self.log(f"   Mode: {'One-time' if run_once else 'Continuous'}")
        self.log("="*70)
        
        iteration = 0
        
        while True:
            iteration += 1
            self.log(f"\n--- Check #{iteration} ---")
            
            # Check for new files
            new_files = self.check_for_new_files()
            
            if new_files:
                # Run the pipeline
                success = self.run_pipeline()
                
                if success:
                    # Mark files as processed
                    self.mark_files_processed(new_files)
                    self.log("✅ Pipeline completed successfully")
                else:
                    self.log("⚠️  Pipeline had errors, will retry on next check")
            
            # Save state
            self.save_state()
            
            # Exit if running once
            if run_once:
                self.log("\n🏁 One-time run completed")
                break
            
            # Wait for next check
            self.log(f"\n💤 Sleeping for {self.check_interval} seconds...")
            time.sleep(self.check_interval)


def main():
    parser = argparse.ArgumentParser(description='Auto Pipeline Watcher')
    parser.add_argument('--interval', type=int, default=300,
                        help='Check interval in seconds (default: 300)')
    parser.add_argument('--once', action='store_true',
                        help='Run once then exit (default: continuous)')
    
    args = parser.parse_args()
    
    # Create watcher
    watcher = AutoPipelineWatcher(check_interval=args.interval)
    
    try:
        watcher.watch(run_once=args.once)
    except KeyboardInterrupt:
        watcher.log("\n\n🛑 Watcher stopped by user")
        sys.exit(0)
    except Exception as e:
        watcher.log(f"\n\n❌ Fatal error: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()

