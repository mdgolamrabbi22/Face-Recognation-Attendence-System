# ============================================================
# routine_service.py — Active Routine Time Matching
# ============================================================
#   Entry Phase = class_start → class_start + 10 min
#   Exit Phase  = class_end - 10 min → class_end
# ============================================================

from datetime import datetime, time, timedelta
from database.db_connection import execute_query

ENTRY_WINDOW_MIN = 10
EXIT_WINDOW_MIN = 10

DAYS = {
    0: "Monday", 1: "Tuesday", 2: "Wednesday",
    3: "Thursday", 4: "Friday", 5: "Saturday", 6: "Sunday",
}


def _to_time(val):
    if isinstance(val, time):
        return val
    total_seconds = int(val.total_seconds())
    h = total_seconds // 3600
    m = (total_seconds % 3600) // 60
    s = total_seconds % 60
    return time(h, m, s)


def _add_minutes(t: time, minutes: int) -> time:
    dt = datetime(2000, 1, 1, t.hour, t.minute, t.second)
    dt += timedelta(minutes=minutes)
    return dt.time()


def _build_routine_dict(row, phase, entry_start, entry_end, exit_start, exit_end,
                        scan_start, scan_end):
    return {
        "routine_id":   row["id"],
        "department":   row["department"],
        "semester":     row["semester"],
        "subject":      row["subject"],
        "shift":        row.get("shift", "morning"),
        "teacher_id":   row["teacher_id"],
        "teacher_name": row["teacher_name"] or "—",
        "class_start":  _to_time(row["class_start"]).strftime("%I:%M %p"),
        "class_end":    _to_time(row["class_end"]).strftime("%I:%M %p"),
        "scan_start":   scan_start.strftime("%I:%M %p"),
        "scan_end":     scan_end.strftime("%I:%M %p"),
        "entry_start":  entry_start,
        "entry_end":    entry_end,
        "exit_start":   exit_start,
        "exit_end":     exit_end,
        "phase":        phase,
    }


def get_active_routines(now: datetime = None) -> list:
    if now is None:
        now = datetime.now()

    today = DAYS.get(now.weekday())
    now_time = now.time()

    rows = execute_query(
        """SELECT r.id, r.department, r.semester, r.day, r.subject,
                  r.class_start, r.class_end, r.shift,
                  t.id AS teacher_id, t.name AS teacher_name
           FROM routines r
           LEFT JOIN teachers t ON r.teacher_id = t.teacher_id
           WHERE r.day = %s
             AND r.id IS NOT NULL""",
        (today,), fetch="all"
    )

    active = []
    for row in rows:
        class_start = _to_time(row["class_start"])
        class_end = _to_time(row["class_end"])

        entry_start = class_start
        entry_end = _add_minutes(class_start, ENTRY_WINDOW_MIN)
        exit_start = _add_minutes(class_end, -EXIT_WINDOW_MIN)
        exit_end = class_end

        if entry_start <= now_time <= entry_end:
            phase = "entry"
            active.append(_build_routine_dict(
                row, phase, entry_start, entry_end,
                exit_start, exit_end, entry_start, entry_end))

        elif exit_start <= now_time <= exit_end:
            phase = "exit"
            active.append(_build_routine_dict(
                row, phase, entry_start, entry_end,
                exit_start, exit_end, exit_start, exit_end))

        elif entry_end < now_time < exit_start:
            phase = "between"
            active.append(_build_routine_dict(
                row, phase, entry_start, entry_end,
                exit_start, exit_end, entry_start, exit_end))

    return active


def get_active_routine(now: datetime = None):
    """Backward compat — returns first active routine."""
    routines = get_active_routines(now)
    return routines[0] if routines else None


def get_todays_all_routines(now: datetime = None) -> list:
    """Returns all of today's routines regardless of active status."""
    if now is None:
        now = datetime.now()

    today = DAYS.get(now.weekday())

    rows = execute_query(
        """SELECT r.id, r.department, r.semester, r.day, r.subject,
                  r.class_start, r.class_end, r.shift,
                  t.id AS teacher_id, t.name AS teacher_name
           FROM routines r
           LEFT JOIN teachers t ON r.teacher_id = t.teacher_id
           WHERE r.day = %s
             AND r.id IS NOT NULL""",
        (today,), fetch="all"
    )

    result = []
    for row in rows:
        class_start = _to_time(row["class_start"])
        class_end = _to_time(row["class_end"])

        entry_start = class_start
        entry_end = _add_minutes(class_start, ENTRY_WINDOW_MIN)
        exit_start = _add_minutes(class_end, -EXIT_WINDOW_MIN)
        exit_end = class_end

        now_time = now.time()
        if entry_start <= now_time <= entry_end:
            phase = "entry"
        elif exit_start <= now_time <= exit_end:
            phase = "exit"
        elif entry_end < now_time < exit_start:
            phase = "between"
        else:
            phase = "done"

        result.append(_build_routine_dict(
            row, phase, entry_start, entry_end,
            exit_start, exit_end, entry_start, exit_end))

    return result


def get_or_create_session(routine_id: int, teacher_id: int, subject: str):
    existing = execute_query(
        """SELECT id FROM attendance_sessions
           WHERE routine_id=%s AND session_date=CURDATE()
           ORDER BY id DESC LIMIT 1""",
        (routine_id,), fetch="one"
    )
    if existing:
        return existing["id"]

    return execute_query(
        """INSERT INTO attendance_sessions
           (routine_id, teacher_id, session_date, subject, status)
           VALUES (%s, %s, CURDATE(), %s, 'open')""",
        (routine_id, teacher_id, subject)
    )


def close_session(session_id: int):
    execute_query(
        "UPDATE attendance_sessions SET status='closed' WHERE id=%s",
        (session_id,)
    )
