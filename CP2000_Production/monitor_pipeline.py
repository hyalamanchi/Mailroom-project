#!/usr/bin/env python3
"""
Pipeline Monitor Script
Monitors pipeline health and sends alerts for issues
"""

import os
import sys
import json
import time
import logging
import psutil
from datetime import datetime, timedelta
from pathlib import Path

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/monitor.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

class PipelineMonitor:
    def __init__(self):
        self.pipeline_process = None
        self.last_activity = None
        self.error_count = 0
        self.max_errors = 3
        self.check_interval = 300  # 5 minutes
        
    def check_directories(self):
        """Check if required directories exist and are writable"""
        required_dirs = [
            'config', 'data', 'logs',
            'MATCHED_CASES', 'UNMATCHED_CASES',
            'QUALITY_REVIEW', 'PROCESSED_FILES',
            'TEMP_PROCESSING'
        ]
        
        for dir_name in required_dirs:
            dir_path = Path(dir_name)
            if not dir_path.exists():
                logger.error(f"❌ Directory missing: {dir_name}")
                dir_path.mkdir(parents=True, exist_ok=True)
                logger.info(f"✅ Created directory: {dir_name}")
            
            # Check permissions
            if not os.access(dir_path, os.W_OK):
                logger.error(f"❌ No write permission: {dir_name}")
                return False
        
        return True
    
    def check_config_files(self):
        """Verify configuration files exist and are valid"""
        required_files = [
            'config/service-account-key.json',
            'config/credentials.json',
            'config/.env'
        ]
        
        for file_path in required_files:
            if not Path(file_path).exists():
                logger.error(f"❌ Missing config file: {file_path}")
                return False
        
        return True
    
    def check_process_health(self):
        """Check if pipeline process is running and healthy"""
        if not self.pipeline_process:
            return False
            
        try:
            process = psutil.Process(self.pipeline_process)
            if process.status() == psutil.STATUS_ZOMBIE:
                logger.error("❌ Pipeline process is zombie")
                return False
                
            # Check CPU and memory usage
            cpu_percent = process.cpu_percent(interval=1)
            mem_percent = process.memory_percent()
            
            if cpu_percent > 90:  # High CPU usage
                logger.warning(f"⚠️ High CPU usage: {cpu_percent}%")
            if mem_percent > 80:  # High memory usage
                logger.warning(f"⚠️ High memory usage: {mem_percent}%")
                
            return True
            
        except psutil.NoSuchProcess:
            logger.error("❌ Pipeline process not found")
            return False
    
    def check_recent_activity(self):
        """Check for recent file processing activity"""
        now = datetime.now()
        if not self.last_activity:
            return True
            
        time_since_activity = now - self.last_activity
        if time_since_activity > timedelta(minutes=30):  # No activity for 30 minutes
            logger.warning(f"⚠️ No activity for {time_since_activity}")
            return False
            
        return True
    
    def check_disk_space(self):
        """Check available disk space"""
        disk = psutil.disk_usage('.')
        if disk.percent > 90:
            logger.error(f"❌ Low disk space: {disk.percent}%")
            return False
        return True
    
    def check_log_files(self):
        """Check log files for errors"""
        log_file = 'logs/pipeline.log'
        if not Path(log_file).exists():
            return True
            
        try:
            with open(log_file, 'r') as f:
                last_lines = f.readlines()[-100:]  # Check last 100 lines
                error_count = sum(1 for line in last_lines if 'ERROR' in line)
                if error_count > 5:  # More than 5 errors in last 100 lines
                    logger.warning(f"⚠️ High error rate in logs: {error_count} errors")
                    return False
        except Exception as e:
            logger.error(f"❌ Error reading log file: {e}")
            return False
            
        return True
    
    def monitor(self):
        """Main monitoring loop"""
        logger.info("🔍 Starting pipeline monitor...")
        
        while True:
            try:
                # Basic checks
                if not self.check_directories():
                    self.error_count += 1
                if not self.check_config_files():
                    self.error_count += 1
                if not self.check_disk_space():
                    self.error_count += 1
                    
                # Process checks
                if not self.check_process_health():
                    self.error_count += 1
                if not self.check_recent_activity():
                    self.error_count += 1
                if not self.check_log_files():
                    self.error_count += 1
                
                # Handle errors
                if self.error_count >= self.max_errors:
                    logger.error(f"❌ Too many errors ({self.error_count}). Restarting pipeline...")
                    self.restart_pipeline()
                    self.error_count = 0
                
                # Reset if everything is good
                if self.error_count == 0:
                    logger.info("✅ Pipeline health check passed")
                
                time.sleep(self.check_interval)
                
            except KeyboardInterrupt:
                logger.info("👋 Stopping pipeline monitor...")
                break
            except Exception as e:
                logger.error(f"❌ Monitor error: {e}")
                time.sleep(60)  # Wait before retrying
    
    def restart_pipeline(self):
        """Restart the pipeline process"""
        try:
            if self.pipeline_process:
                process = psutil.Process(self.pipeline_process)
                process.terminate()
                process.wait()
            
            # Start new pipeline process
            cmd = [sys.executable, 'automated_pipeline.py']
            process = psutil.Popen(cmd)
            self.pipeline_process = process.pid
            logger.info(f"✅ Pipeline restarted (PID: {self.pipeline_process})")
            
        except Exception as e:
            logger.error(f"❌ Error restarting pipeline: {e}")

if __name__ == "__main__":
    monitor = PipelineMonitor()
    monitor.monitor()