# ============================================================
# attendance_service.py — Scan-in / Scan-out Logic
# ============================================================

from datetime import datetime
from database.db_connection import execute_query


# ── Student Scan (identity-based) ────────────────────────────

def student_scan_by_identity(user_id: int, department: str,
                             semester: str, shift: str, phase: str):
    """
    Student dept/sem/shift দিয়ে open session খুঁজে scan করে।
    Return: (action, message, session_id | None)
    """
    # প্রথমে exact shift match চেষ্টা
    session = execute_query(
        """SELECT s.id FROM attendance_sessions s
           JOIN routines r ON s.routine_id = r.id
           WHERE s.session_date = CURDATE()
             AND s.status = 'open'
             AND r.department = %s
             AND r.semester = %s
             AND r.shift = %s
           LIMIT 1""",
        (department, semester, shift), fetch="one"
    )

    # shift match না হলে shift ছাড়াই চেষ্টা (Day/Morning mismatch fix)
    if not session:
        session = execute_query(
            """SELECT s.id FROM attendance_sessions s
               JOIN routines r ON s.routine_id = r.id
               WHERE s.session_date = CURDATE()
                 AND s.status = 'open'
                 AND r.department = %s
                 AND r.semester = %s
               LIMIT 1""",
            (department, semester), fetch="one"
        )

    if not session:
        return "no_session", "⚠️  No active class is available for you at this time.", None

    session_id = session["id"]
    action, msg = student_scan(session_id, user_id, phase)
    return action, msg, session_id


def student_scan(session_id: int, user_id: int, phase: str = "entry"):
    """
    phase="entry" → pending insert
    phase="exit"  → pending → complete update
    """
    record = execute_query(
        """SELECT id, status FROM attendance_records
           WHERE session_id=%s AND user_id=%s""",
        (session_id, user_id), fetch="one"
    )

    if phase == "entry":
        if not record:
            execute_query(
                """INSERT INTO attendance_records
                   (session_id, user_id, scan_in_time, status)
                   VALUES (%s, %s, NOW(), 'pending')""",
                (session_id, user_id)
            )
            return "scan_in", "✅ Entry scan successful! Scan again at class end."

        if record["status"] == "pending":
            return "already_entry", "ℹ️  Entry scan has already been recorded."

        return "already_done", "ℹ️  Today's attendance is already completed."

    elif phase == "exit":
        if not record:
            return "no_entry", "⚠️  Entry scan not found. Attendance was not recorded."

        if record["status"] == "pending":
            execute_query(
                """UPDATE attendance_records
                   SET scan_out_time=NOW(), status='complete'
                   WHERE id=%s""",
                (record["id"],)
            )
            return "scan_out", "✅ Attendance completed!"

        return "already_done", "ℹ️  Today's attendance is already completed."

    return "error", "❌ Unknown phase."


# ── Teacher Scan (identity-based) ─────────────────────────────

def teacher_scan_by_identity(teacher_id: int):
    """
    teacher_id = teachers.id (auto-increment, face recognition থেকে আসে)

    ✅ FIX: routines.teacher_id stores teachers.teacher_id (custom field),
            তাই teachers table JOIN করে t.id দিয়ে match করতে হবে।

    Return: list of (action, message, session_id)
    """
    sessions = execute_query(
        """SELECT s.id, s.routine_id FROM attendance_sessions s
           JOIN routines r ON s.routine_id = r.id
           JOIN teachers t ON r.teacher_id = t.teacher_id
           WHERE t.id = %s
             AND s.session_date = CURDATE()
             AND s.status = 'open'""",
        (teacher_id,), fetch="all"
    )

    if not sessions:
        return [("no_session",
                 "⚠️  No active session is available for you at this time.", None)]

    from services.routine_service import get_active_routines
    active = get_active_routines()
    routine_phase = {r["routine_id"]: r["phase"] for r in active}

    results = []
    for s in sessions:
        sid = s["id"]
        rid = s["routine_id"]
        phase = routine_phase.get(rid, "entry")
        action, msg = teacher_scan(sid, teacher_id, phase)
        results.append((action, msg, sid))
    return results


def teacher_scan(session_id: int, teacher_id: int, phase: str = "entry"):
    """
    phase="entry" → teacher_attendance_records এ pending insert
    phase="exit"  → pending → complete update
    """
    _ensure_teacher_attendance_table()

    record = execute_query(
        """SELECT id, status FROM teacher_attendance_records
           WHERE session_id=%s AND teacher_id=%s""",
        (session_id, teacher_id), fetch="one"
    )

    if phase == "entry":
        if not record:
            execute_query(
                """INSERT INTO teacher_attendance_records
                   (session_id, teacher_id, scan_in_time, status)
                   VALUES (%s, %s, NOW(), 'pending')""",
                (session_id, teacher_id)
            )
            execute_query(
                "UPDATE attendance_sessions SET teacher_scan_in=NOW() WHERE id=%s",
                (session_id,)
            )
            return "teacher_in", "✅ Teacher entry scan successful! Scan again at class end."

        if record["status"] == "pending":
            return "already_entry", "ℹ️  Entry scan has already been recorded."

        return "already_done", "ℹ️  Today's attendance is already completed."

    elif phase == "exit":
        if not record:
            return "no_entry", "⚠️  Entry scan not found."

        if record["status"] == "pending":
            execute_query(
                """UPDATE teacher_attendance_records
                   SET scan_out_time=NOW(), status='complete'
                   WHERE id=%s""",
                (record["id"],)
            )
            execute_query(
                "UPDATE attendance_sessions SET teacher_scan_out=NOW() WHERE id=%s",
                (session_id,)
            )
            return "teacher_out", "✅ Teacher attendance completed!"

        return "already_done", "ℹ️  Today's attendance is already completed."

    return "error", "❌ Unknown phase."


def _ensure_teacher_attendance_table():
    execute_query(
        """CREATE TABLE IF NOT EXISTS teacher_attendance_records (
               id              INT AUTO_INCREMENT PRIMARY KEY,
               session_id      INT NOT NULL,
               teacher_id      INT NOT NULL,
               scan_in_time    DATETIME DEFAULT NULL,
               scan_out_time   DATETIME DEFAULT NULL,
               status          ENUM('pending','complete') DEFAULT 'pending',
               UNIQUE KEY uq_sess_teacher (session_id, teacher_id)
           )""",
        fetch=None
    )


# ── Teacher Attendance Status (for card display) ──────────────

def get_teacher_scan_status(session_id: int, teacher_id: int):
    """
    teacher_id = teachers.id (auto-increment)
    Card এ teacher attendance status দেখানোর জন্য।
    """
    _ensure_teacher_attendance_table()
    return execute_query(
        """SELECT status, scan_in_time, scan_out_time
           FROM teacher_attendance_records
           WHERE session_id=%s AND teacher_id=%s""",
        (session_id, teacher_id), fetch="one"
    )


# ── Session Stats ─────────────────────────────────────────────

def get_session_scan_counts(session_id: int):
    rows = execute_query(
        """SELECT status, COUNT(*) AS cnt
           FROM attendance_records
           WHERE session_id=%s
           GROUP BY status""",
        (session_id,), fetch="all"
    )
    counts = {"pending": 0, "complete": 0}
    for r in (rows or []):
        counts[r["status"]] = r["cnt"]
    counts["total"] = counts["pending"] + counts["complete"]
    return counts
