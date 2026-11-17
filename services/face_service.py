# ============================================================
# face_service.py — Face Capture, Encoding & Recognition
# ============================================================
# OPTIMIZATIONS:
# Comment translated to English.
# Comment translated to English.
# Comment translated to English.
#   4. encode_face_from_frame → model="hog" fixed, upsample=0 (fast)
# ============================================================

import cv2
import face_recognition
import pickle
import numpy as np
import os
from datetime import datetime
from database.db_connection import execute_query
from config import (
    FACE_CAPTURE_COUNT,
    FACE_TOLERANCE,
    WEBCAM_INDEX,
    UNKNOWN_FACES_DIR,
)


# ── Encoding Helpers ──────────────────────────────────────────

def encode_face_from_frame(frame_bgr, return_location=False):
    """
     frame  face encoding  .
    ✅ OPT: upsample=0 → faster detection
    ✅ OPT: return_location=True  (encoding, location) tuple 
            → widget  double detection  
    Return: encoding (numpy array)  None
            return_location=True  (encoding, location)  (None, None)
    """
    small = cv2.resize(frame_bgr, (0, 0), fx=0.5, fy=0.5)
    rgb = cv2.cvtColor(small, cv2.COLOR_BGR2RGB)
    locations = face_recognition.face_locations(
        rgb, number_of_times_to_upsample=0, model="hog")
    if not locations:
        return (None, None) if return_location else None
    encodings = face_recognition.face_encodings(rgb, locations, num_jitters=1)
    if not encodings:
        return (None, None) if return_location else None
    enc = encodings[0]
    if return_location:
# Comment translated to English.
        t, r, b, l = locations[0]
        loc_full = (t*2, r*2, b*2, l*2)
        return enc, loc_full
    return enc


def serialize_encoding(encoding: np.ndarray) -> bytes:
    return pickle.dumps(encoding)


def deserialize_encoding(blob: bytes) -> np.ndarray:
    return pickle.loads(blob)


# ── DB Encoding Load ──────────────────────────────────────────

def load_all_encodings(role="student"):
    """
    DB   encoding  query  load .
    ✅ OPT:   user    query  (N+1 problem)
              query →  fast

    Return:
        list of dict: [{"id", "name", "roll"(student only), "encoding"}, ...]
    """
    if role == "student":
        rows = execute_query(
            """SELECT id, roll, name, face_encoding
               FROM users
               WHERE status='approved' AND face_encoding IS NOT NULL""",
            fetch="all"
        )
        result = []
        for row in rows:
            try:
                result.append({
                    "id":       row["id"],
                    "roll":     row["roll"],
                    "name":     row["name"],
                    "encoding": deserialize_encoding(row["face_encoding"]),
                })
            except Exception as e:
                print(
                    f"[FACE] ⚠ Student id={row['id']} encoding load error: {e}")
        return result

    elif role == "teacher":
        rows = execute_query(
            """SELECT id, name, face_encoding
               FROM teachers
               WHERE face_encoding IS NOT NULL""",
            fetch="all"
        )
        result = []
        for row in rows:
            try:
                result.append({
                    "id":       row["id"],
                    "name":     row["name"],
                    "encoding": deserialize_encoding(row["face_encoding"]),
                })
            except Exception as e:
                print(
                    f"[FACE] ⚠ Teacher id={row['id']} encoding load error: {e}")
        return result

    return []


# ── Face Recognition ──────────────────────────────────────────

def recognize_face(frame_bgr, known_people: list):
    """
    Frame  face detect  known_people   match .
    ✅ OPT: location  return  → draw_face_box   detection   

    Return:
        ("matched",  person_dict, location)
        ("unknown",  None, location)
        ("no_face",  None, None)
    """
    if not known_people:
        return "no_face", None, None

# Comment translated to English.
    small = cv2.resize(frame_bgr, (0, 0), fx=0.5, fy=0.5)
    rgb_small = cv2.cvtColor(small, cv2.COLOR_BGR2RGB)

    locations_small = face_recognition.face_locations(
        rgb_small, number_of_times_to_upsample=0, model="hog")

    if not locations_small:
        return "no_face", None, None

    encodings = face_recognition.face_encodings(
        rgb_small, locations_small, num_jitters=1)
    if not encodings:
        return "no_face", None, None

    face_enc = encodings[0]

