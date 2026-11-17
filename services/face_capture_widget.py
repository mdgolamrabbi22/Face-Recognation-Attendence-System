# ============================================================
# face_capture_widget.py — Reusable Face Capture UI Widget
# ============================================================
# Comment translated to English.
# Comment translated to English.
# Comment translated to English.
# Comment translated to English.
# Comment translated to English.
# Comment translated to English.
# Comment translated to English.
# ============================================================

import customtkinter as ctk
import threading
import time
import cv2
import pickle
import numpy as np
from PIL import Image, ImageTk
from services.face_service import encode_face_from_frame
from config import WEBCAM_INDEX, FACE_CAPTURE_COUNT


class FaceCaptureWidget(ctk.CTkFrame):

    def __init__(self, parent, on_complete=None, **kwargs):
        super().__init__(parent, **kwargs)
        self.on_complete = on_complete

        self._cap = None
        self._running = False
        self._capture_active = False
        self._encoding = None

        # Thread communication
        self._latest_frame = None
        self._display_frame = None
        self._frame_lock = threading.Lock()
        self._display_lock = threading.Lock()

        # Capture state
        self._collected = []
        self._attempts = 0

        # ✅ image + after() track
        self._current_img = None
        self._photo_image = None
        self._after_id = None

        self._build_ui()

    # ── UI ────────────────────────────────────────────────────

    def _build_ui(self):
        self.configure(fg_color="transparent")

        ctk.CTkLabel(
            self,
            text="Face Scan",
            font=ctk.CTkFont(family="Segoe UI", size=15, weight="bold")
        ).pack(pady=(0, 8))

        # Use Canvas instead of Label for more stable image display
        import tkinter as tk
        self.preview_canvas = tk.Canvas(
            self,
            width=320, height=240,
            bg="#0d0d1a",
            highlightthickness=0,
            cursor="arrow"
        )
        self.preview_canvas.pack(pady=(0, 10))

        self.status_label = ctk.CTkLabel(
            self,
            text="Click the button below to start the webcam",
            text_color="gray",
            font=ctk.CTkFont(family="Segoe UI", size=12),
        )
        self.status_label.pack(pady=(0, 6))

        self.progress_bar = ctk.CTkProgressBar(self, width=320)
        self.progress_bar.set(0)
        self.progress_bar.pack(pady=(0, 4))

        self.progress_label = ctk.CTkLabel(
            self,
            text=f"0 / {FACE_CAPTURE_COUNT}",
            text_color="gray",
            font=ctk.CTkFont(family="Segoe UI", size=11),
        )
        self.progress_label.pack(pady=(0, 10))

        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack()

        self.start_btn = ctk.CTkButton(
            btn_frame,
            text="▶  Start Face Scan",
            width=150,
            command=self._start_scan,
            fg_color="#1f6feb",
            hover_color="#388bfd",
        )
        self.start_btn.pack(side="left", padx=5)

        self.reset_btn = ctk.CTkButton(
            btn_frame,
            text="↺  Reset",
            width=90,
            command=self._reset,
            fg_color="transparent",
            border_width=1,
            text_color=("gray10", "gray90"),
        )
        self.reset_btn.pack(side="left", padx=5)

    # ── Start ─────────────────────────────────────────────────

    def _start_scan(self):
        if self._running:
            return

        self._running = True
        self._capture_active = False
        self._collected = []
        self._attempts = 0
        self._encoding = None

        # Clear old image references to prevent GC issues
        self._current_img = None
        self._photo_image = None

        # Clear canvas
        try:
            if self.preview_canvas.winfo_exists():
                self.preview_canvas.delete("all")
        except Exception:
            pass

        self.start_btn.configure(
            state="disabled", text="⏳ Starting camera...")
        self.progress_bar.set(0)
        self.progress_label.configure(text=f"0 / {FACE_CAPTURE_COUNT}")
        self._set_status("Starting camera...", color="orange")

        threading.Thread(target=self._camera_capture_loop, daemon=True).start()
        threading.Thread(target=self._encoding_loop, daemon=True).start()

        # Start preview update loop with initial delay to allow camera initialization
        self._after_id = self.after(100, self._update_preview_ui)

    # ── Thread 1: Camera Capture ──────────────────────────────

    def _camera_capture_loop(self):
        cap = cv2.VideoCapture(WEBCAM_INDEX, cv2.CAP_DSHOW)

        if not cap.isOpened():
            cap.release()
            cap = cv2.VideoCapture(WEBCAM_INDEX)

        if not cap.isOpened():
            for idx in range(4):
                if idx == WEBCAM_INDEX:
                    continue
                for backend in [cv2.CAP_DSHOW, cv2.CAP_ANY]:
                    cap = cv2.VideoCapture(idx, backend)
                    if cap.isOpened():
                        break
                    cap.release()
                if cap.isOpened():
                    break

        if not cap.isOpened():
            self._safe_after(lambda: self._set_status(
                "❌ Webcam not found.", color="red"))
            self._safe_after(lambda: self.start_btn.configure(
                state="normal", text="▶  Start Face Scan"))
            self._running = False
            return

        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        self._cap = cap

        self._safe_after(lambda: self._set_status(
            "Place your face directly in front of the camera...", color="orange"))
        self._safe_after(lambda: self.start_btn.configure(
            text="⏳ Scanning..."))

        self._capture_active = True

        fail_count = 0
        while self._running:
            ret, frame = cap.read()

            if not ret:
                fail_count += 1
                time.sleep(0.02)
                if fail_count > 150:
                    self._safe_after(lambda: self._set_status(
                        "❌ Unable to read camera frame.", color="red"))
                    break
                continue

            fail_count = 0

            with self._frame_lock:
                self._latest_frame = frame

            time.sleep(0.01)

        # Ensure camera is released when loop exits
        try:
            cap.release()
        except Exception:
            pass
        self._cap = None

    # ── Thread 2: Encoding Loop ───────────────────────────────

    def _encoding_loop(self):
        max_attempts = FACE_CAPTURE_COUNT * 15

        while self._running:
            if not self._capture_active:
                time.sleep(0.05)
                continue

            if len(self._collected) >= FACE_CAPTURE_COUNT:
                break

            with self._frame_lock:
                frame = self._latest_frame.copy() if self._latest_frame is not None else None

            if frame is None:
                time.sleep(0.05)
                continue

            self._attempts += 1

            try:
                import face_recognition

                boosted = cv2.convertScaleAbs(frame, alpha=1.4, beta=30)
                small = cv2.resize(boosted, (0, 0), fx=0.5, fy=0.5)
                rgb_small = cv2.cvtColor(small, cv2.COLOR_BGR2RGB)

                locations_small = face_recognition.face_locations(
                    rgb_small, model="hog", number_of_times_to_upsample=0
                )

                if locations_small:
                    encodings = face_recognition.face_encodings(
                        rgb_small, locations_small, num_jitters=1)
                    if encodings:
                        enc = encodings[0]

                        t, r, b, l = locations_small[0]
                        top, right, bottom, left = t*2, r*2, b*2, l*2

                        display = frame.copy()
                        cv2.rectangle(display, (left, top),
                                      (right, bottom), (0, 255, 0), 2)
                        cv2.putText(
                            display,
                            f"{len(self._collected)+1}/{FACE_CAPTURE_COUNT}",
                            (left, top - 10),
                            cv2.FONT_HERSHEY_SIMPLEX,
                            0.6, (0, 255, 0), 2)
                        with self._display_lock:
                            self._display_frame = display

                        self._collected.append(enc)
                        count = len(self._collected)
                        pct = count / FACE_CAPTURE_COUNT

                        self._safe_after(
                            lambda p=pct: self.progress_bar.set(p))
                        self._safe_after(
                            lambda c=count: self.progress_label.configure(
                                text=f"{c} / {FACE_CAPTURE_COUNT}"))
                        self._safe_after(
                            lambda c=count: self._set_status(
                                f"✅ {c}/{FACE_CAPTURE_COUNT} frame captured",
                                color="green"))

                        if count >= FACE_CAPTURE_COUNT:
                            self._safe_after(lambda: self._set_status(
                                "⚙️ Processing...", color="yellow"))
                            avg = np.mean(self._collected, axis=0)
                            enc_bytes = pickle.dumps(avg)
                            self._capture_active = False
                            self._running = False
                            self._safe_after(
                                lambda b=enc_bytes: self._on_capture_done(b, None))
                            return
                    else:
                        with self._display_lock:
                            self._display_frame = frame.copy()
                else:
                    with self._display_lock:
                        self._display_frame = frame.copy()
                    if self._attempts % 20 == 0:
                        self._safe_after(lambda: self._set_status(
                            "⚠️ Face not detected — move closer and face a light source",
                            color="orange"))

            except Exception:
                enc, location = encode_face_from_frame(
                    frame, return_location=True)
                if enc is not None:
                    self._collected.append(enc)
                    count = len(self._collected)
                    self._safe_after(
                        lambda p=count / FACE_CAPTURE_COUNT: self.progress_bar.set(p))
                    self._safe_after(
                        lambda c=count: self.progress_label.configure(
                            text=f"{c} / {FACE_CAPTURE_COUNT}"))
                    if count >= FACE_CAPTURE_COUNT:
                        avg = np.mean(self._collected, axis=0)
                        enc_bytes = pickle.dumps(avg)
                        self._capture_active = False
                        self._running = False
                        self._safe_after(
                            lambda b=enc_bytes: self._on_capture_done(b, None))
                        return
                with self._display_lock:
                    self._display_frame = frame.copy()

            if self._attempts >= max_attempts and len(self._collected) < FACE_CAPTURE_COUNT:
                got = len(self._collected)
                err = (f"Only {got}/{FACE_CAPTURE_COUNT} frames were captured. "
                       f"Try again in better lighting while looking directly at the camera.")
                self._capture_active = False
                self._running = False
                self._safe_after(lambda e=err: self._on_capture_done(None, e))
                return

            time.sleep(0.04)

    # ── UI Update Loop (Main Thread) ──────────────────────────

    def _update_preview_ui(self):
        if not self.winfo_exists():
            return

        frame = None

        with self._display_lock:
            if self._display_frame is not None:
                frame = self._display_frame.copy()

        if frame is None:
            with self._frame_lock:
                if self._latest_frame is not None:
                    frame = self._latest_frame.copy()

        if frame is not None:
            try:
                # Convert BGR to RGB for PIL
                rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

                # Create PIL image
                pil_img = Image.fromarray(rgb).resize((320, 240))

                # Convert PIL to PhotoImage
                photo = ImageTk.PhotoImage(image=pil_img)

                # Store the reference to prevent garbage collection
                self._photo_image = photo
                self._current_img = pil_img

                # Update canvas with new image
                if self.preview_canvas.winfo_exists():
                    # Delete old image if any
                    self.preview_canvas.delete("image")
                    # Create new image on canvas
                    self.preview_canvas.create_image(
                        160, 120,
                        image=photo,
                        tags="image"
                    )

            except Exception as e:
                print(f"[Preview Error] {e}")

        if self._running and self.winfo_exists():
            # Continue updating at 30ms intervals (33 FPS)
            self._after_id = self.after(30, self._update_preview_ui)

    # ── Capture Done ──────────────────────────────────────────

    def _on_capture_done(self, encoding, error):
        self._capture_active = False
        self._running = False

        if error:
            if self.on_complete:
                self.on_complete(None, error)
            self._safe_widget(
                self.start_btn,
                lambda: self.start_btn.configure(
                    state="normal", text="▶  Start Face Scan"))
            return

        self._encoding = encoding
        if self.on_complete:
            print(f"[DEBUG] on_complete called, encoding size: "
                  f"{len(encoding) if encoding else 0}")
            self.on_complete(encoding, None)
        self._safe_widget(
            self.start_btn,
            lambda: self.start_btn.configure(state="normal", text="✅ Done"))

    # ── Helpers ───────────────────────────────────────────────

    def _safe_after(self, fn):
        try:
            if self.winfo_exists():
                self.after(0, fn)
        except Exception:
            pass

    def _safe_widget(self, widget, fn):
        try:
            if widget.winfo_exists():
                fn()
        except Exception:
            pass

    def _set_status(self, msg, color="gray"):
        color_map = {
            "gray":   ("gray50", "gray60"),
            "green":  ("#2e7d32", "#66bb6a"),
            "red":    ("#c62828", "#ef5350"),
            "orange": ("#e65100", "#ffa726"),
            "yellow": ("#f57f17", "#ffee58"),
        }
        tc = color_map.get(color, ("gray50", "gray60"))
        try:
            if self.status_label.winfo_exists():
                self.status_label.configure(text=msg, text_color=tc)
        except Exception:
            pass

    def _reset(self):
        """Reset the capture widget state completely"""
        self._running = False
        self._capture_active = False

        # Cancel any pending after() calls
        if self._after_id is not None:
            try:
                self.after_cancel(self._after_id)
            except Exception:
                pass
            self._after_id = None

        # Release camera if it's open
        if self._cap is not None:
            try:
                self._cap.release()
            except Exception:
                pass
            self._cap = None

        # Clear all frame data
        self._collected = []
        self._attempts = 0
        self._encoding = None
        self._latest_frame = None
        self._display_frame = None

        # Clear image references completely
        self._current_img = None
        self._photo_image = None

        # Reset preview canvas to initial state
        try:
            if self.preview_canvas.winfo_exists():
                self.preview_canvas.delete("all")
        except Exception:
            pass

        # Reset progress indicators
        try:
            if self.progress_bar.winfo_exists():
                self.progress_bar.set(0)
            if self.progress_label.winfo_exists():
                self.progress_label.configure(text=f"0 / {FACE_CAPTURE_COUNT}")
        except Exception:
            pass

        # Reset button
        self._safe_widget(
            self.start_btn,
            lambda: self.start_btn.configure(
                state="normal", text="▶  Start Face Scan"))

        # Reset status message
        self._set_status("Click the button below to start the webcam", color="gray")

    def get_encoding(self):
        return self._encoding

    def destroy(self):
        """Cleanup all resources before destroying widget"""
        self._running = False
        self._capture_active = False

        # Cancel any pending after() calls
        if self._after_id is not None:
            try:
                self.after_cancel(self._after_id)
            except Exception:
                pass
            self._after_id = None

        # Release camera if it's open
        if self._cap is not None:
            try:
                self._cap.release()
            except Exception:
                pass
            self._cap = None

        # Clear all image references
        self._current_img = None
        self._photo_image = None
        
        super().destroy()