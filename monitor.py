import os
import time
import math
import requests
import smtplib
import json

from email.mime.text import MIMEText
from email.message import EmailMessage
from email.contentmanager import raw_data_manager
from geopy import distance
from dotenv import load_dotenv
from typing import Dict, Tuple, Optional, List
from shapely.geometry import Point, Polygon

from config import (
    POLL_INTERVAL_SECS, 
    RUNTIME_SECS,
    API_BASE_URL, 
    CLINICIAN_IDS,
    
    SMTP_HOST,
    SMTP_PORT,
    SMTP_USERNAME,
    SMTP_PASSWORD,
    ALERT_SENDER_EMAIL,
    ALERT_RECIPIENT_EMAIL
)

load_dotenv()


def fetch_clinician_data(clinician_id: int) -> Optional[Dict]:
    try:
        response = requests.get(
            f"{API_BASE_URL}/clinicianstatus/{clinician_id}",
            timeout=5
        )
        response.raise_for_status()
        data = response.json()
        features = data.get("features", [])  # Extract point, polygon features
        if len(features) < 2:
            return None
            
        # Current location
        loc_feature = features[0]
        coords = loc_feature["geometry"]["coordinates"]
        curr_loc = (coords[1], coords[0])

        # Safety zone
        zone_feature = features[1]
        zone_coords = zone_feature["geometry"]["coordinates"]
        safety_zone = zone_coords
        
        return {
            "location": curr_loc,
            "zone": safety_zone
        }
    except Exception as e:
        print(f"Couldn't find clinician {clinician_id}: {e}")
        return None

def is_point_in_polygon(lat: float, lon: float, polygon_coords: List) -> bool:
    """
    https://github.com/shapely/shapely
    """
    try:
        point = Point(lon, lat)
        # Handle exterior and holes
        exterior_ring = polygon_coords[0]  # first ring is exterior
        exterior_coords = [(coord[0], coord[1]) for coord in exterior_ring]
        # create polygon
        if len(polygon_coords) > 1:
            hole_coords = []  # handle holes edge cases, e.g. area they're not allowed to be in
            for hole in polygon_coords[1:]:
                hole_coords.append([(coord[0], coord[1]) for coord in hole])
            polygon = Polygon(exterior_coords, holes=hole_coords)
        else:
            polygon = Polygon(exterior_coords)
        
        return polygon.contains(point) or polygon.touches(point)  # On boundary counts as in-zone!
        
    except Exception as e:
        return False  # Assume out of zone for safety

def send_alert(clinician_id: int, reason: str) -> None:
    """
    https://docs.python.org/3/library/email.contentmanager.html#module-email.contentmanager
    https://docs.python.org/3/library/smtplib.html
    """
    if "returned to their safety zone" in reason:
        subject = f"RE-ENTRY: Clinician {clinician_id} Back in Safety Zone"
    elif "Still out of safety zone" in reason:
        subject = f"ALERT FOLLOW-UP ALERT: Clinician {clinician_id} Still Out of Zone"
    else:
        subject = f"ALERT: Clinician {clinician_id} Out of Safety Zone!!!"
    
    # Compose message/alert
    msg = EmailMessage()
    msg['Subject'] = subject
    msg['From'] = ALERT_SENDER_EMAIL
    msg['To'] = ALERT_RECIPIENT_EMAIL
    body = f"""
    Clinician Safety Zone Update
    
    Clinician ID: {clinician_id}
    Reason: {reason}
    Time: {time.strftime('%Y-%m-%d %H:%M:%S %Z')}
    """
    raw_data_manager.set_content(
        msg,
        body,
        subtype="plain",
        charset='utf-8',
        cte='quoted-printable',
        disposition='inline'
    )

    # sending the message/alert
    with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
        server.starttls()
        server.login(SMTP_USERNAME, SMTP_PASSWORD)
        server.send_message(msg)
    print(f"{reason} alert about clinician {clinician_id} sent!")


def check_clinician_status(clinician_id: int) -> bool:
    data = fetch_clinician_data(clinician_id)
    if data is None:
        return False  # assume out of zone for safety
    # elif data["location"] is None:
    #     # Sprinter HQ (Google Maps)
    #     location = (37.47970680911318, -122.17590752023614)
    # elif data["zone"] is None:
    #     # 500m radius circle around Sprinter HQ (Google Maps)   
    #     zone = [Point(37.47970680911318, -122.17590752023614).buffer(0.005)]  
    else:
        location = data["location"]
        zone = data["zone"]
    return is_point_in_polygon(location[0], location[1], zone)

def main():
    # state tracking
    prev_status: Dict[int, bool] = {cid: True for cid in CLINICIAN_IDS}
    # when clinicians first went out of zone for follow-up warnings
    out_of_zone_since: Dict[int, Optional[float]] = {cid: None for cid in CLINICIAN_IDS}
    # if we've already sent the 5-minute warning
    alert_sent: Dict[int, bool] = {cid: False for cid in CLINICIAN_IDS}
    
    start_time = time.time()
    count = 0
    end_time = start_time + RUNTIME_SECS
    
    try:
        print(f"Monitoring {len(CLINICIAN_IDS)} Sprinters at {POLL_INTERVAL_SECS}s interval")
        while True:
            # time limit
            if RUNTIME_SECS and time.time() >= end_time:
                break
            iter_start = time.time()
            count += 1
            print(f"\nIteration {count} at {time.strftime('%H:%M:%S')}")  # every second counts!
            
            for clinician_id in CLINICIAN_IDS:
                curr_status = check_clinician_status(clinician_id)
                prev_was_in = prev_status[clinician_id]
                current_time = time.time()
                
                # just left zone
                if prev_was_in and not curr_status:
                    reason = "They left their assigned safety zone"
                    send_alert(clinician_id, reason)
                    out_of_zone_since[clinician_id] = current_time  # track when clinician left
                    alert_sent[clinician_id] = False  # reset warning flag
                
                # returned to zone
                elif not prev_was_in and curr_status:
                    if out_of_zone_since[clinician_id] is not None:
                        out_duration = current_time - out_of_zone_since[clinician_id]
                        minutes_out = out_duration / 60
                        reason = f"They returned to their safety zone after {minutes_out:.1f} minutes"
                        send_alert(clinician_id, reason)
                    out_of_zone_since[clinician_id] = None  # reset tracking
                    alert_sent[clinician_id] = False  # reset warning flag
                
                # still out of zone, check 5-minute follow-up
                elif not curr_status and out_of_zone_since[clinician_id] is not None:
                    out_duration = current_time - out_of_zone_since[clinician_id]
                    if out_duration >= 300 and not alert_sent[clinician_id]:  # 300secs=5mins
                        minutes_out = out_duration / 60
                        reason = f"Still out of safety zone after {minutes_out:.1f} minutes"
                        send_alert(clinician_id, reason)
                        alert_sent[clinician_id] = True
                
                prev_status[clinician_id] = curr_status
            # chill until next polling interval
            elapsed = time.time() - iter_start
            if RUNTIME_SECS:
                remaining_runtime = end_time - time.time()
                sleep_time = min(POLL_INTERVAL_SECS - elapsed, remaining_runtime)
            else:
                sleep_time = max(0, POLL_INTERVAL_SECS - elapsed)
            if sleep_time > 0:
                time.sleep(sleep_time)
            else:
                break
        if RUNTIME_SECS:
            print(f"\nCompleted {count} iterations")
    except Exception as e:
        print(f"Error during monitoring: {e}")
        raise

if __name__ == "__main__":
    main() 