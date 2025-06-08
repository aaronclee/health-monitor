# Clinician Safety Monitor

A service that polls clinician GPS status and sends email alerts when clinicians leave their designated safety zones.

## Start Guide

### 1. Create Virtual Environment
```bash
python -m venv venv
source venv/bin/activate
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Configure Email
Create `.env` file with your SMTP settings:
```bash
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=
SMTP_PASSWORD=
ALERT_SENDER_EMAIL=
ALERT_RECIPIENT_EMAIL=
```

### 4. Run Monitor
```bash
python monitor.py
```

## Architecture

- `monitor.py` - Main monitoring service
- `config.py` - Configuration settings
- `requirements.txt` - Python dependencies
- `README.md` - This documentation

**Flow**: API Poll → Parse GeoJSON → Check Point/Polygon → Track State → Send Alerts
**Safety**: All API failures treated as out-of-zone
