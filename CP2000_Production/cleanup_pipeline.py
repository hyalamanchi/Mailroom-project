#!/usr/bin/env python3
"""
Cleanup Script for CP2000 Pipeline
Handles cleanup of temporary files and archiving of old processed files
"""

import os
import shutil
import logging
from datetime import datetime, timedelta
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv('config/.env')

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/cleanup.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class PipelineCleanup:
    def __init__(self):
        self.temp_max_age = int(os.getenv('TEMP_FILE_MAX_AGE', 7))
        self.archive_age = int(os.getenv('ARCHIVE_AGE', 30))
        self.max_disk_usage = int(os.getenv('MAX_DISK_USAGE', 90))
        
        # Directories to clean
        self.temp_dirs = ['TEMP_PROCESSING']
        self.archive_dirs = ['PROCESSED_FILES', 'MATCHED_CASES']
        
    def check_file_age(self, file_path):
        """Get file age in days"""
        mtime = os.path.getmtime(file_path)
        age = datetime.now() - datetime.fromtimestamp(mtime)
        return age.days
    
    def cleanup_temp_files(self):
        """Clean up temporary processing files"""
        logger.info("🧹 Cleaning up temporary files...")
        
        for temp_dir in self.temp_dirs:
            if not os.path.exists(temp_dir):
                continue
                
            for root, _, files in os.walk(temp_dir):
                for file in files:
                    file_path = os.path.join(root, file)
                    age = self.check_file_age(file_path)
                    
                    if age > self.temp_max_age:
                        try:
                            os.remove(file_path)
                            logger.info(f"🗑️  Removed temp file: {file}")
                        except Exception as e:
                            logger.error(f"❌ Error removing {file}: {e}")
    
    def archive_old_files(self):
        """Archive old processed files"""
        logger.info("📦 Archiving old files...")
        
        archive_dir = "ARCHIVES"
        archive_date = datetime.now().strftime("%Y%m")
        
        # Create archive directory if it doesn't exist
        if not os.path.exists(archive_dir):
            os.makedirs(archive_dir)
        
        # Create dated archive folder
        dated_archive = os.path.join(archive_dir, archive_date)
        if not os.path.exists(dated_archive):
            os.makedirs(dated_archive)
        
        for dir_name in self.archive_dirs:
            if not os.path.exists(dir_name):
                continue
                
            logger.info(f"Checking {dir_name} for files to archive...")
            
            for root, _, files in os.walk(dir_name):
                for file in files:
                    file_path = os.path.join(root, file)
                    age = self.check_file_age(file_path)
                    
                    if age > self.archive_age:
                        try:
                            # Create relative path structure in archive
                            rel_path = os.path.relpath(root, dir_name)
                            archive_path = os.path.join(dated_archive, dir_name, rel_path)
                            os.makedirs(archive_path, exist_ok=True)
                            
                            # Move file to archive
                            shutil.move(file_path, os.path.join(archive_path, file))
                            logger.info(f"📦 Archived: {file}")
                            
                        except Exception as e:
                            logger.error(f"❌ Error archiving {file}: {e}")
    
    def cleanup_logs(self):
        """Rotate and clean up log files"""
        logger.info("📝 Cleaning up logs...")
        
        log_dir = "logs"
        if not os.path.exists(log_dir):
            return
            
        for file in os.listdir(log_dir):
            if not file.endswith('.log'):
                continue
                
            file_path = os.path.join(log_dir, file)
            age = self.check_file_age(file_path)
            
            # Rotate logs older than 7 days
            if age > 7:
                try:
                    # Compress old log
                    archive_name = f"{file}.{datetime.now().strftime('%Y%m%d')}.gz"
                    with open(file_path, 'rb') as f_in:
                        with gzip.open(os.path.join(log_dir, archive_name), 'wb') as f_out:
                            shutil.copyfileobj(f_in, f_out)
                    
                    # Remove original
                    os.remove(file_path)
                    logger.info(f"📝 Rotated log: {file}")
                    
                except Exception as e:
                    logger.error(f"❌ Error rotating log {file}: {e}")
    
    def check_disk_space(self):
        """Check and warn about disk space"""
        import shutil
        
        total, used, free = shutil.disk_usage('.')
        usage_percent = (used / total) * 100
        
        if usage_percent > self.max_disk_usage:
            logger.warning(f"⚠️ High disk usage: {usage_percent:.1f}%")
            logger.warning(f"Free space: {free / (2**30):.1f} GB")
            return False
        
        return True
    
    def run_cleanup(self):
        """Run the complete cleanup process"""
        logger.info("🚀 Starting pipeline cleanup...")
        
        try:
            # Check disk space first
            if not self.check_disk_space():
                logger.error("❌ Insufficient disk space for cleanup")
                return False
            
            # Run cleanup tasks
            self.cleanup_temp_files()
            self.archive_old_files()
            self.cleanup_logs()
            
            logger.info("✅ Cleanup completed successfully")
            return True
            
        except Exception as e:
            logger.error(f"❌ Cleanup failed: {e}")
            return False

if __name__ == "__main__":
    cleanup = PipelineCleanup()
    cleanup.run_cleanup()