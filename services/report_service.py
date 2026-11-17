# ============================================================
# report_service.py — CSV & PDF Report Generation
# ============================================================
# Comment translated to English.
# Comment translated to English.
# Comment translated to English.
# ============================================================

import os
import pandas as pd
from datetime import datetime

from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle, Paragraph,
    Spacer, HRFlowable,
)
from reportlab.lib.enums import TA_CENTER, TA_LEFT

from models.report_model import (get_all_reports, get_report_detail,
                                 get_teacher_attendance_detail, get_absent_students)


# ── Shared color palette ──────────────────────────────────────
C_BG_HEADER = colors.HexColor("#1f6feb")
C_TEACHER_HDR = colors.HexColor("#6e40c9")   # purple — teacher section
C_PENDING_BG = colors.HexColor("#2d2006")
C_PENDING_TXT = colors.HexColor("#e3b341")
C_GREEN = colors.HexColor("#238636")
C_RED = colors.HexColor("#f85149")
C_LIGHT_ROW = colors.HexColor("#f6f8fa")
C_WHITE = colors.white
C_DARK = colors.HexColor("#24292f")
C_MUTED = colors.HexColor("#57606a")


def _base_pdf_styles():
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "PDFTitle", fontName="Helvetica-Bold", fontSize=16,
        textColor=C_DARK, spaceAfter=4, alignment=TA_CENTER)
    sub_style = ParagraphStyle(
        "PDFSub", fontName="Helvetica", fontSize=9,
        textColor=C_MUTED, spaceAfter=2, alignment=TA_CENTER)
    section_style = ParagraphStyle(
        "PDFSection", fontName="Helvetica-Bold", fontSize=10,
        textColor=C_DARK, spaceBefore=10, spaceAfter=4)
    return title_style, sub_style, section_style


def _status_color(status: str):
    return C_GREEN if status.upper() == "COMPLETE" else C_PENDING_TXT


def _pct_color(pct: int):
    if pct >= 75:
        return C_GREEN
    elif pct >= 60:
        return C_PENDING_TXT
    return C_RED


def _is_absent_row(row: dict) -> bool:
    return row.get("scan_in_time") is None and row.get("scan_out_time") is None


def _split_student_rows(rows: list):
    absent_rows = [r for r in rows if _is_absent_row(r)]
    pending_rows = [
        r for r in rows
        if not _is_absent_row(r) and r.get("status") == "pending"
    ]
    complete_rows = [
        r for r in rows
        if not _is_absent_row(r) and r.get("status") == "complete"
    ]
    scanned_rows = [r for r in rows if not _is_absent_row(r)]
    return scanned_rows, pending_rows, complete_rows, absent_rows


# ── Teacher Attendance PDF block ──────────────────────────────

