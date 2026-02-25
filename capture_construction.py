#!/usr/bin/env python3
"""
NDI Construction Timelapse Capture
Uses ndi-record from NDI SDK to capture frames, then extracts JPEG using FFmpeg
Requires PTY for ndi-record to function properly
"""

import subprocess
import schedule
import time
from datetime import datetime
import logging
import os
import sys
import signal
import pty

# Configuration from environment variables
OUTPUT_DIR = os.getenv('OUTPUT_DIR', '/output')
LOG_DIR = os.getenv('LOG_DIR', '/logs')
NDI_SOURCE_NAME = os.getenv('NDI_SOURCE_NAME', 'Your-Camera-Name (CAM)')
NDI_SOURCE_URL = os.getenv('NDI_SOURCE_URL', '192.168.1.100:5961')
CAPTURE_INTERVAL = int(os.getenv('CAPTURE_INTERVAL', '15'))
START_HOUR = int(os.getenv('START_HOUR', '5'))
END_HOUR = int(os.getenv('END_HOUR', '21'))
RECORD_SECONDS = int(os.getenv('RECORD_SECONDS', '5'))
JPEG_QUALITY = int(os.getenv('JPEG_QUALITY', '95'))
FRAME_NUMBER = int(os.getenv('FRAME_NUMBER', '120'))

# Setup directories
os.makedirs(LOG_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(LOG_DIR, 'capture.log')),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Find ndi-record binary
NDI_RECORD = None
for path in ['/usr/local/bin/ndi-record', '/tmp/NDI SDK for Linux/bin/x86_64-linux-gnu/ndi-record']:
    if os.path.exists(path):
        NDI_RECORD = path
        break


def check_ffmpeg():
    """Check if FFmpeg is available"""
    try:
        result = subprocess.run(['ffmpeg', '-version'], capture_output=True, text=True, timeout=10)
        return result.returncode == 0
    except:
        return False


def extract_jpeg_from_mov(mov_file, jpeg_file, quality=95, frame_num=120):
    """Extract specific frame from MOV file as JPEG using FFmpeg"""
    try:
        # FFmpeg quality scale: 2-31 (2=best, 31=worst)
        ffmpeg_quality = max(2, min(31, int(31 - (quality / 100 * 29))))
        
        # Frame number is 0-indexed, so frame 120 = index 119
        frame_index = frame_num - 1
        
        cmd = [
            'ffmpeg',
            '-y',
            '-i', mov_file,
            '-vf', f'select=eq(n\\,{frame_index})',
            '-vframes', '1',
            '-q:v', str(ffmpeg_quality),
            jpeg_file
        ]
        
        logger.info(f"Extracting frame {frame_num} as JPEG with quality {quality}")
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.returncode != 0:
            logger.error(f"FFmpeg failed: {result.stderr}")
            return False
            
        return os.path.exists(jpeg_file)
        
    except subprocess.TimeoutExpired:
        logger.error("FFmpeg timed out")
        return False
    except Exception as e:
        logger.error(f"FFmpeg error: {str(e)}")
        return False


