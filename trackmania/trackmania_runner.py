"""
trackmania_runner.py
Autonomous Trackmania Auto-Pilot Dashboard (fully automatic).

The game runs on ANOTHER computer. A USB camera on THIS computer is aimed at
that screen. All vision + driving logic runs here, and the physical controls
are actuated through the ESP32:

    Camera → Road segmentation (lane centre / curvature) → PD steering
           → ESP32 (RACING mode)
               • Steering : stepper wheel  (STEPPER,LEFT/RIGHT/STOP)
                            or left joystick X (SERVO LJX)
               • Throttle : trigger servo  (SERVO ... TRIGGER)

Note: in RACING mode the firmware accepts both STEPPER and SERVO commands
(SERVO only requires RUNNING state), so steering and throttle can be driven
at the same time.

Protocol reference:  ActuatorProgram/include/README.md
UI layout matches:   racing/racing_runner.py, mapper/valorant_runner.py
"""

import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import threading
import time
import os
import sys
import cv2
import numpy as np
from PIL import Image, ImageTk

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from actuator_controller import ActuatorController


# ═══════════════════════════════════════════════════════════════
#  Vision Engine — runs in a background thread
# ═══════════════════════════════════════════════════════════════

class VisionEngine:
    """Camera capture + road detection + steering / throttle decision."""

    NUM_SCANLINES = 8

    def __init__(self):
        self.cap = None
        self.running = False
        self._thread = None

        # Tunable parameters (updated from GUI sliders)
        self.method = "ROAD"         # "ROAD" (colour segmentation) or "EDGE" (Canny density)
        self.horizon_pct = 0.45      # ROI starts here (ignore sky / scenery)
        self.hud_crop_pct = 0.90     # ROI ends here (ignore speedometer / HUD)
        self.color_tol = 28.0        # Lab distance that still counts as "road"
        self.lookahead = 0.6         # 0 = react to near road only, 1 = far road
        self.kp = 1.6                # steering proportional gain
        self.kd = 0.25               # steering damping (derivative) gain
        self.brake_curve = 0.35      # curvature above which throttle is released
        self.canny_min = 30
        self.canny_max = 100

        # Controller state
        self._prev_err = 0.0
        self._prev_t = None
        self._smoothed = 0.0
        self._prev_small = None
        self._still_since = None

        # Latest results (read by GUI on main thread)
        self.last_frame = None
        self.last_debug = None
        self.last_action = "IDLE"     # LEFT / RIGHT / STRAIGHT / LOST
        self.last_steer = 0.0         # -1 (full left) … +1 (full right)
        self.last_throttle = False
        self.last_metrics = (0.0, 0.0, 0.0)  # (offset, curvature, road coverage %)
        self.stuck = False
        self.fps = 0.0

        # Training data collection
        self.collect_data = False
        self.data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "training_data")
        self._frame_counter = 0
        self._save_every_n = 5

    # ── camera ──────────────────────────────────────────────────

    def open_camera(self, index: int = 0) -> bool:
        self.close_camera()
        self.cap = cv2.VideoCapture(index)
        if not self.cap.isOpened():
            self.cap = None
            return False
        return True

    def close_camera(self):
        if self.cap:
            self.cap.release()
            self.cap = None

    # ── start / stop ────────────────────────────────────────────

    def start(self):
        if self.running:
            return
        self.reset_controller()
        self.running = True
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def stop(self):
        self.running = False
        if self._thread:
            self._thread.join(timeout=2)
            self._thread = None

    def reset_controller(self):
        self._prev_err = 0.0
        self._prev_t = None
        self._smoothed = 0.0
        self._prev_small = None
        self._still_since = None
        self.stuck = False

    # ── analysis loop ───────────────────────────────────────────

    def _loop(self):
        prev_time = time.time()
        while self.running:
            if not self.cap or not self.cap.isOpened():
                time.sleep(0.05)
                continue

            ret, frame = self.cap.read()
            if not ret:
                time.sleep(0.01)
                continue

            now = time.time()
            dt = now - prev_time
            self.fps = 1.0 / dt if dt > 0 else 0
            prev_time = now

            self.last_frame = frame.copy()

            action, steer, throttle, metrics, debug = self.analyze(frame, now)
            self.last_action = action
            self.last_steer = steer
            self.last_throttle = throttle
            self.last_metrics = metrics
            self.last_debug = debug

            if self.collect_data:
                self._frame_counter += 1
                if self._frame_counter % self._save_every_n == 0:
                    self._save_frame(frame, action)

            time.sleep(0.005)

    # ── core decision (pure function of frame + state) ──────────

    def analyze(self, frame, now=None):
        """Return (action, steer[-1..1], throttle(bool), (offset, curvature, coverage%), debug_img)."""
        if now is None:
            now = time.time()
        h, w = frame.shape[:2]

        top = int(h * self.horizon_pct)
        bottom = int(h * self.hud_crop_pct)
        if bottom <= top + 10:
            bottom = min(h, top + 10)
        roi = frame[top:bottom, :]

        self._update_stuck(frame, now)

        if self.method == "EDGE":
            err, curvature, coverage, centers, mask = self._edge_method(roi)
        else:
            err, curvature, coverage, centers, mask = self._road_method(roi)

        lost = coverage < 3.0 or not centers

        # ── PD steering ─────────────────────────────────────────
        if lost:
            steer = self._smoothed * 0.9   # hold last steering, decaying
            action = "LOST"
        else:
            dt = (now - self._prev_t) if self._prev_t else 0.033
            dt = max(dt, 1e-3)
            deriv = (err - self._prev_err) / dt
            raw = self.kp * err + self.kd * deriv * 0.033
            raw = max(-1.0, min(1.0, raw))
            steer = 0.6 * raw + 0.4 * self._smoothed   # low-pass filter
            self._prev_err = err
            if steer < -0.08:
                action = "LEFT"
            elif steer > 0.08:
                action = "RIGHT"
            else:
                action = "STRAIGHT"
        self._prev_t = now
        self._smoothed = steer

        # ── throttle ────────────────────────────────────────────
        throttle = (not lost) and curvature < self.brake_curve

        metrics = (err, curvature, coverage)
        debug = self._build_debug(roi, mask, centers, steer, throttle, action, metrics)
        return action, round(steer, 3), throttle, metrics, debug

    # ── method 1: road colour segmentation ──────────────────────

    def _road_method(self, roi):
        rh, rw = roi.shape[:2]
        small = cv2.resize(roi, (max(rw // 2, 1), max(rh // 2, 1)), interpolation=cv2.INTER_AREA)
        sh, sw = small.shape[:2]
        blurred = cv2.GaussianBlur(small, (5, 5), 0)
        lab = cv2.cvtColor(blurred, cv2.COLOR_BGR2LAB).astype(np.float32)

        # Sample road colour just in front of the car (bottom-centre of ROI)
        sx1, sx2 = int(sw * 0.44), int(sw * 0.56)
        sy1, sy2 = int(sh * 0.85), sh
        patch = lab[sy1:sy2, sx1:sx2].reshape(-1, 3)
        ref = np.median(patch, axis=0) if patch.size else np.array([128, 128, 128], np.float32)

        dist = np.linalg.norm(lab - ref, axis=2)
        mask = (dist < self.color_tol).astype(np.uint8) * 255
        kernel = np.ones((5, 5), np.uint8)
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)

        # Keep only the connected region the car is actually driving on
        n, labels = cv2.connectedComponents(mask)
        seed = labels[min(sh - 2, int(sh * 0.93)), sw // 2]
        if n > 1 and seed > 0:
            mask = np.where(labels == seed, 255, 0).astype(np.uint8)

        mask_full = cv2.resize(mask, (rw, rh), interpolation=cv2.INTER_NEAREST)
        return self._centerline(mask_full)

    # ── method 2: edge density fallback (like racing_runner) ────

    def _edge_method(self, roi):
        gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)
        edges = cv2.Canny(blurred, self.canny_min, self.canny_max)
        # Free space = low edge density; dilate edges into "walls"
        walls = cv2.dilate(edges, np.ones((9, 9), np.uint8))
        free = cv2.bitwise_not(walls)
        return self._centerline(free)

    # ── shared: scanline lane-centre extraction ─────────────────

    def _centerline(self, mask):
        rh, rw = mask.shape[:2]
        coverage = cv2.countNonZero(mask) / float(max(rh * rw, 1)) * 100.0
        centers = []   # (x, y, weight)
        prev_x = rw // 2

        # Scan from bottom (near) to top (far)
        for i in range(self.NUM_SCANLINES):
            frac = i / max(self.NUM_SCANLINES - 1, 1)
            y = int((rh - 1) - frac * (rh - 1) * 0.95)
            row = mask[y] > 0
            if not row.any():
                break
            # Find runs of road pixels and pick the run closest to previous centre
            padded = np.concatenate(([False], row, [False]))
            diff = np.diff(padded.astype(np.int8))
            starts = np.where(diff == 1)[0]
            ends = np.where(diff == -1)[0]
            best, best_d = None, None
            for s, e in zip(starts, ends):
                if e - s < max(4, rw // 60):
                    continue
                cx = (s + e) // 2
                d = 0 if s <= prev_x < e else min(abs(s - prev_x), abs(e - prev_x))
                if best_d is None or d < best_d:
                    best, best_d = cx, d
            if best is None:
                break
            prev_x = best
            # Far rows weighted by lookahead, near rows by (1 - lookahead)
            weight = (1.0 - self.lookahead) * (1.0 - frac) + self.lookahead * frac + 0.05
            centers.append((best, y, weight))

        if not centers:
            return 0.0, 0.0, coverage, centers, mask

        half = rw / 2.0
        total_w = sum(c[2] for c in centers)
        err = sum(((c[0] - half) / half) * c[2] for c in centers) / total_w
        near = (centers[0][0] - half) / half
        far = (centers[-1][0] - half) / half
        curvature = abs(far - near)
        return float(err), float(curvature), coverage, centers, mask

    # ── stuck detection (wall hit / stopped car) ────────────────

    def _update_stuck(self, frame, now):
        small = cv2.cvtColor(cv2.resize(frame, (64, 36)), cv2.COLOR_BGR2GRAY).astype(np.int16)
        if self._prev_small is not None:
            motion = float(np.mean(np.abs(small - self._prev_small)))
            if motion < 1.5:
                if self._still_since is None:
                    self._still_since = now
                self.stuck = (now - self._still_since) > 3.0
            else:
                self._still_since = None
                self.stuck = False
        self._prev_small = small

    # ── debug visual ────────────────────────────────────────────

    def _build_debug(self, roi, mask, centers, steer, throttle, action, metrics):
        debug = roi.copy()
        overlay = np.zeros_like(debug)
        overlay[mask > 0] = (0, 180, 0)
        debug = cv2.addWeighted(debug, 0.6, overlay, 0.4, 0)

        rh, rw = debug.shape[:2]
        cv2.line(debug, (rw // 2, 0), (rw // 2, rh), (255, 0, 0), 1)
        for i, (x, y, _) in enumerate(centers):
            cv2.circle(debug, (int(x), int(y)), 5, (0, 255, 255), -1)
            if i > 0:
                px, py, _ = centers[i - 1]
                cv2.line(debug, (int(px), int(py)), (int(x), int(y)), (0, 255, 255), 2)

        # Steering bar
        bar_y = rh - 12
        cv2.rectangle(debug, (rw // 2 - 100, bar_y - 6), (rw // 2 + 100, bar_y + 6), (60, 60, 60), -1)
        sx = int(rw // 2 + steer * 100)
        cv2.rectangle(debug, (min(rw // 2, sx), bar_y - 6), (max(rw // 2, sx), bar_y + 6), (0, 200, 255), -1)

        off, curv, cov = metrics
        thr = "GAS" if throttle else "COAST"
        cv2.putText(debug, f"{action}  steer:{steer:+.2f}  {thr}", (10, 28),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
        cv2.putText(debug, f"off:{off:+.2f} curve:{curv:.2f} road:{cov:.0f}%", (10, 54),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 1)
        if self.stuck:
            cv2.putText(debug, "STUCK?", (rw - 110, 28), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)
        return debug

    def _save_frame(self, frame, action):
        folder = os.path.join(self.data_dir, action.lower())
        os.makedirs(folder, exist_ok=True)
        cv2.imwrite(os.path.join(folder, f"frame_{int(time.time() * 1000)}.jpg"), frame)


# ═══════════════════════════════════════════════════════════════
#  Steering output controllers
# ═══════════════════════════════════════════════════════════════

class WheelStepperController:
    """
    Closed-loop (estimated) position control for the stepper steering wheel.

    The firmware only offers continuous LEFT/RIGHT/STOP at a given rate, so the
    wheel angle is estimated by integrating rate × time. The target position is
    steer × wheel_range steps; the wheel is driven toward it and stopped inside
    a dead-band, so it re-centres on straights instead of drifting.
    """

    MIN_HZ = 150

    def __init__(self, ctrl: ActuatorController):
        self.ctrl = ctrl
        self.wheel_range = 600     # steps from centre to full lock
        self.max_hz = 800
        self.reset()

    def reset(self):
        self.pos = 0.0             # estimated steps (negative = left)
        self.dir = 0               # -1 left, 0 stopped, +1 right
        self.hz = 0
        self._last = time.time()

    def set_center(self):
        self.pos = 0.0

    def _integrate(self):
        now = time.time()
        self.pos += self.dir * self.hz * (now - self._last)
        self._last = now

    def tick(self, steer: float):
        self._integrate()
        target = max(-1.0, min(1.0, steer)) * self.wheel_range
        err = target - self.pos
        deadband = max(8.0, self.wheel_range * 0.04)

        if abs(err) < deadband:
            want_dir, want_hz = 0, 0
        else:
            want_dir = 1 if err > 0 else -1
            want_hz = int(max(self.MIN_HZ, min(self.max_hz, abs(err) * 6)))

        if want_dir != self.dir or (want_dir != 0 and abs(want_hz - self.hz) >= 60):
            if want_dir == 0:
                self.ctrl.steer_stop()
            elif want_dir < 0:
                self.ctrl.steer_left(want_hz)
            else:
                self.ctrl.steer_right(want_hz)
            self.dir, self.hz = want_dir, want_hz

    def stop(self):
        self._integrate()
        self.ctrl.steer_stop()
        self.dir, self.hz = 0, 0


# ═══════════════════════════════════════════════════════════════
#  Auto-Pilot GUI
# ═══════════════════════════════════════════════════════════════

class AutoPilotGUI:
    """Trackmania Auto-Pilot Dashboard — camera preview + autonomous driving."""

    BG        = "#1e1e2e"
    FG        = "#cdd6f4"
    ACCENT    = "#89b4fa"
    GREEN     = "#a6e3a1"
    RED       = "#f38ba8"
    YELLOW    = "#f9e2af"
    SURFACE   = "#313244"
    OVERLAY   = "#45475a"

    STEER_WHEEL = "Wheel (Stepper)"
    STEER_JOY = "Joystick (LJX servo)"

    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Trackmania Auto-Pilot")
        self.root.geometry("1060x720")
        self.root.minsize(860, 580)
        self.root.configure(bg=self.BG)
        self.root.resizable(True, True)

        self.ctrl = ActuatorController()
        self.ctrl.on_response = self._on_serial_response
        self.ctrl.on_status = self._on_serial_status
        self.ctrl.on_error = self._on_serial_error
        self.ctrl.on_disconnect = self._on_serial_disconnect

        self.vision = VisionEngine()
        self.wheel = WheelStepperController(self.ctrl)

        self._autopilot_active = False
        self._last_sent_servos = None
        self._last_servo_time = 0.0
        self._esp_state = "IDLE"
        self._stuck_logged = False

        self._build_ui()
        self._refresh_ports()
        self._update_loop()

    # ── UI ──────────────────────────────────────────────────────

    def _build_ui(self):
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(1, weight=1)

        # Header Title
        hdr = tk.Frame(self.root, bg=self.BG)
        hdr.grid(row=0, column=0, sticky="ew", pady=(8, 2))
        tk.Label(hdr, text="Trackmania Auto-Pilot",
                 font=("Segoe UI", 16, "bold"), bg=self.BG, fg=self.ACCENT).pack()
        tk.Label(hdr, text="Camera (other PC) → Road CV → PD Steering → ESP32 Wheel / Joystick + Throttle",
                 font=("Segoe UI", 9), bg=self.BG, fg=self.OVERLAY).pack()

        # Center split: Left (Videos) + Right (Controls with vertical scrollbar)
        center = tk.Frame(self.root, bg=self.BG)
        center.grid(row=1, column=0, sticky="nsew", padx=10, pady=2)
        center.columnconfigure(0, weight=1)  # Left camera column expands
        center.columnconfigure(1, weight=0)  # Right controls column fixed
        center.rowconfigure(0, weight=1)

        # ── Left column: camera + debug ─────────────────────────
        self.left_col = tk.Frame(center, bg=self.BG)
        self.left_col.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        self.left_col.columnconfigure(0, weight=1)
        self.left_col.rowconfigure(0, weight=3)
        self.left_col.rowconfigure(1, weight=2)

        self.camera_label = tk.Label(self.left_col, bg="#000000")
        self.camera_label.grid(row=0, column=0, sticky="nsew", pady=(0, 4))

        self.debug_label = tk.Label(self.left_col, bg="#111111")
        self.debug_label.grid(row=1, column=0, sticky="nsew")

        # ── Right column: scrollable controls ───────────────────
        right_canvas = tk.Canvas(center, bg=self.BG, highlightthickness=0, width=400)
        right_scroll = ttk.Scrollbar(center, orient="vertical", command=right_canvas.yview)
        right_canvas.configure(yscrollcommand=right_scroll.set)

        right = tk.Frame(right_canvas, bg=self.BG)
        right_win = right_canvas.create_window((0, 0), window=right, anchor="nw")

        def _on_right_cfg(e):
            right_canvas.configure(scrollregion=right_canvas.bbox("all"))
        right.bind("<Configure>", _on_right_cfg)

        def _on_canvas_cfg(e):
            right_canvas.itemconfig(right_win, width=e.width)
        right_canvas.bind("<Configure>", _on_canvas_cfg)

        # Mouse wheel support on controls pane
        def _on_mousewheel(e):
            right_canvas.yview_scroll(int(-1 * (e.delta / 120)), "units")
        right_canvas.bind_all("<MouseWheel>", _on_mousewheel)

        right_canvas.grid(row=0, column=1, sticky="nsew")
        right_scroll.grid(row=0, column=2, sticky="ns")

        # Connection
        conn = tk.LabelFrame(right, text=" Connection ", font=("Segoe UI", 9, "bold"),
                             bg=self.SURFACE, fg=self.FG, padx=8, pady=6)
        conn.pack(fill="x", pady=(0, 6))

        r1 = tk.Frame(conn, bg=self.SURFACE)
        r1.pack(fill="x")
        tk.Label(r1, text="COM:", bg=self.SURFACE, fg=self.FG,
                 font=("Segoe UI", 9)).pack(side="left")
        self.port_var = tk.StringVar()
        self.port_combo = ttk.Combobox(r1, textvariable=self.port_var, width=8, state="readonly")
        self.port_combo.pack(side="left", padx=4)
        tk.Button(r1, text="⟳", width=2, command=self._refresh_ports,
                  bg=self.OVERLAY, fg=self.FG, relief="flat").pack(side="left")
        self.btn_connect = tk.Button(r1, text="Connect", width=10,
                                     command=self._toggle_connect,
                                     bg=self.ACCENT, fg=self.BG, relief="flat",
                                     font=("Segoe UI", 9, "bold"))
        self.btn_connect.pack(side="right")

        r2 = tk.Frame(conn, bg=self.SURFACE)
        r2.pack(fill="x", pady=(4, 0))
        tk.Label(r2, text="Camera:", bg=self.SURFACE, fg=self.FG,
                 font=("Segoe UI", 9)).pack(side="left")
        self.cam_var = tk.IntVar(value=1)
        tk.Spinbox(r2, from_=0, to=5, textvariable=self.cam_var,
                   width=3, font=("Segoe UI", 9)).pack(side="left", padx=4)

        # State
        state_f = tk.Frame(right, bg=self.BG)
        state_f.pack(fill="x", pady=4)
        tk.Label(state_f, text="ESP32:", bg=self.BG, fg=self.FG,
                 font=("Segoe UI", 9)).pack(side="left")
        self.state_label = tk.Label(state_f, text="DISCONNECTED",
                                    bg=self.BG, fg=self.RED,
                                    font=("Segoe UI", 10, "bold"))
        self.state_label.pack(side="left", padx=4)

        # Auto-pilot button
        self.btn_autopilot = tk.Button(right, text="▶  START AUTO-PILOT",
                                       width=28, height=2,
                                       command=self._toggle_autopilot,
                                       bg=self.GREEN, fg=self.BG, relief="flat",
                                       font=("Segoe UI", 11, "bold"),
                                       state="disabled")
        self.btn_autopilot.pack(pady=6)

        # Live status
        status_f = tk.LabelFrame(right, text=" Live Status ", font=("Segoe UI", 9, "bold"),
                                 bg=self.SURFACE, fg=self.FG, padx=8, pady=4)
        status_f.pack(fill="x", pady=(0, 6))

        self.action_label = tk.Label(status_f, text="IDLE", bg=self.SURFACE, fg=self.YELLOW,
                                     font=("Consolas", 14, "bold"))
        self.action_label.pack()
        self.output_label = tk.Label(status_f, text="Steer: +0.00   Throttle: OFF",
                                     bg=self.SURFACE, fg=self.FG, font=("Consolas", 10))
        self.output_label.pack()
        self.wheel_label = tk.Label(status_f, text="Wheel pos: 0 steps",
                                    bg=self.SURFACE, fg=self.FG, font=("Consolas", 9))
        self.wheel_label.pack()
        self.fps_label = tk.Label(status_f, text="FPS: --", bg=self.SURFACE, fg=self.OVERLAY,
                                  font=("Segoe UI", 8))
        self.fps_label.pack()
        self.metrics_label = tk.Label(status_f, text="Off: --  Curve: --  Road: --",
                                      bg=self.SURFACE, fg=self.FG, font=("Consolas", 9))
        self.metrics_label.pack(pady=(2, 0))

        # Output configuration
        out_f = tk.LabelFrame(right, text=" Controls Output ", font=("Segoe UI", 9, "bold"),
                              bg=self.SURFACE, fg=self.FG, padx=8, pady=4)
        out_f.pack(fill="x", pady=(0, 6))

        o1 = tk.Frame(out_f, bg=self.SURFACE)
        o1.pack(fill="x")
        tk.Label(o1, text="Steering:", bg=self.SURFACE, fg=self.FG,
                 font=("Segoe UI", 8)).pack(side="left")
        self.steer_mode_var = tk.StringVar(value=self.STEER_WHEEL)
        ttk.Combobox(o1, textvariable=self.steer_mode_var, width=18, state="readonly",
                     values=[self.STEER_WHEEL, self.STEER_JOY]).pack(side="left", padx=4)
        tk.Button(o1, text="Set Center", command=self._set_wheel_center,
                  bg=self.OVERLAY, fg=self.FG, relief="flat",
                  font=("Segoe UI", 8)).pack(side="right")

        o2 = tk.Frame(out_f, bg=self.SURFACE)
        o2.pack(fill="x", pady=(2, 0))
        tk.Label(o2, text="Vision:", bg=self.SURFACE, fg=self.FG,
                 font=("Segoe UI", 8)).pack(side="left")
        self.method_var = tk.StringVar(value="Road Colour")
        ttk.Combobox(o2, textvariable=self.method_var, width=12, state="readonly",
                     values=["Road Colour", "Edge Density"]).pack(side="left", padx=4)
        self.throttle_var = tk.BooleanVar(value=True)
        tk.Checkbutton(o2, text="Auto throttle", variable=self.throttle_var,
                       bg=self.SURFACE, fg=self.FG, selectcolor=self.BG,
                       activebackground=self.SURFACE, activeforeground=self.FG,
                       font=("Segoe UI", 8)).pack(side="right")

        self.wheel_range_var = tk.IntVar(value=600)
        self._add_slider(out_f, "Wheel Range", self.wheel_range_var, 100, 2000)
        self.max_hz_var = tk.IntVar(value=800)
        self._add_slider(out_f, "Max Steer Hz", self.max_hz_var, 200, 2000)
        self.joy_range_var = tk.IntVar(value=40)
        self._add_slider(out_f, "Joystick Range °", self.joy_range_var, 10, 90)
        self.gas_angle_var = tk.IntVar(value=180)
        self._add_slider(out_f, "Throttle Angle °", self.gas_angle_var, 0, 180)

        # Tuning
        tune = tk.LabelFrame(right, text=" Tuning ", font=("Segoe UI", 9, "bold"),
                             bg=self.SURFACE, fg=self.FG, padx=8, pady=4)
        tune.pack(fill="x", pady=(0, 6))

        self.horizon_var = tk.DoubleVar(value=45.0)
        self._add_slider(tune, "Horizon %", self.horizon_var, 10.0, 80.0)
        self.crop_var = tk.DoubleVar(value=90.0)
        self._add_slider(tune, "HUD Crop %", self.crop_var, 50.0, 100.0)
        self.tol_var = tk.DoubleVar(value=28.0)
        self._add_slider(tune, "Road Colour Tol", self.tol_var, 5.0, 80.0)
        self.look_var = tk.DoubleVar(value=0.6)
        self._add_slider(tune, "Lookahead", self.look_var, 0.0, 1.0, res=0.05)
        self.kp_var = tk.DoubleVar(value=1.6)
        self._add_slider(tune, "Steer Gain", self.kp_var, 0.2, 5.0)
        self.kd_var = tk.DoubleVar(value=0.25)
        self._add_slider(tune, "Steer Damping", self.kd_var, 0.0, 2.0, res=0.05)
        self.brake_var = tk.DoubleVar(value=0.35)
        self._add_slider(tune, "Brake Curve", self.brake_var, 0.05, 1.5, res=0.05)

        self.collect_var = tk.BooleanVar(value=False)
        tk.Checkbutton(right, text="Collect training data",
                       variable=self.collect_var, bg=self.BG, fg=self.FG,
                       selectcolor=self.SURFACE, font=("Segoe UI", 9),
                       activebackground=self.BG, activeforeground=self.FG
                       ).pack(anchor="w")

        # Serial log
        log_f = tk.LabelFrame(self.root, text=" Serial Log ", font=("Segoe UI", 9, "bold"),
                              bg=self.SURFACE, fg=self.FG, padx=4, pady=2)
        log_f.grid(row=2, column=0, padx=10, pady=(2, 6), sticky="ew")
        self.log_text = scrolledtext.ScrolledText(log_f, height=4, bg=self.BG,
                                                  fg=self.GREEN, font=("Consolas", 8),
                                                  relief="flat", state="disabled", wrap="word")
        self.log_text.pack(fill="x")

    def _add_slider(self, parent, label, var, from_, to, res=None):
        row = tk.Frame(parent, bg=self.SURFACE)
        row.pack(fill="x", pady=0)
        tk.Label(row, text=label, bg=self.SURFACE, fg=self.FG,
                 font=("Segoe UI", 8), width=14, anchor="w").pack(side="left")
        if res is None:
            res = 0.1 if isinstance(var, tk.DoubleVar) else 1
        tk.Scale(row, from_=from_, to=to, orient="horizontal", variable=var,
                 bg=self.SURFACE, fg=self.FG, highlightthickness=0,
                 troughcolor=self.OVERLAY, font=("Segoe UI", 7),
                 resolution=res, length=150, sliderlength=14, width=10
                 ).pack(side="left", fill="x", expand=True)

    # ── connection ──────────────────────────────────────────────

    def _refresh_ports(self):
        ports = ActuatorController.list_ports()
        self.port_combo["values"] = ports
        if ports:
            self.port_combo.current(0)

    def _toggle_connect(self):
        if self.ctrl.is_connected:
            if self._autopilot_active:
                self._stop_autopilot()
            self.ctrl.disconnect()
            self._log("Disconnected.")
            self.btn_connect.config(text="Connect", bg=self.ACCENT)
            self.state_label.config(text="DISCONNECTED", fg=self.RED)
            self._esp_state = "IDLE"
            self.btn_autopilot.config(state="disabled")
        else:
            port = self.port_var.get()
            if not port:
                messagebox.showwarning("No Port", "Select a COM port first.")
                return
            self._log(f"Connecting to {port}...")
            if self.ctrl.connect(port):
                self._log("Connected @ 115200 baud.")
                self.btn_connect.config(text="Disconnect", bg=self.RED)
                self.state_label.config(text="IDLE", fg=self.YELLOW)
                self._esp_state = "IDLE"
                self.btn_autopilot.config(state="normal")
                self.ctrl.get_status()
            else:
                messagebox.showerror("Failed", f"Could not open {port}.")

    # ── auto-pilot ──────────────────────────────────────────────

    def _toggle_autopilot(self):
        if self._autopilot_active:
            self._stop_autopilot()
        else:
            self._start_autopilot()

    def _start_autopilot(self):
        cam_idx = self.cam_var.get()
        if not self.vision.open_camera(cam_idx):
            messagebox.showerror("Camera Error",
                                 f"Could not open camera index {cam_idx}.\nTry a different index.")
            return

        # RACING mode accepts both STEPPER and SERVO commands while RUNNING
        self.ctrl.set_racing_mode()
        time.sleep(0.3)
        self.ctrl.start()
        time.sleep(0.3)

        self.wheel.reset()
        self.vision.start()
        self._autopilot_active = True
        self._last_sent_servos = None
        self._stuck_logged = False

        self.btn_autopilot.config(text="■  STOP AUTO-PILOT", bg=self.RED)
        self._log(f"Auto-pilot STARTED (steering: {self.steer_mode_var.get()}).")

    def _stop_autopilot(self):
        self.vision.stop()
        self.vision.close_camera()
        self._autopilot_active = False

        # Release throttle + centre joystick
        self.ctrl.send_servo(90, 90, 90, 90, 0, 200)
        self._last_sent_servos = None

        # Drive the wheel back to its estimated centre, then stop the mode
        self.wheel.stop()
        steps = abs(self.wheel.pos)
        if steps > 10:
            rate = 400
            if self.wheel.pos > 0:
                self.ctrl.steer_left(rate)
            else:
                self.ctrl.steer_right(rate)
            delay_ms = int(steps / rate * 1000)
            self._log(f"Re-centering wheel ({int(steps)} steps)...")
            self.root.after(delay_ms, self._finish_stop)
        else:
            self._finish_stop()

    def _finish_stop(self):
        self.ctrl.steer_stop()
        self.wheel.reset()
        time.sleep(0.1)
        self.ctrl.stop()
        time.sleep(0.1)
        self.ctrl.reset()
        self.btn_autopilot.config(text="▶  START AUTO-PILOT", bg=self.GREEN)
        self._log("Auto-pilot STOPPED.")

    def _set_wheel_center(self):
        self.wheel.set_center()
        self._log("Wheel centre set to current position.")

    # ── main update loop (Tk main thread) ───────────────────────

    def _update_loop(self):
        v = self.vision
        v.method = "EDGE" if self.method_var.get() == "Edge Density" else "ROAD"
        v.horizon_pct = self.horizon_var.get() / 100.0
        v.hud_crop_pct = self.crop_var.get() / 100.0
        v.color_tol = self.tol_var.get()
        v.lookahead = self.look_var.get()
        v.kp = self.kp_var.get()
        v.kd = self.kd_var.get()
        v.brake_curve = self.brake_var.get()
        v.collect_data = self.collect_var.get()
        self.wheel.wheel_range = self.wheel_range_var.get()
        self.wheel.max_hz = self.max_hz_var.get()

        if self._autopilot_active:
            # Dynamic max dimensions based on actual left column size
            lw = max(440, self.left_col.winfo_width())
            lh = max(380, self.left_col.winfo_height())
            cam_max_h = max(240, int(lh * 0.60))
            dbg_max_h = max(140, int(lh * 0.38))

            frame = v.last_frame
            if frame is not None:
                self._show_image(self.camera_label, frame, max_w=lw, max_h=cam_max_h)
            debug = v.last_debug
            if debug is not None:
                self._show_image(self.debug_label, debug, max_w=lw, max_h=dbg_max_h)

            action = v.last_action
            steer = v.last_steer
            throttle = v.last_throttle and self.throttle_var.get()
            off, curv, cov = v.last_metrics

            colors = {"LEFT": self.ACCENT, "RIGHT": self.ACCENT,
                      "STRAIGHT": self.GREEN, "LOST": self.RED, "IDLE": self.YELLOW}
            text = f"⟵ {action}" if action == "LEFT" else f"{action} ⟶" if action == "RIGHT" else action
            self.action_label.config(text=text, fg=colors.get(action, self.FG))
            self.output_label.config(text=f"Steer: {steer:+.2f}   Throttle: {'ON' if throttle else 'OFF'}")
            self.wheel_label.config(text=f"Wheel pos: {int(self.wheel.pos)} / ±{self.wheel.wheel_range} steps")
            self.fps_label.config(text=f"FPS: {v.fps:.0f}")
            self.metrics_label.config(text=f"Off: {off:+.2f}  Curve: {curv:.2f}  Road: {cov:.0f}%")

            if v.stuck and not self._stuck_logged:
                self._log("⚠ Car appears stuck (no motion for 3 s) — check the track / respawn.")
                self._stuck_logged = True
            elif not v.stuck:
                self._stuck_logged = False

            self._send_controls(steer, throttle)

        self.root.after(33, self._update_loop)

    def _send_controls(self, steer, throttle):
        if not self.ctrl.is_connected:
            return

        use_wheel = self.steer_mode_var.get() == self.STEER_WHEEL

        # Steering: wheel (stepper) or joystick X (servo)
        if use_wheel:
            self.wheel.tick(steer)
            ljx = 90
        else:
            if self.wheel.dir != 0:
                self.wheel.stop()
            ljx = int(round(90 + steer * self.joy_range_var.get()))
            ljx = max(0, min(180, ljx))

        trig = self.gas_angle_var.get() if throttle else 0
        servos = (ljx, 90, 90, 90, trig)

        # Rate-limit servo traffic: send on meaningful change or 1 s heartbeat
        now = time.time()
        last = self._last_sent_servos
        changed = (last is None or abs(last[0] - ljx) >= 2 or last[4] != trig)
        if changed or (now - self._last_servo_time) > 1.0:
            self.ctrl.send_servo(*servos, duration=50)
            self._last_sent_servos = servos
            self._last_servo_time = now

    def _show_image(self, label, cv_img, max_w, max_h):
        h, w = cv_img.shape[:2]
        scale = min(max_w / w, max_h / h, 1.0)
        if scale < 1.0:
            cv_img = cv2.resize(cv_img, (int(w * scale), int(h * scale)))
        rgb = cv2.cvtColor(cv_img, cv2.COLOR_BGR2RGB)
        tk_img = ImageTk.PhotoImage(Image.fromarray(rgb))
        label.config(image=tk_img, width=0, height=0)
        label._photo = tk_img  # prevent garbage collection

    # ── serial callbacks (from reader thread) ───────────────────

    def _on_serial_response(self, line):
        if line == "OK":
            return  # high-rate acknowledgements; keep the log readable
        self.root.after(0, self._log, f"← {line}")

    def _on_serial_status(self, mode, state):
        def _u():
            self._esp_state = state
            color = {"IDLE": self.YELLOW, "MODE_SET": self.ACCENT,
                     "RUNNING": self.GREEN, "STOPPED": self.RED}.get(state, self.FG)
            self.state_label.config(text=f"{state} ({mode})", fg=color)
        self.root.after(0, _u)

    def _on_serial_error(self, code, msg):
        self.root.after(0, self._log, f"⚠ ERR {code}: {msg}")

    def _on_serial_disconnect(self):
        def _u():
            if self._autopilot_active:
                self.vision.stop()
                self.vision.close_camera()
                self._autopilot_active = False
                self.btn_autopilot.config(text="▶  START AUTO-PILOT", bg=self.GREEN)
            self.btn_connect.config(text="Connect", bg=self.ACCENT)
            self.state_label.config(text="DISCONNECTED", fg=self.RED)
            self.btn_autopilot.config(state="disabled")
            self._log("⚠ Connection lost.")
        self.root.after(0, _u)

    # ── helpers ─────────────────────────────────────────────────

    def _log(self, text):
        self.log_text.config(state="normal")
        self.log_text.insert("end", text + "\n")
        self.log_text.see("end")
        self.log_text.config(state="disabled")

    def on_close(self):
        if self._autopilot_active:
            self.vision.stop()
            self.vision.close_camera()
            self.ctrl.send_servo(90, 90, 90, 90, 0, 200)
            self.ctrl.steer_stop()
            self.ctrl.stop()
        if self.ctrl.is_connected:
            self.ctrl.disconnect()
        self.root.destroy()


# ── standalone launch ───────────────────────────────────────────

if __name__ == "__main__":
    root = tk.Tk()
    app = AutoPilotGUI(root)
    root.protocol("WM_DELETE_WINDOW", app.on_close)
    root.mainloop()

