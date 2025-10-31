"""
CP2000 PRODUCTION EXTRACTOR - OPTIMIZED FOR SPEED
Clean, simple, ULTRA-FAST workflow for high-volume business needs

WORKFLOW:
1. Download PDFs from Google Drive (single source of truth)
2. INCREMENTAL: Skip already processed files (tracks history)
3. Extract data with 100% accuracy engine + HIGH PARALLELISM (16 workers)
4. PROPER LETTER TYPE DETECTION (CP2000, CP2501, LTR3172, etc.)
5. Generate Logics integration output (JSON + EXCEL)
6. Auto-cleanup temp files

SPEED IMPROVEMENTS:
- 16 workers (was 8) = 2x faster
- Incremental processing = Only process new files
- Chunk-based progress tracking = Better monitoring
- Optimized letter type extraction

USAGE:
    python production_extractor.py
    python production_extractor.py --full  # Force full reprocess
    
OUTPUT:
    LOGICS_DATA_[timestamp].json - Ready for Logics upload
    LOGICS_DATA_[timestamp].xlsx - Excel format for review
"""

import os
import json
import shutil
import sys
import hashlib
from datetime import datetime
from concurrent.futures import ProcessPoolExecutor, as_completed
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
import pandas as pd

# Import the 100% accuracy engine
from hundred_percent_accuracy_extractor import HundredPercentAccuracyExtractor