def capture_frame():
    """Capture a single frame using ndi-record with PTY, then extract JPEG"""
    if not NDI_RECORD:
        logger.error("ndi-record binary not found")
        return False
    
    master = None
    slave = None
        
    try:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        date_folder = datetime.now().strftime("%Y-%m-%d")
        
        daily_dir = os.path.join(OUTPUT_DIR, date_folder)
        os.makedirs(daily_dir, exist_ok=True)
        
        temp_base = f"/tmp/capture_{timestamp}"
        temp_mov = f"{temp_base}.mov"
        final_jpeg = os.path.join(daily_dir, f"frame_{timestamp}.jpg")
        
        # Build command
        cmd = [NDI_RECORD, '-i', NDI_SOURCE_NAME, '-u', NDI_SOURCE_URL, '-o', temp_base]
        
        logger.info(f"Running: {' '.join(cmd)}")
        logger.info(f"Recording for {RECORD_SECONDS} seconds...")
        
        # Create pseudo-terminal (required for ndi-record to work)
        master, slave = pty.openpty()
        
        # Start recording process with PTY
        process = subprocess.Popen(
            cmd,
            stdin=slave,
            stdout=slave,
            stderr=slave,
            close_fds=True
        )
        
        # Wait for recording duration
        time.sleep(RECORD_SECONDS)
        
        # Send SIGINT first (like Ctrl+C) to properly finalize the MOV file
        process.send_signal(signal.SIGINT)
        
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            logger.warning("Process didn't stop with SIGINT, trying SIGTERM...")
            process.send_signal(signal.SIGTERM)
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                logger.warning("Process didn't stop gracefully, killing...")
                process.kill()
                process.wait(timeout=5)
        
        # Close PTY file descriptors
        os.close(master)
        os.close(slave)
        master = None
        slave = None
        
        # Wait for file to be finalized on disk
        time.sleep(1)
        
        # Check if MOV file was created
        if not os.path.exists(temp_mov):
            logger.error(f"Recording file not created: {temp_mov}")
            tmp_files = [f for f in os.listdir('/tmp') if 'capture' in f.lower()]
            logger.error(f"Capture files in /tmp: {tmp_files}")
            return False
        
        file_size = os.path.getsize(temp_mov) / (1024 * 1024)  # MB
        logger.info(f"Recorded MOV: {temp_mov} ({file_size:.1f} MB)")
        
        # Extract JPEG from MOV
        if extract_jpeg_from_mov(temp_mov, final_jpeg, JPEG_QUALITY, FRAME_NUMBER):
            jpeg_size = os.path.getsize(final_jpeg) / 1024  # KB
            logger.info(f"SUCCESS: {final_jpeg} ({jpeg_size:.1f} KB)")
            
            # Clean up temp files
            for ext in ['.mov', '.mov.ndi', '.mov.preview', '.mov.preview.ndi', '.mov.Recording', '.mov.preview.Recording']:
                temp_file = temp_base + ext
                if os.path.exists(temp_file):
                    try:
                        os.remove(temp_file)
                    except Exception as e:
                        logger.warning(f"Could not remove {temp_file}: {e}")
                    
            return True
        else:
            logger.error("Failed to extract JPEG from MOV")
            return False
            
    except Exception as e:
        logger.error(f"Capture failed: {str(e)}", exc_info=True)
        return False
    finally:
        # Ensure PTY file descriptors are closed
        if master is not None:
            try:
                os.close(master)
            except:
                pass
        if slave is not None:
            try:
                os.close(slave)
            except:
                pass


def should_capture():
    """Check if current time is within capture window"""
    current_hour = datetime.now().hour
    return START_HOUR <= current_hour < END_HOUR


def main():
    logger.info("=" * 60)
    logger.info("NDI Construction Timelapse System Starting")
    logger.info("=" * 60)
    logger.info(f"Output directory: {OUTPUT_DIR}")
    logger.info(f"Capture interval: Every {CAPTURE_INTERVAL} minutes")
    logger.info(f"Active hours: {START_HOUR}:00 - {END_HOUR}:00")
    logger.info(f"Record duration: {RECORD_SECONDS} seconds")
    logger.info(f"JPEG quality: {JPEG_QUALITY}")
    logger.info(f"Frame to extract: {FRAME_NUMBER}")
    logger.info(f"Target NDI source: {NDI_SOURCE_NAME}")
    logger.info(f"NDI source URL: {NDI_SOURCE_URL}")
    logger.info(f"NDI Record binary: {NDI_RECORD}")
    logger.info("=" * 60)
    
    if NDI_RECORD is None:
        logger.error("ndi-record binary not found!")
        return 1
    
    if check_ffmpeg():
        logger.info("FFmpeg found - JPEG extraction enabled")
    else:
        logger.error("FFmpeg not found - cannot extract JPEGs!")
        return 1
    
    # Schedule captures
    schedule.every(CAPTURE_INTERVAL).minutes.do(capture_frame)
    
    # Capture test frame
    logger.info("Capturing test frame...")
    if capture_frame():
        logger.info("Test frame captured successfully!")
    else:
        logger.warning("Test frame capture failed - check configuration")
    
    logger.info("Entering main loop. Press Ctrl+C to stop.")
    
    try:
        while True:
            if should_capture():
                schedule.run_pending()
            time.sleep(30)
            
    except KeyboardInterrupt:
        logger.info("Shutdown requested by user")
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}", exc_info=True)
    
    logger.info("Shutdown complete")
    return 0


if __name__ == "__main__":
    sys.exit(main())
