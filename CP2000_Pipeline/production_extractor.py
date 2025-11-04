"""
CP2000 PRODUCTION EXTRACTOR - OPTIMIZED FOR SPEED
This script processes CP2000 letters and extracts key data for Logics integration.

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
from logics_case_search import LogicsCaseSearcher

        except Exception as e:        return {}

            print(f"❌ Error processing {file_name}: {str(e)}")    

            processed_files[file_name] = {    def save_history(self, file_hash, result):

                'processed_at': datetime.now().isoformat(),        """Save processed file to history"""

                'success': False,        self.processed_files[file_hash] = {

                'error': str(e)            'processed_at': datetime.now().isoformat(),

            }            'filename': result.get('filename', ''),

                'success': True

    # Save processing history        }

    with open(history_file, 'w') as f:        

        json.dump(processed_files, f, indent=2)        with open(self.history_file, 'w') as f:

                json.dump(self.processed_files, f, indent=2)

    # Save results    

    if results:    def get_file_hash(self, filename):

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")        """Get unique hash for a file to track if it's been processed"""

                # Use filename as hash (simpler for Drive files)

        # Save JSON        return hashlib.md5(filename.encode()).hexdigest()

        output_json = f"LOGICS_DATA_{timestamp}.json"    

        with open(output_json, 'w') as f:    def authenticate(self):

            json.dump({        """Authenticate with Google Drive using service account"""

                'extraction_metadata': {        try:

                    'timestamp': datetime.now().isoformat(),            creds = service_account.Credentials.from_service_account_file(

                    'total_files': len(pdf_files),                'service-account-key.json',

                    'processed_files': processed_count,                scopes=self.SCOPES

                    'source_directory': str(input_dir),            )

                    'incremental': incremental            

                },            self.service = build('drive', 'v3', credentials=creds)

                'extracted_data': results            print("✅ Authenticated with Google Drive (Service Account)")

            }, f, indent=2)            

                except FileNotFoundError:

        print(f"\n✅ Results saved to {output_json}")            print("❌ Error: service-account-key.json not found")

        print(f"📊 Processed {processed_count} new files")            print("💡 Place your service account JSON file in the project root")

        print(f"📁 Total processed files in history: {len(processed_files)}")            raise

            except Exception as e:

    # Cleanup            print(f"❌ Authentication error: {str(e)}")

    if temp_dir.exists():            raise

        shutil.rmtree(temp_dir)    

        print("🧹 Cleaned up temporary files")    def download_from_drive(self):

        """Download PDFs from Google Drive with INCREMENTAL processing"""