# Comment translated to English.
    top, right, bottom, left = locations_small[0]
    location_full = (top * 2, right * 2, bottom * 2, left * 2)

    known_encs = [p["encoding"] for p in known_people]
    distances = face_recognition.face_distance(known_encs, face_enc)
    best_idx = int(np.argmin(distances))
    best_dist = distances[best_idx]

    if best_dist <= FACE_TOLERANCE:
        matched = known_people[best_idx]
        print(f"[FACE] ✓ Match: {matched['name']} (dist={best_dist:.3f})")
        return "matched", matched, location_full
    else:
        print(f"[FACE] ✗ Unknown (best dist={best_dist:.3f})")
        return "unknown", None, location_full


# ── Face Box Drawing ──────────────────────────────────────────

def draw_face_box(frame_bgr, label: str = "", color=(0, 255, 0), location=None):
    """
    Frame  face bounding box .
    ✅ OPT: location pass  re-detection   (recognize_face  result reuse)
            location=None    detect  (widget preview  )
    """
    if location is not None:
# Comment translated to English.
        top, right, bottom, left = location
        locations = [(top, right, bottom, left)]
    else:
# Comment translated to English.
        small = cv2.resize(frame_bgr, (0, 0), fx=0.5, fy=0.5)
        rgb = cv2.cvtColor(small, cv2.COLOR_BGR2RGB)
        locs = face_recognition.face_locations(
            rgb, number_of_times_to_upsample=0, model="hog")
# Comment translated to English.
        locations = [(t*2, r*2, b*2, l*2) for (t, r, b, l) in locs]

    for (top, right, bottom, left) in locations:
        cv2.rectangle(frame_bgr, (left, top), (right, bottom), color, 2)
        if label:
            cv2.rectangle(frame_bgr, (left, bottom - 28),
                          (right, bottom), color, cv2.FILLED)
            cv2.putText(frame_bgr, label, (left + 6, bottom - 8),
                        cv2.FONT_HERSHEY_DUPLEX, 0.55, (255, 255, 255), 1)
    return frame_bgr


# ── Unknown Face Logging ──────────────────────────────────────

def save_unknown_face(frame_bgr, page_context: str = "face_scanner"):
    """
    Unknown face screenshot save + DB log.
    """
    try:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        filename = f"unknown_{timestamp}.jpg"
        image_path = os.path.join(UNKNOWN_FACES_DIR, filename)
        cv2.imwrite(image_path, frame_bgr)
        execute_query(
            """INSERT INTO unknown_face_logs (detected_at, image_path, page_context)
               VALUES (NOW(), %s, %s)""",
            (image_path, page_context)
        )
        print(f"[FACE] Unknown face saved: {filename}")
        return image_path
    except Exception as e:
        print(f"[FACE ERROR] save_unknown_face: {e}")
        return None


# ── Capture Function (terminal/test) ─────────────────────────

def capture_face_encoding(progress_callback=None):
    """
    Webcam  FACE_CAPTURE_COUNT  valid frame capture  encoding return .
    Widget   terminal  test  .
    """
    cap = cv2.VideoCapture(WEBCAM_INDEX, cv2.CAP_DSHOW)
    if not cap.isOpened():
        for idx in range(3):
            if idx == WEBCAM_INDEX:
                continue
            cap = cv2.VideoCapture(idx, cv2.CAP_DSHOW)
            if cap.isOpened():
                break
            cap.release()
    if not cap.isOpened():
        return None, "Could not open webcam."

    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

    collected = []
    attempts = 0
    max_attempts = FACE_CAPTURE_COUNT * 10

    while len(collected) < FACE_CAPTURE_COUNT and attempts < max_attempts:
        ret, frame = cap.read()
        if not ret:
            attempts += 1
            continue
        attempts += 1
        enc = encode_face_from_frame(frame)
        if enc is not None:
            collected.append(enc)
            if progress_callback:
                progress_callback(len(collected), FACE_CAPTURE_COUNT, frame)

    cap.release()

    if len(collected) < 20:
        return None, f"Only {len(collected)} valid frames captured — try again in better lighting."

    avg = np.mean(collected, axis=0)
    return serialize_encoding(avg), None


def capture_with_cv2_window():
    """Terminal test."""
    def progress(current, total, frame):
        cv2.putText(frame, f"Captured: {current}/{total}",
                    (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
        cv2.imshow("Face Capture", frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            raise InterruptedError("Cancelled")

    try:
        enc, err = capture_face_encoding(progress_callback=progress)
    except InterruptedError:
        enc, err = None, "User cancelled"
    finally:
        cv2.destroyAllWindows()
    return enc, err


if __name__ == "__main__":
    enc, err = capture_with_cv2_window()
    if err:
        print(f"[ERROR] {err}")
    else:
        print(f"[OK] Encoding ready — {len(enc)/1024:.1f} KB")