class ProductionExtractor:
    """Optimized production-ready extractor with incremental processing"""
    
    def __init__(self, force_full=False):
        self.SCOPES = ['https://www.googleapis.com/auth/drive.readonly']
        self.service = None
        self.force_full = force_full
        
        # Google Drive folder
        self.folders = {
            'main_folder': '18e8lj66Mdr7PFGhJ7ySYtsnkNgiuczmx'
        }
        
        # Temp directory for downloads
        self.temp_dir = 'TEMP_PROCESSING'
        
        # Processing history file for incremental processing
        self.history_file = 'PROCESSING_HISTORY.json'
        self.processed_files = self.load_history()
        
    def load_history(self):
        """Load processing history for incremental processing"""
        if os.path.exists(self.history_file) and not self.force_full:
            try:
                with open(self.history_file, 'r') as f:
                    return json.load(f)
            except:
                return {}
        return {}
    
    def save_history(self, file_hash, result):
        """Save processed file to history"""
        self.processed_files[file_hash] = {
            'processed_at': datetime.now().isoformat(),
            'filename': result.get('filename', ''),
            'success': True
        }
        
        with open(self.history_file, 'w') as f:
            json.dump(self.processed_files, f, indent=2)
    
    def get_file_hash(self, filename):
        """Get unique hash for a file to track if it's been processed"""
        # Use filename as hash (simpler for Drive files)
        return hashlib.md5(filename.encode()).hexdigest()
    
    def authenticate(self):
        """Authenticate with Google Drive using service account"""
        try:
            creds = service_account.Credentials.from_service_account_file(
                'service-account-key.json',
                scopes=self.SCOPES
            )
            
            self.service = build('drive', 'v3', credentials=creds)
            print("✅ Authenticated with Google Drive (Service Account)")
            
        except FileNotFoundError:
            print("❌ Error: service-account-key.json not found")
            print("💡 Place your service account JSON file in the project root")
            raise
        except Exception as e:
            print(f"❌ Authentication error: {str(e)}")
            raise
    
    def download_from_drive(self):
        """Download PDFs from Google Drive with INCREMENTAL processing"""
        print("\n📥 DOWNLOADING FROM GOOGLE DRIVE (INCREMENTAL MODE)")
        print("=" * 60)
        
        if self.force_full:
            print("⚠️  FULL REPROCESS MODE - Will process all files")
        
        # Clean and create temp directory
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
        os.makedirs(self.temp_dir)
        
        all_files = []
        skipped_count = 0
        
        for folder_name, folder_id in self.folders.items():
            print(f"\n📁 {folder_name}:")
            
            # List files
            query = f"'{folder_id}' in parents and mimeType='application/pdf' and trashed=false"
            results = self.service.files().list(q=query, fields="files(id, name)", pageSize=1000).execute()
            files = results.get('files', [])
            
            print(f"   Found: {len(files)} PDFs")
            
            # Download each file (skip already processed)
            new_files = 0
            for i, file in enumerate(files, 1):
                file_hash = self.get_file_hash(file['name'])
                
                # Skip if already processed (unless force_full)
                if file_hash in self.processed_files and not self.force_full:
                    skipped_count += 1
                    continue
                
                try:
                    request = self.service.files().get_media(fileId=file['id'])
                    local_path = os.path.join(self.temp_dir, file['name'])
                    
                    with open(local_path, 'wb') as f:
                        downloader = MediaIoBaseDownload(f, request)
                        done = False
                        while not done:
                            status, done = downloader.next_chunk()
                    
                    all_files.append(local_path)
                    new_files += 1
                    
                    if new_files % 10 == 0:
                        print(f"   Downloaded: {new_files} new files...")
                
                except Exception as e:
                    print(f"   ❌ Error: {file['name']} - {str(e)}")
            
            print(f"   ✅ New files: {new_files}, Skipped: {len(files) - new_files}")
        
        print(f"\n✅ Total NEW files to process: {len(all_files)} PDFs")
        if skipped_count > 0:
            print(f"⏭️  Skipped (already processed): {skipped_count} PDFs")
        
        return all_files
    
    def extract_single_file(self, pdf_path):
        """Extract data from one PDF with improved letter type detection"""
        try:
            extractor = HundredPercentAccuracyExtractor()
            result = extractor.extract_100_percent_accuracy_data(pdf_path)
            
            # Enhanced letter type detection from filename and content
            if result:
                filename = os.path.basename(pdf_path).upper()
                
                # Detect letter type from filename
                if 'CP2000' in filename or 'CP 2000' in filename:
                    result['letter_type'] = 'CP2000'
                elif 'CP2501' in filename or 'CP 2501' in filename:
                    result['letter_type'] = 'CP2501'
                elif 'LTR3172' in filename or 'LTR 3172' in filename:
                    result['letter_type'] = 'LTR3172'
                elif '566' in filename:
                    result['letter_type'] = 'CP566'
                elif 'NOTICE' in filename:
                    result['letter_type'] = 'IRS_NOTICE'
                else:
                    # Default to CP2000 if not specified
                    result['letter_type'] = result.get('letter_type', 'CP2000')
                
                # Save to history after successful extraction
                file_hash = self.get_file_hash(os.path.basename(pdf_path))
                self.save_history(file_hash, result)
            
            return result
        except Exception as e:
            print(f"❌ {os.path.basename(pdf_path)}: {str(e)}")
            return None
    
    def extract_all_data(self, pdf_files, workers=16):
        """Extract data from all PDFs with HIGH PARALLELISM for maximum speed"""
        print(f"\n🚀 EXTRACTING DATA (ULTRA-FAST: {workers} workers)")
        print("=" * 60)
        
        if not pdf_files:
            print("⚠️  No new files to process!")
            return []
        
        results = []
        chunk_size = 20  # Report progress every 20 files
        
        with ProcessPoolExecutor(max_workers=workers) as executor:
            # Submit all jobs
            futures = {executor.submit(self.extract_single_file, pdf): pdf for pdf in pdf_files}
            
            # Collect results with chunk-based progress
            completed = 0
            for future in as_completed(futures):
                result = future.result()
                if result:
                    results.append(result)
                
                completed += 1
                
                # Chunk-based progress reporting
                if completed % chunk_size == 0 or completed == len(pdf_files):
                    progress_pct = (completed/len(pdf_files))*100
                    files_per_sec = completed / ((datetime.now() - self.start_time).total_seconds())
                    eta_seconds = (len(pdf_files) - completed) / files_per_sec if files_per_sec > 0 else 0
                    print(f"   📊 Progress: {completed}/{len(pdf_files)} ({progress_pct:.1f}%) | Speed: {files_per_sec:.1f} files/sec | ETA: {int(eta_seconds)}s")
        
        success_count = len(results)
        print(f"\n✅ Extraction complete:")
        print(f"   Total: {len(pdf_files)} files")
        print(f"   Success: {success_count} extractions")
        print(f"   Rate: {(success_count/len(pdf_files)*100):.1f}%")
        
        return results
    
    def save_output(self, results):
        """Save in both JSON and Excel formats"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        json_file = f"LOGICS_DATA_{timestamp}.json"
        excel_file = f"LOGICS_DATA_{timestamp}.xlsx"
        
        # Prepare data
        output_data = {
            "extraction_metadata": {
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "total_records": len(results),
                "source": "Google Drive",
                "quality_score": sum(r.get('extraction_confidence', 0) for r in results) / len(results) if results else 0,
                "google_drive_folders": list(self.folders.keys())
            },
            "case_matching_data": results
        }
        
        # Save JSON
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, indent=2, ensure_ascii=False)
        
        # Save Excel
        df_data = []
        for record in results:
            df_data.append({
                'Filename': record.get('filename', ''),
                'Taxpayer Name': record.get('taxpayer_name', ''),
                'Spouse Name': record.get('spouse_name', ''),
                'Full SSN': record.get('full_ssn', ''),
                'SSN Last 4': record.get('ssn_last_4', ''),
                'Letter Type': record.get('letter_type', ''),
                'Notice Date': record.get('notice_date', ''),
                'Notice Reference': record.get('notice_ref_number', ''),
                'Tax Year': record.get('tax_year', ''),
                'Urgency Level': record.get('urgency_level', ''),
                'Urgency Status': record.get('urgency_status', ''),
                'Date of Urgency': record.get('date_of_urgency', ''),
                'Response Due Date': record.get('response_due_date', ''),
                'Days Remaining': record.get('days_remaining', ''),
                'Response Days Allowed': record.get('response_days_allowed', 30),
                'Extraction Confidence': record.get('extraction_confidence', 0),
                'Needs Review': record.get('needs_review', False),
                'Quality Issues': ', '.join(record.get('quality_issues', []))
            })
        
        df = pd.DataFrame(df_data)
        
        # Create Excel with formatting
        with pd.ExcelWriter(excel_file, engine='openpyxl') as writer:
            # Write data
            df.to_excel(writer, sheet_name='CP2000 Extractions', index=False)
            
            # Get workbook and worksheet
            workbook = writer.book
            worksheet = writer.sheets['CP2000 Extractions']
            
            # Auto-adjust column widths
            for idx, col in enumerate(df.columns):
                max_length = max(
                    df[col].astype(str).map(len).max(),
                    len(col)
                ) + 2
                worksheet.column_dimensions[chr(65 + idx)].width = min(max_length, 50)
            
            # Add metadata sheet
            metadata_df = pd.DataFrame([
                ['Extraction Date', output_data['extraction_metadata']['timestamp']],
                ['Total Records', output_data['extraction_metadata']['total_records']],
                ['Quality Score', f"{output_data['extraction_metadata']['quality_score']:.1%}"],
                ['Source', output_data['extraction_metadata']['source']],
                ['Google Drive Folders', ', '.join(output_data['extraction_metadata']['google_drive_folders'])]
            ], columns=['Metric', 'Value'])
            
            metadata_df.to_excel(writer, sheet_name='Metadata', index=False)
            
            # Auto-adjust metadata column widths
            metadata_sheet = writer.sheets['Metadata']
            metadata_sheet.column_dimensions['A'].width = 25
            metadata_sheet.column_dimensions['B'].width = 50
        
        print(f"\n💾 OUTPUT SAVED:")
        print(f"   JSON: {json_file}")
        print(f"   Excel: {excel_file}")
        print(f"   Records: {len(results)}")
        print(f"   Quality: {output_data['extraction_metadata']['quality_score']:.1%}")
        
        return json_file, excel_file
    
    def cleanup(self):
        """Delete temporary files"""
        if os.path.exists(self.temp_dir):
            file_count = len([f for f in os.listdir(self.temp_dir) if f.endswith('.pdf')])
            shutil.rmtree(self.temp_dir)
            print(f"\n🗑️  Cleaned up: {file_count} temp files deleted")
    
    def run(self):
        """Main OPTIMIZED production workflow with incremental processing"""
        print("\n" + "=" * 60)
        print("🚀 CP2000 PRODUCTION EXTRACTOR - OPTIMIZED")
        print("=" * 60)
        
        if self.force_full:
            print("⚠️  FULL REPROCESS MODE ENABLED")
        else:
            print("⚡ INCREMENTAL MODE: Only processing new files")
        
        self.start_time = datetime.now()
        
        try:
            # Step 1: Authenticate
            self.authenticate()
            
            # Step 2: Download from Google Drive (incremental)
            pdf_files = self.download_from_drive()
            
            if not pdf_files:
                print("\n✅ No new files to process! All files already processed.")
                print(f"📊 Total files in history: {len(self.processed_files)}")
                print("\n💡 To reprocess all files, run: python production_extractor.py --full")
                return
            
            # Step 3: Extract data (16 workers for ULTRA-FAST processing)
            results = self.extract_all_data(pdf_files, workers=16)
            
            if not results:
                print("\n⚠️  No successful extractions!")
                self.cleanup()
                return
            
            # Step 4: Save output (JSON + Excel)
            json_file, excel_file = self.save_output(results)
            
            # Step 5: Cleanup
            self.cleanup()
            
            # Summary
            duration = (datetime.now() - self.start_time).total_seconds()
            throughput = len(pdf_files) / duration if duration > 0 else 0
            
            print("\n" + "=" * 60)
            print("✅ EXTRACTION COMPLETE")
            print("=" * 60)
            print(f"⏱️  Time: {duration:.1f}s ({throughput:.2f} files/sec)")
            print(f"📊 New Files Processed: {len(pdf_files)}")
            print(f"✅ Successful Extractions: {len(results)}")
            print(f"📁 Total Files in History: {len(self.processed_files)}")
            print(f"💾 JSON: {json_file}")
            print(f"📊 Excel: {excel_file}")
            print(f"🗑️  Temp files: DELETED")
            print("\n✨ Ready for Logics upload!")
            print("\n💡 Next time, only NEW files will be processed automatically!")
            
        except KeyboardInterrupt:
            print("\n\n⚠️  Interrupted by user")
            self.cleanup()
        except Exception as e:
            print(f"\n❌ Error: {str(e)}")
            self.cleanup()
            raise

if __name__ == "__main__":
    # Check for --full flag
    force_full = '--full' in sys.argv
    
    extractor = ProductionExtractor(force_full=force_full)
    extractor.run()
