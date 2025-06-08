"""
Run the service for an hour with alerts pointed to coding-challenges+alerts@sprinterhealth.com
"""
import os
import time
import signal
import sys
from monitor import main
from dotenv import load_dotenv

load_dotenv()

def signal_handler(signum, frame):
    print("\nReceived interrupt signal. Shutting down monitor...")
    sys.exit(0)

def run_for_one_hour():    
    # Signal handlers for graceful shutdown
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    start_time = time.time()
    end_time = start_time + 3600  # 1 hour=3600 seconds
    print(f"Clinician Monitor until: {time.localtime(end_time)}")
    
    try:
        import monitor
        # init state tracking
        prev_status = {cid: True for cid in monitor.CLINICIAN_IDS}
        print(f"Monitoring {len(monitor.CLINICIAN_IDS)} Sprinters at {monitor.POLL_INTERVAL_SECS}s interval")
        count = 0
        
        while time.time() < end_time:
            iteration_start = time.time()
            count += 1
            for clinician_id in monitor.CLINICIAN_IDS:
                curr_status = monitor.check_clinician_status(clinician_id)
                # alert if status: in-zone --> out-of-zone
                if prev_status[clinician_id] and not curr_status:
                    reason = "They left their assigned safety zone"
                    monitor.send_alert(clinician_id, reason) 
                prev_status[clinician_id] = curr_status
            
            # chill until next polling interval
            elapsed = time.time() - iteration_start
            sleep_time = min(monitor.POLL_INTERVAL_SECS - elapsed, end_time - time.time())
            
            if sleep_time > 0:
                remaining_time = end_time - time.time()
                remaining_minutes = remaining_time / 60
                time.sleep(sleep_time)
            else:
                break
        
        print(f"\n1 hour monitor complete!")
        print(f"\nTotal iterations: {count}")
        print("\nAll alerts were sent to: coding-challenges+alerts@sprinterhealth.com")
        
    except Exception as e:
        print(f"Error during monitoring: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    run_for_one_hour() 