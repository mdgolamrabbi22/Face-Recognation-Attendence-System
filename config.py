# ============================================================
# config.py — App settings, DB credentials, constants
# ============================================================

import os
from dotenv import load_dotenv

load_dotenv(encoding='utf-8')

# ── Database ──────────────────────────────────────────────────
DB_HOST = os.getenv("DB_HOST",     "localhost")
DB_PORT = int(os.getenv("DB_PORT", "3306"))
DB_USER = os.getenv("DB_USER",     "root")
DB_PASSWORD = os.getenv("DB_PASSWORD", "gr743693")
DB_NAME = os.getenv("DB_NAME",     "face_attendance_db")

# ── App Info ──────────────────────────────────────────────────
APP_NAME = "Face Recognition Attendance System"
APP_VERSION = "1.0.0"
INSTITUTION = "Barishal Polytechnic Institute"

# ── Face Recognition ──────────────────────────────────────────
FACE_CAPTURE_COUNT = 30
FACE_TOLERANCE = 0.5
WEBCAM_INDEX = 0

# ── Multi-Camera (IP Webcam) ───────────────────────────────────
# IP Webcam camera URLs — .env থেকে পড়া হয়।
# .env এ যোগ করো:
#   IP_CAM_1=http://192.168.1.100:8080/video
#   IP_CAM_2=http://192.168.1.101:8080/video
# অথবা সরাসরি নিচে URL লিখে দাও।
# IP_CAM_ROTATE: 0=none, 90=clockwise, 180=flip, 270=counter-clockwise

_raw_cams = [
    os.getenv("IP_CAM_1", "").strip(),   # Mobile/IP cam 1
    os.getenv("IP_CAM_2", "").strip(),   # Mobile/IP cam 2
]
# None বা empty string ফিল্টার করে শুধু valid URL রাখা
EXTRA_CAMERAS = [url for url in _raw_cams if url]

# IP camera থেকে আসা frame rotate করতে চাইলে (ক্যামেরা উল্টা থাকলে)
IP_CAM_ROTATE = int(os.getenv("IP_CAM_ROTATE", "0"))  # 0 / 90 / 180 / 270

# IP camera reconnect করার চেষ্টার সংখ্যা
IP_CAM_RETRY_LIMIT = 5

# ── Paths ─────────────────────────────────────────────────────
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ASSETS_DIR = os.path.join(BASE_DIR, "assets")
UNKNOWN_FACES_DIR = os.path.join(ASSETS_DIR, "unknown_faces")
LOGO_PATH = os.path.join(ASSETS_DIR, "logo.png")

# ── Splash Screen ─────────────────────────────────────────────
SPLASH_DURATION_MS = 3500

# ── UI Theme ──────────────────────────────────────────────────
APPEARANCE_MODE = "dark"
COLOR_THEME = "blue"

# Comment translated to English.
os.makedirs(UNKNOWN_FACES_DIR, exist_ok=True)
os.makedirs(ASSETS_DIR,        exist_ok=True)
