#!/bin/bash

# CP2000 Pipeline Shutdown Script
# Gracefully stops all pipeline components and performs cleanup

# Configuration
LOG_DIR="logs"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

# Function to log messages
log_message() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_DIR/shutdown_${TIMESTAMP}.log"
}

# Function to stop a process gracefully
stop_process() {
    local pid=$1
    local name=$2
    local max_wait=30  # Maximum wait time in seconds
    
    if [ -z "$pid" ]; then
        log_message "No PID found for $name"
        return 0
    }
    
    if ! ps -p $pid > /dev/null; then
        log_message "$name (PID: $pid) is not running"
        return 0
    }
    
    log_message "Stopping $name (PID: $pid)..."
    
    # Send SIGTERM first for graceful shutdown
    kill -15 $pid 2>/dev/null
    
    # Wait for process to stop
    local counter=0
    while ps -p $pid > /dev/null && [ $counter -lt $max_wait ]; do
        sleep 1
        counter=$((counter + 1))
    done
    
    # If process still running, force kill
    if ps -p $pid > /dev/null; then
        log_message "Force stopping $name (PID: $pid)..."
        kill -9 $pid 2>/dev/null
    fi
    
    # Verify process is stopped
    if ! ps -p $pid > /dev/null; then
        log_message "✅ $name stopped successfully"
        return 0
    else
        log_message "❌ Failed to stop $name"
        return 1
    fi
}

# Function to archive logs
archive_logs() {
    log_message "Archiving logs..."
    
    # Create archive directory if it doesn't exist
    mkdir -p "$LOG_DIR/archive"
    
    # Create archive file
    archive_file="$LOG_DIR/archive/logs_${TIMESTAMP}.tar.gz"
    
    # Archive all log files except current shutdown log
    find "$LOG_DIR" -type f -name "*.log" ! -name "shutdown_${TIMESTAMP}.log" -exec tar -czf "$archive_file" {} +
    
    if [ $? -eq 0 ]; then
        log_message "✅ Logs archived to $archive_file"
        # Clean up old logs
        find "$LOG_DIR" -type f -name "*.log" ! -name "shutdown_${TIMESTAMP}.log" -delete
    else
        log_message "❌ Failed to archive logs"
        return 1
    fi
}

# Function to clean temporary files
clean_temp_files() {
    log_message "Cleaning temporary files..."
    
    # Clean TEMP_PROCESSING directory
    if [ -d "TEMP_PROCESSING" ]; then
        rm -rf TEMP_PROCESSING/*
        if [ $? -eq 0 ]; then
            log_message "✅ Temporary files cleaned"
        else
            log_message "❌ Failed to clean temporary files"
            return 1
        fi
    fi
}

# Main shutdown sequence
main() {
    log_message "🛑 Initiating CP2000 Pipeline shutdown..."
    
    # Stop monitor process
    if [ -f "$LOG_DIR/monitor.pid" ]; then
        stop_process $(cat "$LOG_DIR/monitor.pid") "Monitor"
        rm "$LOG_DIR/monitor.pid"
    fi
    
    # Stop pipeline process
    if [ -f "$LOG_DIR/pipeline.pid" ]; then
        stop_process $(cat "$LOG_DIR/pipeline.pid") "Pipeline"
        rm "$LOG_DIR/pipeline.pid"
    fi
    
    # Clean up and archive
    clean_temp_files
    archive_logs
    
    log_message "✨ Pipeline shutdown complete!"
    
    # Display shutdown summary
    echo ""
    echo "=== CP2000 Pipeline Shutdown Summary ==="
    echo "Shutdown Time: $(date '+%Y-%m-%d %H:%M:%S')"
    echo "Log Archive: $LOG_DIR/archive/logs_${TIMESTAMP}.tar.gz"
    echo "Shutdown Log: $LOG_DIR/shutdown_${TIMESTAMP}.log"
    echo "==================================="
}

# Run main function
main