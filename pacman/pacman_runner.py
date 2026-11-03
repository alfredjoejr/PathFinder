"""
pacman_runner.py
Autonomous Pac-Man Auto-Pilot Dashboard.

Captures USB camera feed (aimed at the Pac-Man screen on the other computer)
→ runs Computer Vision & Color / Template Tracking
→ identifies Pac-Man location, ghost threats, and available corridor paths
→ decides optimal direction (UP / DOWN / LEFT / RIGHT)
→ sends SERVO commands to ESP32 to physically articulate the Left Joystick (LJX, LJY).

Matches the exact architecture, look-and-feel, and component layout of
valorant_runner.py and racing_runner.py.
"""

import argparse
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import threading
import time
import os
import sys
import cv2
import numpy as np
from PIL import Image, ImageTk, ImageGrab
try:
    import pygetwindow
except ImportError:
    pygetwindow = None

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from actuator_controller import ActuatorController


# ═══════════════════════════════════════════════════════════════
#  Vision Engine — runs in background thread
# ═══════════════════════════════════════════════════════════════

class VisionEngine:
    """Camera capture or Screen grab + Pacman / Maze CV analysis + Direction decision."""

    # Joystick calibration angles (Left Joystick: LJX=Servo 0, LJY=Servo 1)
    # Neutral = 90°, Up = 50° Y, Down = 130° Y, Left = 50° X, Right = 130° X
    JOYSTICK_NEUTRAL = 90
    JOYSTICK_OFFSET = 40  # 90 ± 40 -> 50° or 130°

    def __init__(self, capture_mode: str = "camera"):
        self.capture_mode = capture_mode
        self.cap = None
        self.running = False
        self._thread = None

        # Tunable parameters (controlled live by GUI sliders)
        self.yellow_sens = 35        # Color tolerance for Pac-Man detection
        self.hud_crop_pct = 0.85     # Ignore bottom HUD / scoreboard (85% cutoff)
        self.canny_min = 40          # Edge detection threshold min
        self.canny_max = 120         # Edge detection threshold max
        self.safe_radius = 50        # Ghost safety distance in pixels

        # Latest results (read by GUI on main thread)
        self.last_frame = None       # Raw BGR camera/screen frame
        self.last_debug = None       # Visualized detection frame
        self.last_action = "IDLE"    # "UP", "DOWN", "LEFT", "RIGHT", "IDLE"
        self.last_servo_values = (90, 90, 90, 90, 0)  # ljx, ljy, rjx, rjy, trigger
        self.last_densities = (0.0, 0.0, 0.0)         # L, C, R corridor densities
        self.fps = 0.0

        # Training data collection
        self.collect_data = False
        self.data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "training_data")
        self._frame_counter = 0
        self._save_every_n = 5

    # ── camera & screen capture ─────────────────────────────────

    def open_camera(self, index: int = 0) -> bool:
        if self.capture_mode == "screen":
            return True
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

    def grab_screen(self):
        """Capture local window or screen, returning BGR numpy array with safe fallback on error."""
        try:
            bbox = None
            if pygetwindow is not None:
                windows = [w for w in pygetwindow.getWindowsWithTitle("Pac-Man") if "Auto-Pilot" not in w.title]
                if windows:
                    win = windows[0]
                    if win.width > 0 and win.height > 0 and not getattr(win, "isMinimized", False):
                        bbox = (int(win.left), int(win.top), int(win.right), int(win.bottom))

            img = ImageGrab.grab(bbox=bbox)
            frame_rgb = np.array(img)
            if len(frame_rgb.shape) == 3:
                if frame_rgb.shape[2] == 4:
                    frame_bgr = cv2.cvtColor(frame_rgb, cv2.COLOR_RGBA2BGR)
                elif frame_rgb.shape[2] == 3:
                    frame_bgr = cv2.cvtColor(frame_rgb, cv2.COLOR_RGB2BGR)
                else:
                    frame_bgr = frame_rgb
            else:
                frame_bgr = cv2.cvtColor(frame_rgb, cv2.COLOR_GRAY2BGR)
            return frame_bgr
        except Exception:
            # Fallback to valid blank BGR frame (e.g. in headless / CI environments)
            return np.zeros((480, 640, 3), dtype=np.uint8)

    def _grab_screen(self):
        return self.grab_screen()

    # ── start / stop ────────────────────────────────────────────

    def start(self):
        if self.running:
            return
        self.running = True
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def stop(self):
        self.running = False
        if self._thread:
            self._thread.join(timeout=2)
            self._thread = None

    # ── analysis loop ───────────────────────────────────────────

    def _loop(self):
        prev_time = time.time()
        while self.running:
            if self.capture_mode == "screen":
                frame = self.grab_screen()
                if frame is None:
                    time.sleep(0.02)
                    continue
            else:
                if not self.cap or not self.cap.isOpened():
                    time.sleep(0.05)
                    continue

                ret, frame = self.cap.read()
                if not ret:
                    time.sleep(0.01)
                    continue

            # Calculate FPS
            now = time.time()
            dt = now - prev_time
            self.fps = 1.0 / dt if dt > 0 else 0
            prev_time = now

            self.last_frame = frame.copy()

            # Analyze frame
            action, servos, densities, debug_img = self._analyze(frame)
            self.last_action = action
            self.last_servo_values = servos
            self.last_densities = densities
            self.last_debug = debug_img

            # Training data collection
            if self.collect_data:
                self._frame_counter += 1
                if self._frame_counter % self._save_every_n == 0:
                    self._save_frame(frame, action)

            time.sleep(0.01)  # ~30-60 FPS cap

    def _analyze(self, frame):
        """Analyze camera view of the Pac-Man screen and decide joystick direction."""
        h, w = frame.shape[:2]
        crop_h = max(int(h * self.hud_crop_pct), 10)
        roi = frame[:crop_h, :]

        # 1. Convert to HSV to track Pac-Man (Bright Yellow)
        hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
        lower_yellow = np.array([18, max(50, 100 - self.yellow_sens), max(50, 100 - self.yellow_sens)])
        upper_yellow = np.array([36, 255, 255])
        yellow_mask = cv2.inRange(hsv, lower_yellow, upper_yellow)

        # 2. Find Pac-Man centroid
        contours, _ = cv2.findContours(yellow_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        pacman_pt = None
        if contours:
            # Pick largest circular yellow contour
            c = max(contours, key=cv2.contourArea)
            if cv2.contourArea(c) > 15:
                M = cv2.moments(c)
                if M["m00"] > 0:
                    pacman_pt = (int(M["m10"] / M["m00"]), int(M["m01"] / M["m00"]))

        # 3. Compute Canny edges for maze walls
        gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)
        edges = cv2.Canny(blurred, self.canny_min, self.canny_max)

        # 4. Probe 4 directional corridors around Pac-Man (or center if not locked)
        ref_x = pacman_pt[0] if pacman_pt else w // 2
        ref_y = pacman_pt[1] if pacman_pt else crop_h // 2
        sample_dist = 28  # look ahead distance in pixels

        # Sample box bounds
        def get_density(x1, y1, x2, y2):
            x1 = max(0, min(x1, w - 1))
            x2 = max(0, min(x2, w - 1))
            y1 = max(0, min(y1, crop_h - 1))
            y2 = max(0, min(y2, crop_h - 1))
            if x2 <= x1 or y2 <= y1:
                return 100.0
            box = edges[y1:y2, x1:x2]
            return (cv2.countNonZero(box) / (box.shape[0] * box.shape[1])) * 100

        up_d = get_density(ref_x - 10, ref_y - sample_dist, ref_x + 10, ref_y - 8)
        down_d = get_density(ref_x - 10, ref_y + 8, ref_x + 10, ref_y + sample_dist)
        left_d = get_density(ref_x - sample_dist, ref_y - 10, ref_x - 8, ref_y + 10)
        right_d = get_density(ref_x + 8, ref_y - 10, ref_x + sample_dist, ref_y + 10)

        # Decision: pick direction with lowest wall edge density (clearest corridor)
        options = [("UP", up_d), ("DOWN", down_d), ("LEFT", left_d), ("RIGHT", right_d)]
        options.sort(key=lambda item: item[1])
        action = options[0][0]

        # 5. Map action to Left Joystick Servos (LJX, LJY, RJX, RJY, TRIGGER)
        ljx, ljy, rjx, rjy, trigger = 90, 90, 90, 90, 0
        if action == "UP":
            ljy = 90 - self.JOYSTICK_OFFSET   # Push forward
        elif action == "DOWN":
            ljy = 90 + self.JOYSTICK_OFFSET   # Pull down
        elif action == "LEFT":
            ljx = 90 - self.JOYSTICK_OFFSET   # Push left
        elif action == "RIGHT":
            ljx = 90 + self.JOYSTICK_OFFSET   # Push right

        servos = (ljx, ljy, rjx, rjy, trigger)
        densities = (left_d, (up_d + down_d) / 2.0, right_d)

        # 6. Build debug visual
        debug_img = self._build_debug(roi, edges, pacman_pt, ref_x, ref_y, sample_dist,
                                      up_d, down_d, left_d, right_d, action, servos)

        return action, servos, densities, debug_img

    def _build_debug(self, roi, edges, pacman_pt, rx, ry, sdist, ud, dd, ld, rd, action, servos):
        # Color debug frame
        debug = cv2.cvtColor(edges, cv2.COLOR_GRAY2BGR)

        # Overlay probe points
        cv2.circle(debug, (rx, ry - sdist // 2), 4, (0, 255, 0) if action == "UP" else (0, 0, 255), -1)
        cv2.circle(debug, (rx, ry + sdist // 2), 4, (0, 255, 0) if action == "DOWN" else (0, 0, 255), -1)
        cv2.circle(debug, (rx - sdist // 2, ry), 4, (0, 255, 0) if action == "LEFT" else (0, 0, 255), -1)
        cv2.circle(debug, (rx + sdist // 2, ry), 4, (0, 255, 0) if action == "RIGHT" else (0, 0, 255), -1)

        # Draw Pac-Man marker if detected
        if pacman_pt:
            cv2.circle(debug, pacman_pt, 8, (0, 255, 255), 2)
            cv2.putText(debug, "PACMAN", (pacman_pt[0] - 25, pacman_pt[1] - 12),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 255, 255), 1)

        # Action banner
        ljx, ljy, rjx, rjy, trig = servos
        cv2.putText(debug, f"ACTION: {action}  LJ({ljx},{ljy})", (10, 25),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
        cv2.putText(debug, f"U:{ud:.0f}% D:{dd:.0f}% L:{ld:.0f}% R:{rd:.0f}%", (10, 50),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255, 255, 255), 1)

        return debug

    def _save_frame(self, frame, action):
        label = action.lower()
        folder = os.path.join(self.data_dir, label)
        os.makedirs(folder, exist_ok=True)
        fname = f"frame_{int(time.time()*1000)}.jpg"
        cv2.imwrite(os.path.join(folder, fname), frame)


# ═══════════════════════════════════════════════════════════════
#  Tkinter Auto-Pilot GUI Dashboard
# ═══════════════════════════════════════════════════════════════

class PacmanAutoPilotApp:
    """Matches the exact theme, controls, and layout of valorant_runner & racing_runner."""

    # Dark cyber palette
    BG = "#121214"
    SURFACE = "#1a1a1e"
    OVERLAY = "#26262b"
    FG = "#e1e1e6"
    ACCENT = "#eab308"   # Pac-Man classic gold/yellow accent
    GREEN = "#22c55e"
    RED = "#ef4444"
    YELLOW = "#eab308"

    def __init__(self, root, capture_mode: str = "camera", camera_index: int = 0):
        self.root = root
        self.capture_mode = capture_mode
        self.camera_index = camera_index
        self.root.title("Pac-Man Auto-Pilot")
        self.root.geometry("860x780")
        self.root.configure(bg=self.BG)
        self.root.resizable(True, True)

        # Shared ESP32 actuator controller
        self.ctrl = ActuatorController()
        self.ctrl.on_response = self._on_serial_response
        self.ctrl.on_status = self._on_serial_status
        self.ctrl.on_error = self._on_serial_error
        self.ctrl.on_disconnect = self._on_serial_disconnect

        self.vision = VisionEngine(capture_mode=capture_mode)

        self._autopilot_active = False
        self._last_sent_servos = None
        self._esp_state = "IDLE"

        self._build_ui()
        self._refresh_ports()
        self._update_loop()

    # ── UI Construction ─────────────────────────────────────────

    def _build_ui(self):
        # Header Title
        tk.Label(self.root, text="Pac-Man Auto-Pilot",
                 font=("Segoe UI", 16, "bold"), bg=self.BG, fg=self.ACCENT
                 ).grid(row=0, column=0, columnspan=2, pady=(10, 2))
        tk.Label(self.root, text="Screen Capture → Maze CV → Left Joystick Servos → ESP32",
                 font=("Segoe UI", 9), bg=self.BG, fg=self.OVERLAY
                 ).grid(row=1, column=0, columnspan=2)

        # Left Column: Camera Feed & CV Edge Debugger
        left = tk.Frame(self.root, bg=self.BG)
        left.grid(row=2, column=0, padx=(12, 6), pady=8, sticky="n")

        self.camera_label = tk.Label(left, bg="#000000", width=52, height=18)
        self.camera_label.pack()

        self.debug_label = tk.Label(left, bg="#111111", width=52, height=8)
        self.debug_label.pack(pady=(6, 0))

        # Right Column: Controls & Connection
        right = tk.Frame(self.root, bg=self.BG)
        right.grid(row=2, column=1, padx=(6, 12), pady=8, sticky="n")

        # 1. Connection Panel
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
        self.cam_var = tk.IntVar(value=self.camera_index)
        self.cam_spin = tk.Spinbox(r2, from_=0, to=5, textvariable=self.cam_var,
                                   width=3, font=("Segoe UI", 9))
        self.cam_spin.pack(side="left", padx=4)
        if self.capture_mode == "screen":
            tk.Label(r2, text="[SCREEN]", bg=self.SURFACE, fg=self.ACCENT,
                     font=("Segoe UI", 8, "bold")).pack(side="left", padx=4)

        # 2. ESP32 State Indicator
        state_f = tk.Frame(right, bg=self.BG)
        state_f.pack(fill="x", pady=4)
        tk.Label(state_f, text="ESP32:", bg=self.BG, fg=self.FG,
                 font=("Segoe UI", 9)).pack(side="left")
        self.state_label = tk.Label(state_f, text="DISCONNECTED",
                                    bg=self.BG, fg=self.RED,
                                    font=("Segoe UI", 10, "bold"))
        self.state_label.pack(side="left", padx=4)

        # 3. Main Autopilot Action Button
        self.btn_autopilot = tk.Button(right, text="▶  START AUTO-PILOT",
                                       width=28, height=2,
                                       command=self._toggle_autopilot,
                                       bg=self.GREEN, fg=self.BG, relief="flat",
                                       font=("Segoe UI", 11, "bold"),
                                       state="disabled")
        self.btn_autopilot.pack(pady=8)

        # 4. Live Status Panel
        status_f = tk.LabelFrame(right, text=" Live Status ", font=("Segoe UI", 9, "bold"),
                                 bg=self.SURFACE, fg=self.FG, padx=8, pady=6)
        status_f.pack(fill="x", pady=(0, 6))

        self.action_label = tk.Label(status_f, text="IDLE",
                                     bg=self.SURFACE, fg=self.YELLOW,
                                     font=("Consolas", 14, "bold"))
        self.action_label.pack()

        self.servo_label = tk.Label(status_f, text="LJ(90,90) RJ(90,90) T:0",
                                    bg=self.SURFACE, fg=self.FG,
                                    font=("Consolas", 10))
        self.servo_label.pack()

        self.fps_label = tk.Label(status_f, text="FPS: --",
                                  bg=self.SURFACE, fg=self.OVERLAY,
                                  font=("Segoe UI", 8))
        self.fps_label.pack()

        self.density_label = tk.Label(status_f, text="L: --  C: --  R: --",
                                      bg=self.SURFACE, fg=self.FG,
                                      font=("Consolas", 9))
        self.density_label.pack(pady=(4, 0))

        # 5. Live Tuning Sliders
        tune = tk.LabelFrame(right, text=" Tuning ", font=("Segoe UI", 9, "bold"),
                             bg=self.SURFACE, fg=self.FG, padx=8, pady=4)
        tune.pack(fill="x", pady=(0, 6))

        self.sens_var = tk.IntVar(value=35)
        self._add_slider(tune, "Yellow Sens", self.sens_var, 10, 80)

        self.crop_var = tk.DoubleVar(value=85.0)
        self._add_slider(tune, "HUD Crop %", self.crop_var, 50.0, 100.0)

        self.emin_var = tk.IntVar(value=40)
        self._add_slider(tune, "Edge Min", self.emin_var, 0, 255)

        self.emax_var = tk.IntVar(value=120)
        self._add_slider(tune, "Edge Max", self.emax_var, 0, 255)

        # 6. Data Collection Checkbox
        self.collect_var = tk.BooleanVar(value=False)
        tk.Checkbutton(right, text="Collect training data",
                       variable=self.collect_var, bg=self.BG, fg=self.FG,
                       selectcolor=self.SURFACE, font=("Segoe UI", 9),
                       activebackground=self.BG, activeforeground=self.FG
                       ).pack(anchor="w")

        # 7. Serial Terminal Log
        log_f = tk.LabelFrame(self.root, text=" Serial Log ", font=("Segoe UI", 9, "bold"),
                              bg=self.SURFACE, fg=self.FG, padx=4, pady=2)
        log_f.grid(row=3, column=0, columnspan=2, padx=12, pady=(0, 10), sticky="ew")

        self.log_text = scrolledtext.ScrolledText(log_f, height=5, bg=self.BG,
                                                  fg=self.GREEN, font=("Consolas", 8),
                                                  relief="flat", state="disabled",
                                                  wrap="word")
        self.log_text.pack(fill="x")

    def _add_slider(self, parent, label, var, from_, to):
        row = tk.Frame(parent, bg=self.SURFACE)
        row.pack(fill="x", pady=1)
        tk.Label(row, text=label, bg=self.SURFACE, fg=self.FG,
                 font=("Segoe UI", 8), width=14, anchor="w").pack(side="left")
        res = 0.1 if isinstance(var, tk.DoubleVar) else 1
        tk.Scale(row, from_=from_, to=to, orient="horizontal", variable=var,
                 bg=self.SURFACE, fg=self.FG, highlightthickness=0,
                 troughcolor=self.OVERLAY, font=("Segoe UI", 7),
                 resolution=res, length=160).pack(side="left", fill="x", expand=True)

    # ── Connection Handling ─────────────────────────────────────

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
            self._log("Disconnected from ESP32.")
            self.btn_connect.config(text="Connect", bg=self.ACCENT)
            self.state_label.config(text="DISCONNECTED", fg=self.RED)
            self._esp_state = "IDLE"
            self.btn_autopilot.config(state="disabled")
        else:
            port = self.port_var.get()
            if not port:
                messagebox.showwarning("No Port", "Select an ESP32 COM port first.")
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

    # ── Auto-Pilot Control ──────────────────────────────────────

    def _toggle_autopilot(self):
        if self._autopilot_active:
            self._stop_autopilot()
        else:
            self._start_autopilot()

    def _start_autopilot(self):
        cam_idx = self.cam_var.get()
        if not self.vision.open_camera(cam_idx):
            messagebox.showerror("Camera Error",
                                 f"Could not open camera index {cam_idx}.\nCheck connections.")
            return

        # Start servo mode on ESP32 (VALORANT servo mode drives joysticks)
        self.ctrl.set_valorant_mode()
        time.sleep(0.3)
        self.ctrl.start()
        time.sleep(0.3)

        self.vision.start()
        self._autopilot_active = True
        self._last_sent_servos = None

        self.btn_autopilot.config(text="■  STOP AUTO-PILOT", bg=self.RED)
        mode_desc = "Screen Capture" if self.capture_mode == "screen" else f"Camera #{cam_idx}"
        self._log(f"Pac-Man Auto-Pilot STARTED ({mode_desc}).")

    def _stop_autopilot(self):
        self.vision.stop()
        self.vision.close_camera()

        # Send neutral joystick position
        self.ctrl.send_servo(90, 90, 90, 90, 0, 200)
        time.sleep(0.1)
        self.ctrl.stop()
        time.sleep(0.1)
        self.ctrl.reset()

        self._autopilot_active = False
        self._last_sent_servos = None

        self.btn_autopilot.config(text="▶  START AUTO-PILOT", bg=self.GREEN)
        self._log("Pac-Man Auto-Pilot STOPPED.")

    # ── Main Update Loop (Tkinter thread) ───────────────────────

    def _update_loop(self):
        # Update live slider params
        self.vision.yellow_sens = self.sens_var.get()
        self.vision.hud_crop_pct = self.crop_var.get() / 100.0
        self.vision.canny_min = self.emin_var.get()
        self.vision.canny_max = self.emax_var.get()
        self.vision.collect_data = self.collect_var.get()

        if self._autopilot_active:
            frame = self.vision.last_frame
            if frame is not None:
                self._show_image(self.camera_label, frame, max_w=420, max_h=280)

            debug = self.vision.last_debug
            if debug is not None:
                self._show_image(self.debug_label, debug, max_w=420, max_h=130)

            action = self.vision.last_action
            ljx, ljy, rjx, rjy, trig = self.vision.last_servo_values
            ld, cd, rd = self.vision.last_densities

            action_colors = {"UP": self.GREEN, "DOWN": self.GREEN,
                             "LEFT": self.ACCENT, "RIGHT": self.ACCENT, "IDLE": self.YELLOW}
            self.action_label.config(text=action, fg=action_colors.get(action, self.FG))
            self.servo_label.config(text=f"LJ({ljx},{ljy})  RJ({rjx},{rjy})  T:{trig}")
            self.fps_label.config(text=f"FPS: {self.vision.fps:.0f}")
            self.density_label.config(text=f"L: {ld:.1f}%  C: {cd:.1f}%  R: {rd:.1f}%")

            # Send servo position to ESP32 (only on change or heartbeat)
            self._send_servos(ljx, ljy, rjx, rjy, trig)

        self.root.after(33, self._update_loop)

    def _send_servos(self, ljx, ljy, rjx, rjy, trig):
        if not self.ctrl.is_connected:
            return

        vals = (ljx, ljy, rjx, rjy, trig)
        # Send immediately when direction changes
        if self._last_sent_servos != vals:
            self.ctrl.send_servo(ljx, ljy, rjx, rjy, trig, duration=80)
            self._last_sent_servos = vals

    def _show_image(self, label, cv_img, max_w, max_h):
        h, w = cv_img.shape[:2]
        scale = min(max_w / w, max_h / h, 1.0)
        nw, nh = int(w * scale), int(h * scale)
        resized = cv2.resize(cv_img, (nw, nh), interpolation=cv2.INTER_AREA)

        rgb = cv2.cvtColor(resized, cv2.COLOR_BGR2RGB)
        img_pi = ImageTk.PhotoImage(Image.fromarray(rgb))
        label.config(image=img_pi, width=0, height=0)
        label.image = img_pi

    # ── Serial Callbacks & Logging ──────────────────────────────

    def _on_serial_response(self, line: str):
        self._log(f"← {line}")

    def _on_serial_status(self, mode: str, state: str):
        self._esp_state = state
        colors = {"RUNNING": self.GREEN, "MODE_SET": self.YELLOW,
                  "STOPPED": self.RED, "IDLE": self.YELLOW}
        self.state_label.config(text=f"{mode}:{state}", fg=colors.get(state, self.FG))

    def _on_serial_error(self, code: int, msg: str):
        self._log(f"[ERR {code}] {msg}")

    def _on_serial_disconnect(self):
        self.state_label.config(text="DISCONNECTED", fg=self.RED)
        self.btn_connect.config(text="Connect", bg=self.ACCENT)
        self.btn_autopilot.config(state="disabled")

    def _log(self, text: str):
        self.log_text.config(state="normal")
        self.log_text.insert("end", text + "\n")
        self.log_text.see("end")
        self.log_text.config(state="disabled")


def parse_args(args=None):
    parser = argparse.ArgumentParser(description="Pac-Man Auto-Pilot Dashboard")
    parser.add_argument(
        "--capture-mode",
        "--capture_mode",
        dest="capture_mode",
        choices=["screen", "camera"],
        default="camera",
        help="Capture source: 'screen' (in-computer) or 'camera' (external computer, default)",
    )
    parser.add_argument(
        "--camera",
        type=int,
        default=0,
        help="Camera device index (default: 0)",
    )
    return parser.parse_args(args)


if __name__ == "__main__":
    cli_args = parse_args()
    root = tk.Tk()
    app = PacmanAutoPilotApp(root, capture_mode=cli_args.capture_mode, camera_index=cli_args.camera)
    root.protocol("WM_DELETE_WINDOW", lambda: (app._stop_autopilot(), app.ctrl.disconnect(), root.destroy()))
    root.mainloop()

