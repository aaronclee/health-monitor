import os
from dotenv import load_dotenv

load_dotenv()

API_BASE_URL = os.getenv("API_BASE_URL")
CLINICIAN_IDS = list(range(1, 8))  # IDs 1-7

# Balance between API load (<100 QPS) and 5-minute alert
POLL_INTERVAL_SECS = 60  # 7 clinicians/60 secs = 0.12 QPS

SMTP_HOST = os.getenv("SMTP_HOST")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USERNAME = os.getenv("SMTP_USERNAME")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")
ALERT_SENDER_EMAIL = os.getenv("ALERT_SENDER_EMAIL")  # personal or sprinter-eng-test@guerrillamail.info
ALERT_RECIPIENT_EMAIL = os.getenv("ALERT_RECIPIENT_EMAIL")  #coding-challenges+alerts@sprinterhealth.com