def _teacher_attendance_block(story, session_id: int):
    """
    Teacher attendance  section  story  append .
    session_id  teacher record   'Not Scanned' .
    """
    rec = get_teacher_attendance_detail(session_id)

    story.append(Paragraph(
        "Teacher Attendance",
        ParagraphStyle("tchhdr", fontName="Helvetica-Bold",
                       fontSize=9, textColor=C_TEACHER_HDR,
                       spaceBefore=8, spaceAfter=3)))

    if rec is None:
        story.append(Paragraph(
            "⚠  Teacher has not scanned.",
            ParagraphStyle("tno", fontName="Helvetica",
                           fontSize=8, textColor=C_PENDING_TXT,
                           spaceAfter=4)))
        return

    sin = str(rec["scan_in_time"])[11:16] if rec["scan_in_time"] else "—"
    sout = str(rec["scan_out_time"])[11:16] if rec["scan_out_time"] else "—"
    status = rec["status"].upper()
    sc = C_GREEN if status == "COMPLETE" else C_PENDING_TXT

    tbl_data = [
        ["Teacher Name", "Scan In", "Scan Out", "Status"],
        [rec["name"], sin, sout, status],
    ]
    tbl = Table(tbl_data,
                colWidths=[70*mm, 35*mm, 35*mm, 35*mm])
    tbl.setStyle(TableStyle([
        ("BACKGROUND",  (0, 0), (-1, 0), C_TEACHER_HDR),
        ("TEXTCOLOR",   (0, 0), (-1, 0), C_WHITE),
        ("FONTNAME",    (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE",    (0, 0), (-1, 0), 8),
        ("FONTNAME",    (0, 1), (-1, 1), "Helvetica-Bold"),
        ("FONTSIZE",    (0, 1), (-1, 1), 9),
        ("TEXTCOLOR",   (3, 1), (3, 1), sc),
        ("ALIGN",       (0, 0), (-1, -1), "CENTER"),
        ("VALIGN",      (0, 0), (-1, -1), "MIDDLE"),
        ("ROWBACKGROUNDS", (0, 1), (-1, 1), [C_LIGHT_ROW]),
        ("GRID",        (0, 0), (-1, -1), 0.3,
         colors.HexColor("#d0d7de")),
        ("TOPPADDING",    (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    story.append(tbl)
    story.append(Spacer(1, 6))


# ════════════════════════════════════════════════════════════
# 1.  Single Session PDF
# ════════════════════════════════════════════════════════════

def export_session_pdf(session_id: int, subject: str,
                       session_date, teacher_name: str = "",
                       save_dir: str = None) -> str:
    if save_dir is None:
        save_dir = os.path.join(os.path.expanduser("~"), "Downloads")
    os.makedirs(save_dir, exist_ok=True)

    rows = get_report_detail(session_id)
    if not rows:
        raise ValueError(
            "No attendance records found for this session. Please scan face first.")

    date_str = str(session_date).replace("-", "")
    subject_str = subject.replace(" ", "_")[:20]
    filename = f"attendance_{subject_str}_{date_str}.pdf"
    filepath = os.path.join(save_dir, filename)

    doc = SimpleDocTemplate(
        filepath, pagesize=landscape(A4),
        leftMargin=15*mm, rightMargin=15*mm,
        topMargin=15*mm,  bottomMargin=15*mm)

    title_style, sub_style, section_style = _base_pdf_styles()
    story = []

    # ── Header ────────────────────────────────────────────────
    story.append(Paragraph("Attendance Report", title_style))
    story.append(Paragraph(
        f"Subject: {subject}   |   Date: {session_date}   |   Teacher: {teacher_name or '—'}",
        sub_style))
    story.append(HRFlowable(width="100%", thickness=1,
                            color=C_BG_HEADER, spaceAfter=8))

    # ── Summary ───────────────────────────────────────────────
    scanned_rows, pending_rows, complete_rows, absent_list = _split_student_rows(rows)
    complete_ct = len(complete_rows)
    pending_ct = len(pending_rows)
    absent_ct = len(absent_list)

    total_scanned = len(scanned_rows)
    total_ct = total_scanned + absent_ct
    pct = round(complete_ct / total_ct * 100) if total_ct else 0

    summary_data = [
        ["Total Students", "Present", "Pending", "Absent", "Attendance %"],
        [str(total_ct), str(complete_ct), str(pending_ct), str(absent_ct), f"{pct}%"],
    ]
    summary_tbl = Table(summary_data, colWidths=[48*mm]*5)
    summary_tbl.setStyle(TableStyle([
        ("BACKGROUND",  (0, 0), (-1, 0), C_BG_HEADER),
        ("TEXTCOLOR",   (0, 0), (-1, 0), C_WHITE),
        ("FONTNAME",    (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE",    (0, 0), (-1, 0), 9),
        ("FONTNAME",    (0, 1), (-1, 1), "Helvetica-Bold"),
        ("FONTSIZE",    (0, 1), (-1, 1), 14),
        ("TEXTCOLOR",   (1, 1), (1, 1), C_GREEN),
        ("TEXTCOLOR",   (2, 1), (2, 1),
         C_PENDING_TXT if pending_ct else C_MUTED),
        ("TEXTCOLOR",   (3, 1), (3, 1), C_RED if absent_ct else C_MUTED),
        ("TEXTCOLOR",   (4, 1), (4, 1), _pct_color(pct)),
        ("ALIGN",       (0, 0), (-1, -1), "CENTER"),
        ("VALIGN",      (0, 0), (-1, -1), "MIDDLE"),
        ("ROWBACKGROUNDS", (0, 1), (-1, 1), [C_LIGHT_ROW]),
        ("GRID",        (0, 0), (-1, -1), 0.4,
         colors.HexColor("#d0d7de")),
        ("TOPPADDING",  (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(summary_tbl)
    story.append(Spacer(1, 8))

    # ── Teacher Attendance Section ────────────────────────────
    _teacher_attendance_block(story, session_id)

    # ── Student Attendance Table ──────────────────────────────
    col_headers = ["#", "Roll", "Name", "Department",
                   "Sem", "Scan In", "Scan Out", "Status"]
    col_widths = [10*mm, 22*mm, 52*mm, 50*mm,
                  14*mm, 28*mm, 28*mm, 24*mm]

    def _make_detail_table(row_list, header_bg):
        data = [col_headers]
        for i, r in enumerate(row_list, start=1):
            sin = str(r["scan_in_time"])[11:16] if r["scan_in_time"] else "—"
            sout = str(r["scan_out_time"])[
                11:16] if r["scan_out_time"] else "—"
            data.append([str(i), r["roll"], r["name"],
                         r["department"], r["semester"],
                         sin, sout, r["status"].upper()])

        tbl = Table(data, colWidths=col_widths, repeatRows=1)
        style_cmds = [
            ("BACKGROUND",    (0, 0), (-1, 0),  header_bg),
            ("TEXTCOLOR",     (0, 0), (-1, 0),  C_WHITE),
            ("FONTNAME",      (0, 0), (-1, 0),  "Helvetica-Bold"),
            ("FONTSIZE",      (0, 0), (-1, 0),  8),
            ("ALIGN",         (0, 0), (-1, 0),  "CENTER"),
            ("FONTNAME",      (0, 1), (-1, -1), "Helvetica"),
            ("FONTSIZE",      (0, 1), (-1, -1), 8),
            ("ALIGN",         (0, 1), (1, -1),  "CENTER"),
            ("ALIGN",         (7, 1), (7, -1),  "CENTER"),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [C_WHITE, C_LIGHT_ROW]),
            ("GRID",          (0, 0), (-1, -1),  0.3,
             colors.HexColor("#d0d7de")),
            ("TOPPADDING",    (0, 0), (-1, -1),  4),
            ("BOTTOMPADDING", (0, 0), (-1, -1),  4),
            ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
        ]
        for row_idx, r in enumerate(row_list, start=1):
            sc = C_GREEN if r["status"] == "complete" else C_PENDING_TXT
            style_cmds += [
                ("TEXTCOLOR", (7, row_idx), (7, row_idx), sc),
                ("FONTNAME",  (7, row_idx), (7, row_idx), "Helvetica-Bold"),
            ]
        tbl.setStyle(TableStyle(style_cmds))
        return tbl

    if pending_rows:
        story.append(Paragraph(
            f"⚠  Pending — {len(pending_rows)} student(s) have not scanned out",
            ParagraphStyle("warn", fontName="Helvetica-Bold",
                           fontSize=9, textColor=C_PENDING_TXT,
                           spaceBefore=4, spaceAfter=3)))
        story.append(_make_detail_table(pending_rows,
                                        header_bg=colors.HexColor("#4d3a07")))
        story.append(Spacer(1, 8))

    if complete_rows:
        story.append(Paragraph(
            f"✓  Complete — {len(complete_rows)} student(s)",
            ParagraphStyle("ok", fontName="Helvetica-Bold",
                           fontSize=9, textColor=C_GREEN,
                           spaceBefore=4, spaceAfter=3)))
        story.append(_make_detail_table(complete_rows,
                                        header_bg=C_BG_HEADER))

    # ── Absent Students Section ────────────────────────────────
    if absent_list:
        story.append(Paragraph(
            f"✖  Absent — {len(absent_list)} student(s)",
            ParagraphStyle("absent", fontName="Helvetica-Bold",
                           fontSize=9, textColor=C_RED,
                           spaceBefore=8, spaceAfter=3)))
        
        absent_headers = ["#", "Roll", "Name", "Department", "Sem", "Status"]
        absent_widths = [10*mm, 30*mm, 80*mm, 60*mm, 20*mm, 40*mm]
        
        abs_data = [absent_headers]
        for i, r in enumerate(absent_list, start=1):
            abs_data.append([str(i), r["roll"], r["name"], 
                             r["department"], r["semester"], "ABSENT"])
            
        abs_tbl = Table(abs_data, colWidths=absent_widths)
        abs_tbl.setStyle(TableStyle([
            ("BACKGROUND",    (0, 0), (-1, 0),  C_RED),
            ("TEXTCOLOR",     (0, 0), (-1, 0),  C_WHITE),
            ("FONTNAME",      (0, 0), (-1, 0),  "Helvetica-Bold"),
            ("FONTSIZE",      (0, 0), (-1, 0),  8),
            ("ALIGN",         (0, 0), (-1, 0),  "CENTER"),
            ("FONTNAME",      (0, 1), (-1, -1), "Helvetica"),
            ("FONTSIZE",      (0, 1), (-1, -1), 8),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [C_WHITE, C_LIGHT_ROW]),
            ("GRID",          (0, 0), (-1, -1),  0.3, colors.HexColor("#d0d7de")),
            ("TEXTCOLOR",     (5, 1), (5, -1),   C_RED),
            ("FONTNAME",      (5, 1), (5, -1),   "Helvetica-Bold"),
            ("ALIGN",         (0, 0), (1, -1),   "CENTER"),
            ("ALIGN",         (4, 0), (5, -1),   "CENTER"),
        ]))
        story.append(abs_tbl)

    # ── Footer ────────────────────────────────────────────────
    story.append(Spacer(1, 8))
    story.append(HRFlowable(width="100%", thickness=0.5,
                            color=colors.HexColor("#d0d7de")))
    story.append(Paragraph(
        f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        ParagraphStyle("footer", fontName="Helvetica",
                       fontSize=7, textColor=C_MUTED,
                       alignment=TA_LEFT, spaceBefore=3)))

    doc.build(story)
    return filepath


# ════════════════════════════════════════════════════════════
# 2.  Filtered (Multiple Sessions) PDF
# ════════════════════════════════════════════════════════════

def export_filtered_pdf(reports: list, save_dir: str = None) -> str:
    if save_dir is None:
        save_dir = os.path.join(os.path.expanduser("~"), "Downloads")
    os.makedirs(save_dir, exist_ok=True)

    if not reports:
        raise ValueError("No reports found.")

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    subj = reports[0]["subject"].replace(" ", "_")[:15]
    filename = f"report_{subj}_{ts}.pdf"
    filepath = os.path.join(save_dir, filename)

    doc = SimpleDocTemplate(
        filepath, pagesize=landscape(A4),
        leftMargin=15*mm, rightMargin=15*mm,
        topMargin=15*mm,  bottomMargin=15*mm)

    title_style, sub_style, section_style = _base_pdf_styles()
    story = []

    # ── Cover ─────────────────────────────────────────────────
    first = reports[0]
    story.append(Paragraph("Attendance Report", title_style))
    story.append(Paragraph(
        f"Subject: {first['subject']}   |   "
        f"Department: {first.get('department', '')}   |   "
        f"Semester: {first.get('semester', '')}   |   "
        f"Shift: {first.get('shift', '')}",
        sub_style))
    story.append(HRFlowable(width="100%", thickness=1,
                            color=C_BG_HEADER, spaceAfter=8))

    # Overall summary
    total_sessions = len(reports)
    total_attended = sum((r.get("attended") or 0) for r in reports)
    total_scanned = sum((r.get("total_scanned") or 0) for r in reports)
    overall_pct = round(total_attended / total_scanned * 100) \
        if total_scanned else 0

    ov_data = [
        ["Total Sessions", "Total Present", "Total Scanned", "Overall %"],
        [str(total_sessions), str(total_attended),
         str(total_scanned),  f"{overall_pct}%"],
    ]
    ov_tbl = Table(ov_data, colWidths=[60*mm]*4)
    ov_tbl.setStyle(TableStyle([
        ("BACKGROUND",  (0, 0), (-1, 0), C_BG_HEADER),
        ("TEXTCOLOR",   (0, 0), (-1, 0), C_WHITE),
        ("FONTNAME",    (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE",    (0, 0), (-1, 0), 9),
        ("FONTNAME",    (0, 1), (-1, 1), "Helvetica-Bold"),
        ("FONTSIZE",    (0, 1), (-1, 1), 14),
        ("TEXTCOLOR",   (1, 1), (1, 1), C_GREEN),
        ("TEXTCOLOR",   (3, 1), (3, 1), _pct_color(overall_pct)),
        ("ALIGN",       (0, 0), (-1, -1), "CENTER"),
        ("VALIGN",      (0, 0), (-1, -1), "MIDDLE"),
        ("ROWBACKGROUNDS", (0, 1), (-1, 1), [C_LIGHT_ROW]),
        ("GRID",        (0, 0), (-1, -1), 0.4,
         colors.HexColor("#d0d7de")),
        ("TOPPADDING",  (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(ov_tbl)
    story.append(Spacer(1, 14))

    # Session index table
    story.append(Paragraph("Session Summary", section_style))
    idx_data = [["#", "Date", "Teacher", "Present",
                 "Pending", "Absent", "Total", "%", "Teacher Status"]]
    for i, rep in enumerate(reports, start=1):
        att = rep.get("attended") or 0
        tot = rep.get("total_scanned") or 0
        pen = rep.get("pending_count") or 0
        abs_ct = len(get_absent_students(rep["session_id"]))
        total_all = tot + abs_ct
        pct = round(att / total_all * 100) if total_all else 0
        t_rec = get_teacher_attendance_detail(rep["session_id"])
        t_status = t_rec["status"].upper() if t_rec and t_rec.get("status") else "NOT SCANNED"

        idx_data.append([
            str(i), str(rep["session_date"]),
            rep["teacher_name"] or "—",
            str(att), str(pen), str(abs_ct), str(total_all), f"{pct}%",
            t_status,
        ])

    idx_tbl = Table(
        idx_data,
        colWidths=[10*mm, 25*mm, 45*mm, 18*mm,
                   18*mm, 18*mm, 18*mm, 18*mm, 30*mm])
    idx_style = [
        ("BACKGROUND",   (0, 0), (-1, 0), C_BG_HEADER),
        ("TEXTCOLOR",    (0, 0), (-1, 0), C_WHITE),
        ("FONTNAME",     (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE",     (0, 0), (-1, -1), 8),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [C_WHITE, C_LIGHT_ROW]),
        ("GRID",         (0, 0), (-1, -1), 0.3,
         colors.HexColor("#d0d7de")),
        ("ALIGN",        (0, 0), (0, -1), "CENTER"),
        ("ALIGN",        (3, 0), (6, -1), "CENTER"),
        ("TOPPADDING",   (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]
    for i, rep in enumerate(reports, start=1):
        att = rep.get("attended") or 0
        tot = rep.get("total_scanned") or 0
        pen = rep.get("pending_count") or 0
        
        abs_list = get_absent_students(rep["session_id"])
        abs_ct = len(abs_list)
        total_all = tot + abs_ct
        pct = round(att / total_all * 100) if total_all else 0
        
        idx_style.append(("TEXTCOLOR", (7, i), (7, i), _pct_color(pct)))
        if pen > 0:
            idx_style.append(("TEXTCOLOR", (4, i), (4, i), C_PENDING_TXT))
        if abs_ct > 0:
            idx_style.append(("TEXTCOLOR", (5, i), (5, i), C_RED))
            
        # Teacher status color
        t_rec = get_teacher_attendance_detail(rep["session_id"])
        if t_rec and t_rec["status"] == "complete":
            idx_style.append(("TEXTCOLOR", (8, i), (8, i), C_GREEN))
        else:
            idx_style.append(("TEXTCOLOR", (8, i), (8, i), C_PENDING_TXT))
    idx_tbl.setStyle(TableStyle(idx_style))
    story.append(idx_tbl)

    # ── Per-session detail ────────────────────────────────────
    col_headers = ["#", "Roll", "Name", "Department",
                   "Sem", "Scan In", "Scan Out", "Status"]
    col_widths = [10*mm, 22*mm, 52*mm, 50*mm,
                  14*mm, 28*mm, 28*mm, 24*mm]

    for rep_idx, rep in enumerate(reports, start=1):
        att = rep.get("attended") or 0
        tot = rep.get("total_scanned") or 0
        detail = get_report_detail(rep["session_id"])
        scanned_rows, pending_rows, complete_rows, absent_list = _split_student_rows(detail)
        absent_ct = len(absent_list)
        total_all = tot + absent_ct
        pct = round(att / total_all * 100) if total_all else 0

        story.append(Spacer(1, 14))
        story.append(HRFlowable(width="100%", thickness=0.5,
                                color=colors.HexColor("#d0d7de")))
        story.append(Paragraph(
            f"Session {rep_idx}  —  {rep['session_date']}  "
            f"|  Teacher: {rep['teacher_name'] or '—'}  "
            f"|  Present: {att}/{total_all}  ({pct}%)  "
            f"|  Absent: {absent_ct}",
            ParagraphStyle(
                "sesshdr", fontName="Helvetica-Bold",
                fontSize=9, textColor=C_DARK,
                spaceBefore=6, spaceAfter=4)))

        # Teacher attendance block
        _teacher_attendance_block(story, rep["session_id"])

        # Student detail
        if not detail:
            story.append(Paragraph(
                "No student records found.",
                ParagraphStyle("nr", fontSize=8, textColor=C_MUTED)))
            continue

        data = [col_headers]
        detail_rows = pending_rows + complete_rows
        for i, r in enumerate(detail_rows, start=1):
            sin = str(r["scan_in_time"])[11:16] if r["scan_in_time"] else "—"
            sout = str(r["scan_out_time"])[
                11:16] if r["scan_out_time"] else "—"
            data.append([str(i), r["roll"], r["name"],
                         r["department"], r["semester"],
                         sin, sout, r["status"].upper()])

        tbl = Table(data, colWidths=col_widths, repeatRows=1)
        style_cmds = [
            ("BACKGROUND",    (0, 0), (-1, 0),  C_BG_HEADER),
            ("TEXTCOLOR",     (0, 0), (-1, 0),  C_WHITE),
            ("FONTNAME",      (0, 0), (-1, 0),  "Helvetica-Bold"),
            ("FONTSIZE",      (0, 0), (-1, 0),  8),
            ("ALIGN",         (0, 0), (-1, 0),  "CENTER"),
            ("FONTNAME",      (0, 1), (-1, -1), "Helvetica"),
            ("FONTSIZE",      (0, 1), (-1, -1), 8),
            ("ALIGN",         (0, 1), (1, -1),  "CENTER"),
            ("ALIGN",         (7, 1), (7, -1),  "CENTER"),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [C_WHITE, C_LIGHT_ROW]),
            ("GRID",          (0, 0), (-1, -1),  0.3,
             colors.HexColor("#d0d7de")),
            ("TOPPADDING",    (0, 0), (-1, -1),  3),
            ("BOTTOMPADDING", (0, 0), (-1, -1),  3),
            ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
        ]
        for row_i, r in enumerate(detail_rows, start=1):
            sc = C_GREEN if r["status"] == "complete" else C_PENDING_TXT
            style_cmds += [
                ("TEXTCOLOR", (7, row_i), (7, row_i), sc),
                ("FONTNAME",  (7, row_i), (7, row_i), "Helvetica-Bold"),
            ]
        tbl.setStyle(TableStyle(style_cmds))
        story.append(tbl)

        # Absent list per session
        if absent_list:
            story.append(Paragraph(
                f"✖  Absent — {len(absent_list)} student(s)",
                ParagraphStyle("absent_sub", fontName="Helvetica-Bold",
                               fontSize=8, textColor=C_RED,
                               spaceBefore=4, spaceAfter=2)))
            
            abs_data = [["#", "Roll", "Name", "Department", "Sem", "Status"]]
            for i, r in enumerate(absent_list, start=1):
                abs_data.append([str(i), r["roll"], r["name"], 
                                 r["department"], r["semester"], "ABSENT"])
            
            abs_tbl = Table(abs_data, colWidths=[10*mm, 25*mm, 60*mm, 50*mm, 15*mm, 30*mm])
            abs_tbl.setStyle(TableStyle([
                ("BACKGROUND",    (0, 0), (-1, 0),  C_RED),
                ("TEXTCOLOR",     (0, 0), (-1, 0),  C_WHITE),
                ("FONTNAME",      (0, 0), (-1, 0),  "Helvetica-Bold"),
                ("FONTSIZE",      (0, 0), (-1, 0),  7),
                ("ALIGN",         (0, 0), (-1, 0),  "CENTER"),
                ("FONTNAME",      (0, 1), (-1, -1), "Helvetica"),
                ("FONTSIZE",      (0, 1), (-1, -1), 7),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [C_WHITE, C_LIGHT_ROW]),
                ("GRID",          (0, 0), (-1, -1),  0.3, colors.HexColor("#d0d7de")),
                ("TEXTCOLOR",     (5, 1), (5, -1),   C_RED),
                ("FONTNAME",      (5, 1), (5, -1),   "Helvetica-Bold"),
                ("ALIGN",         (0, 0), (1, -1),   "CENTER"),
                ("ALIGN",         (4, 0), (5, -1),   "CENTER"),
            ]))
            story.append(abs_tbl)

    # Footer
    story.append(Spacer(1, 10))
    story.append(HRFlowable(width="100%", thickness=0.5,
                            color=colors.HexColor("#d0d7de")))
    story.append(Paragraph(
        f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        ParagraphStyle("footer", fontName="Helvetica",
                       fontSize=7, textColor=C_MUTED,
                       alignment=TA_LEFT, spaceBefore=3)))

    doc.build(story)
    return filepath


# ════════════════════════════════════════════════════════════
# CSV helpers
# ════════════════════════════════════════════════════════════

def export_session_csv(session_id: int, subject: str,
                       session_date, save_dir: str = None) -> str:
    """ session  CSV. Teacher attendance  row ."""
    if save_dir is None:
        save_dir = os.path.join(os.path.expanduser("~"), "Downloads")
    os.makedirs(save_dir, exist_ok=True)

    rows = get_report_detail(session_id)
    if not rows:
        raise ValueError("No attendance records found for this session.")

    # Teacher row
    t_rec = get_teacher_attendance_detail(session_id)
    records = []

    if t_rec:
        records.append({
            "Type":       "TEACHER",
            "Roll":       "—",
            "Name":       t_rec["name"],
            "Department": "—",
            "Semester":   "—",
            "Scan In":    str(t_rec["scan_in_time"])[11:16] if t_rec["scan_in_time"] else "—",
            "Scan Out":   str(t_rec["scan_out_time"])[11:16] if t_rec["scan_out_time"] else "—",
            "Status":     t_rec["status"].upper(),
        })

    for r in rows:
        records.append({
            "Type":       "STUDENT",
            "Roll":       r["roll"],
            "Name":       r["name"],
            "Department": r["department"],
            "Semester":   r["semester"],
            "Scan In":    str(r["scan_in_time"]) if r["scan_in_time"] else "—",
            "Scan Out":   str(r["scan_out_time"]) if r["scan_out_time"] else "—",
            "Status":     r["status"].upper(),
        })

    df = pd.DataFrame(records)
    date_str = str(session_date).replace("-", "")
    subject_str = subject.replace(" ", "_")[:20]
    filename = f"attendance_{subject_str}_{date_str}.csv"
    filepath = os.path.join(save_dir, filename)
    df.to_csv(filepath, index=False, encoding="utf-8-sig")
    return filepath


def export_filtered_csv(reports: list, save_dir: str = None) -> str:
    """Filter  multiple sessions → combined CSV. Teacher row  include."""
    if save_dir is None:
        save_dir = os.path.join(os.path.expanduser("~"), "Downloads")
    os.makedirs(save_dir, exist_ok=True)

    if not reports:
        raise ValueError("No reports found.")

    all_records = []
    for rep in reports:
        # Teacher row
        t_rec = get_teacher_attendance_detail(rep["session_id"])
        if t_rec:
            all_records.append({
                "Date":       str(rep["session_date"]),
                "Subject":    rep["subject"],
                "Department": rep.get("department", ""),
                "Semester":   rep.get("semester", ""),
                "Shift":      rep.get("shift", ""),
                "Type":       "TEACHER",
                "Roll":       "—",
                "Name":       t_rec["name"],
                "Scan In":    str(t_rec["scan_in_time"])[11:16] if t_rec["scan_in_time"] else "—",
                "Scan Out":   str(t_rec["scan_out_time"])[11:16] if t_rec["scan_out_time"] else "—",
                "Status":     t_rec["status"].upper(),
            })

        # Student rows
        details = get_report_detail(rep["session_id"])
        for r in details:
            all_records.append({
                "Date":       str(rep["session_date"]),
                "Subject":    rep["subject"],
                "Department": rep.get("department", ""),
                "Semester":   rep.get("semester", ""),
                "Shift":      rep.get("shift", ""),
                "Type":       "STUDENT",
                "Roll":       r["roll"],
                "Name":       r["name"],
                "Scan In":    str(r["scan_in_time"]) if r["scan_in_time"] else "—",
                "Scan Out":   str(r["scan_out_time"]) if r["scan_out_time"] else "—",
                "Status":     r["status"].upper(),
            })

    df = pd.DataFrame(all_records)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    subj = reports[0]["subject"].replace(" ", "_")[:15]
    filename = f"report_{subj}_{ts}.csv"
    filepath = os.path.join(save_dir, filename)
    df.to_csv(filepath, index=False, encoding="utf-8-sig")
    return filepath


def export_all_csv(save_dir: str = None) -> str:
    """ session  combined CSV."""
    if save_dir is None:
        save_dir = os.path.join(os.path.expanduser("~"), "Downloads")
    os.makedirs(save_dir, exist_ok=True)

    reports = get_all_reports()
    if not reports:
        raise ValueError("No reports found.")

    all_records = []
    for rep in reports:
        t_rec = get_teacher_attendance_detail(rep["session_id"])
        if t_rec:
            all_records.append({
                "Date":       str(rep["session_date"]),
                "Subject":    rep["subject"],
                "Teacher":    rep["teacher_name"] or "—",
                "Type":       "TEACHER",
                "Roll":       "—",
                "Name":       t_rec["name"],
                "Department": "—",
                "Semester":   "—",
                "Status":     t_rec["status"].upper(),
            })
        details = get_report_detail(rep["session_id"])
        for r in details:
            all_records.append({
                "Date":       str(rep["session_date"]),
                "Subject":    rep["subject"],
                "Teacher":    rep["teacher_name"] or "—",
                "Type":       "STUDENT",
                "Roll":       r["roll"],
                "Name":       r["name"],
                "Department": r["department"],
                "Semester":   r["semester"],
                "Status":     r["status"].upper(),
            })

    df = pd.DataFrame(all_records)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    filepath = os.path.join(save_dir, f"all_attendance_{ts}.csv")
    df.to_csv(filepath, index=False, encoding="utf-8-sig")
    return filepath