if __name__ == "__main__":        print("\n📥 DOWNLOADING FROM GOOGLE DRIVE (INCREMENTAL MODE)")

    # Process the new batch        print("=" * 60)

    process_batch("../CP2000_Production/CP2000 NEW BATCH 2")        
        if self.force_full:
            print("⚠️  FULL REPROCESS MODE - Will process all files")
        
        # Clean and create temp directory
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
        os.makedirs(self.temp_dir)
        
        # Local directories to process
        local_dirs = [
            '../cp2000',
            '../cp2000 newbatch/temp_processing',
            '../cp2000new batch2'
        ]
        
        all_files = []
        skipped_count = 0
        
        for dir_path in local_dirs:
            if not os.path.exists(dir_path):
                print(f"⚠️  Directory not found: {dir_path}")
                continue
                
            print(f"\n📁 Processing directory: {dir_path}")
            
            # List PDF files in directory
            pdf_files = []
            for root, dirs, files in os.walk(dir_path):
                for file in files:
                    if file.lower().endswith('.pdf'):
                        pdf_files.append(os.path.join(root, file))
            
            print(f"   Found: {len(pdf_files)} PDFs")
            
            # Process each file (skip already processed)
            new_files = 0
            for file_path in pdf_files:
                file_name = os.path.basename(file_path)
                file_hash = self.get_file_hash(file_name)
                
                # Skip if already processed (unless force_full)
                if file_hash in self.processed_files and not self.force_full:
                    skipped_count += 1
                    continue
                
                try:
                    # Copy file to temp directory
                    local_path = os.path.join(self.temp_dir, file_name)
                    shutil.copy2(file_path, local_path)
                    
                    all_files.append(local_path)
                    new_files += 1
                    
                    if new_files % 10 == 0:
                        print(f"   Copied: {new_files} new files...")
                
                except Exception as e:
                    print(f"   ❌ Error: {file_name} - {str(e)}")
            
            print(f"   ✅ New files: {new_files}, Skipped: {len(pdf_files) - new_files}")
        
        print(f"\n✅ Total NEW files to process: {len(all_files)} PDFs")
        if skipped_count > 0:
            print(f"⏭️  Skipped (already processed): {skipped_count} PDFs")
        
        return all_files
    
    def extract_single_file(self, pdf_path):
        """Extract data from one PDF with improved letter type detection and Logics case search"""
        try:
            # Initialize extractors
            extractor = HundredPercentAccuracyExtractor()
            logics_searcher = LogicsCaseSearcher()
            
            # Extract data from PDF
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
                
                # Search for Logics case
                if result.get('ssn_last_4') and result.get('taxpayer_name'):
                    # Split full name into parts (if available)
                    name_parts = result['taxpayer_name'].split(' ', 1)
                    first_name = name_parts[0] if len(name_parts) > 1 else None
                    last_name = name_parts[-1]
                    
                    print(f"\n🔍 Searching Logics for: {last_name}, SSN: ***-**-{result['ssn_last_4']}")
                    case_result = logics_searcher.search_case(
                        ssn_last_4=result['ssn_last_4'],
                        last_name=last_name,
                        first_name=first_name
                    )
                    
                    if case_result:
                        result['logics_case_id'] = case_result.get('case_id')
                        result['logics_case_data'] = case_result
                        print(f"✅ Found Logics case: {result['logics_case_id']}")
                    else:
                        print("❌ No matching Logics case found")
                
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
        """Save results in separate files for matched and unmatched cases"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Separate matched and unmatched cases
        matched_cases = [r for r in results if r.get('logics_case_id')]
        unmatched_cases = [r for r in results if not r.get('logics_case_id')]
        
        # Save JSON with all data
        json_file = f"LOGICS_DATA_{timestamp}.json"
        output_data = {
            "extraction_metadata": {
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "total_records": len(results),
                "matched_records": len(matched_cases),
                "unmatched_records": len(unmatched_cases),
                "source": "Google Drive",
                "quality_score": sum(r.get('extraction_confidence', 0) for r in results) / len(results) if results else 0,
                "google_drive_folders": list(self.folders.keys())
            },
            "case_matching_data": results
        }
        
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, indent=2, ensure_ascii=False)

        # Create output directories if they don't exist
        os.makedirs("matched_cases", exist_ok=True)
        os.makedirs("unmatched_cases", exist_ok=True)
        
        # Function to create DataFrame from records
        def create_df_data(records, include_status=False):
            df_data = []
            for record in records:
                data = {
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
                    'Quality Issues': ', '.join(record.get('quality_issues', [])),
                }
                
                if include_status:
                    data.update({
                        'Case ID': record.get('logics_case_id', ''),
                        'Status': 'Pending',  # Initial status
                        'Action': 'Choose Action',  # Dropdown cell
                        'Last Updated': '',
                        'Notes': ''
                    })
                
                df_data.append(data)
            return pd.DataFrame(df_data)

        # Save matched cases Excel
        if matched_cases:
            matched_file = f"matched_cases/MATCHED_CASES_{timestamp}.xlsx"
            df_matched = create_df_data(matched_cases, include_status=True)
            
            with pd.ExcelWriter(matched_file, engine='openpyxl') as writer:
                df_matched.to_excel(writer, sheet_name='Matched Cases', index=False)
                
                # Get workbook and worksheet
                workbook = writer.book
                worksheet = writer.sheets['Matched Cases']
                
                # Add data validation for Action column
                from openpyxl.worksheet.datavalidation import DataValidation
                action_validation = DataValidation(
                    type="list",
                    formula1='"Approve,Reject,Review"',
                    allow_blank=True
                )
                worksheet.add_data_validation(action_validation)
                
                # Apply validation to Action column
                action_col = df_matched.columns.get_loc('Action') + 1  # +1 because Excel is 1-based
                for row in range(2, len(df_matched) + 2):  # +2 for header and 1-based
                    cell = worksheet.cell(row=row, column=action_col)
                    action_validation.add(cell)
                
                # Auto-adjust column widths
                for idx, col in enumerate(df_matched.columns):
                    max_length = max(
                        df_matched[col].astype(str).map(len).max(),
                        len(col)
                    ) + 2
                    worksheet.column_dimensions[chr(65 + idx)].width = min(max_length, 50)
                
                # Add instructions sheet
                instructions = pd.DataFrame([
                    ['Instructions', 'Description'],
                    ['Approve', 'Document will be uploaded and task created in Logics'],
                    ['Reject', 'Case will be moved to unmatched for manual review'],
                    ['Review', 'Mark for additional review before processing'],
                    ['', ''],
                    ['Note:', 'After selecting an action, save the file to trigger processing']
                ])
                instructions.to_excel(writer, sheet_name='Instructions', index=False)

        # Save unmatched cases Excel
        if unmatched_cases:
            unmatched_file = f"unmatched_cases/UNMATCHED_CASES_{timestamp}.xlsx"
            df_unmatched = create_df_data(unmatched_cases)
            
            with pd.ExcelWriter(unmatched_file, engine='openpyxl') as writer:
                df_unmatched.to_excel(writer, sheet_name='Unmatched Cases', index=False)
                
                # Get workbook and worksheet
                workbook = writer.book
                worksheet = writer.sheets['Unmatched Cases']
                
                # Auto-adjust column widths
                for idx, col in enumerate(df_unmatched.columns):
                    max_length = max(
                        df_unmatched[col].astype(str).map(len).max(),
                        len(col)
                    ) + 2
                    worksheet.column_dimensions[chr(65 + idx)].width = min(max_length, 50)
                
                # Add metadata sheet
                metadata_df = pd.DataFrame([
                    ['Total Unmatched Cases', len(unmatched_cases)],
                    ['Extraction Date', datetime.now().strftime("%Y-%m-%d %H:%M:%S")],
                    ['Instructions', 'These cases require manual review and matching'],
                    ['Next Steps', '1. Review case details\n2. Search in Logics manually\n3. Create cases if needed']
                ], columns=['Metric', 'Value'])
                
                metadata_df.to_excel(writer, sheet_name='Instructions', index=False)
                
        # Return file paths
        files = {
            'json': json_file,
            'matched': matched_file if matched_cases else None,
            'unmatched': unmatched_file if unmatched_cases else None
        }
        
        print(f"\n💾 OUTPUT SAVED:")
        print(f"   JSON: {json_file}")
        if matched_cases:
            print(f"   Matched Cases Excel: {matched_file}")
            print(f"   Matched Records: {len(matched_cases)}")
        if unmatched_cases:
            print(f"   Unmatched Cases Excel: {unmatched_file}")
            print(f"   Unmatched Records: {len(unmatched_cases)}")
        print(f"   Quality: {output_data['extraction_metadata']['quality_score']:.1%}")
        
        return files
        
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
