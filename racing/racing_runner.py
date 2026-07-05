"""
racing_runner.py
Autonomous Racing Auto-Pilot Dashboard.

Captures USB camera feed → runs Canny edge-density analysis (left / center / right)
→ decides steering direction → sends STEPPER commands to ESP32 proportionally.

Optionally collects labelled training frames for future CNN model training.

Protocol reference:  ActuatorProgram/include/README.md
CV logic based on:   mapper/test.py
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

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from actuator_controller import ActuatorController


# ═══════════════════════════════════════════════════════════════
#  Vision Engine — runs in a background thread
# ═══════════════════════════════════════════════════════════════

class VisionEngine:
    """Camera capture + Canny edge-density analysis + steering decision."""

    # Proportional steering: map density difference → stepper Hz
    MIN_STEER_HZ = 150
    MAX_STEER_HZ = 800

    def __init__(self):
        self.cap = None
        self.running = False
        self._thread = None

        # Tunable parameters (updated from GUI sliders)
        self.turn_threshold = 5.0   # edge-density % above which center is "blocked"
        self.hud_crop_pct = 0.75    # crop bottom N% of frame (ignore HUD)
        self.roi_top_pct = 0.4      # ROI starts at 40% from top
        self.canny_min = 30
        self.canny_max = 100

        # Latest results (read by GUI on main thread)
        self.last_frame = None        # raw BGR frame
        self.last_debug = None        # edge-density debug image (BGR)
        self.last_action = "IDLE"     # "LEFT", "RIGHT", "STRAIGHT", "IDLE"
        self.last_steer_hz = 0        # proportional speed for stepper
        self.last_densities = (0.0, 0.0, 0.0)  # (left, center, right)
        self.fps = 0.0

        # Training data collection
        self.collect_data = False
        self.data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "training_data")
        self._frame_counter = 0
        self._save_every_n = 5  # save every Nth frame

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
            if not self.cap or not self.cap.isOpened():
                time.sleep(0.05)
                continue

            ret, frame = self.cap.read()
            if not ret:
                time.sleep(0.01)
                continue

            # FPS
            now = time.time()
            dt = now - prev_time
            self.fps = 1.0 / dt if dt > 0 else 0
            prev_time = now

            self.last_frame = frame.copy()

            # Analyze
            action, steer_hz, densities, debug_img = self._analyze(frame)
            self.last_action = action
            self.last_steer_hz = steer_hz
            self.last_densities = densities
            self.last_debug = debug_img

            # Collect training data
            if self.collect_data:
                self._frame_counter += 1
                if self._frame_counter % self._save_every_n == 0:
                    self._save_frame(frame, action)

            time.sleep(0.01)  # ~30-60 FPS cap

    def _analyze(self, frame):
        """Run Canny edge-density on L/C/R slices and decide steering."""
        h, w = frame.shape[:2]

        roi_top = int(h * self.roi_top_pct)
        roi_bottom = int(h * self.hud_crop_pct)
        if roi_bottom <= roi_top:
            roi_bottom = roi_top + 10
        roi = frame[roi_top:roi_bottom, :]

        third_w = max(w // 3, 1)
        left_slice = roi[:, :third_w]
        center_slice = roi[:, third_w:third_w * 2]
        right_slice = roi[:, third_w * 2:]

        left_d, left_edges = self._edge_density(left_slice)
        center_d, center_edges = self._edge_density(center_slice)
        right_d, right_edges = self._edge_density(right_slice)

        densities = (left_d, center_d, right_d)

        # ── decision logic ──────────────────────────────────────
        action = "STRAIGHT"
        steer_hz = 0

        if center_d < self.turn_threshold:
            # Road ahead is clear → go straight
            action = "STRAIGHT"
            steer_hz = 0
        else:
            # Center blocked → steer toward the more open side
            diff = abs(left_d - right_d)
            # Proportional speed: bigger difference = harder turn
            steer_hz = self._map_hz(diff, center_d)

            if left_d < right_d:
                action = "LEFT"
            else:
                action = "RIGHT"

        # ── debug visualization ─────────────────────────────────
        debug_img = self._build_debug(
            left_edges, center_edges, right_edges,
            left_d, center_d, right_d,
            third_w, roi_bottom - roi_top, action, steer_hz
        )

        return action, steer_hz, densities, debug_img

    def _edge_density(self, roi_slice):
        gray = cv2.cvtColor(roi_slice, cv2.COLOR_BGR2GRAY)
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)
        edges = cv2.Canny(blurred, self.canny_min, self.canny_max)
        total = edges.shape[0] * edges.shape[1]
        if total == 0:
            return 0.0, edges
        density = (cv2.countNonZero(edges) / total) * 100
        return density, edges

    def _map_hz(self, density_diff, center_density):
        """Map edge-density metrics to stepper Hz (proportional steering)."""
        # Two factors: how blocked the center is + how different L/R are
        # Normalize center_density relative to threshold (1.0 = at threshold, 3.0 = heavily blocked)
        center_factor = min(center_density / max(self.turn_threshold, 0.1), 3.0)
        # Normalize diff (0-20% range is typical)
        diff_factor = min(density_diff / 15.0, 1.0)
        # Combine: center urgency (70%) + directional clarity (30%)
        combined = 0.7 * (center_factor / 3.0) + 0.3 * diff_factor
        combined = max(0.0, min(combined, 1.0))

        hz = int(self.MIN_STEER_HZ + combined * (self.MAX_STEER_HZ - self.MIN_STEER_HZ))
        return max(self.MIN_STEER_HZ, min(hz, self.MAX_STEER_HZ))

    def _build_debug(self, le, ce, re, ld, cd, rd, tw, rh, action, hz):
        debug = np.hstack((le, ce, re))
        debug = cv2.cvtColor(debug, cv2.COLOR_GRAY2BGR)
        # Divider lines
        cv2.line(debug, (tw, 0), (tw, rh), (255, 0, 0), 2)
        cv2.line(debug, (tw * 2, 0), (tw * 2, rh), (255, 0, 0), 2)
        # Density labels
        c_color = (0, 255, 0) if cd < self.turn_threshold else (0, 0, 255)
        cv2.putText(debug, f"L:{ld:.1f}%", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
        cv2.putText(debug, f"C:{cd:.1f}%", (tw + 10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.6, c_color, 2)
        cv2.putText(debug, f"R:{rd:.1f}%", (tw * 2 + 10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
        # Action + speed
        cv2.putText(debug, f"{action}  {hz}Hz", (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
        return debug

    def _save_frame(self, frame, action):
        label = action.lower()  # "left", "right", "straight"
        folder = os.path.join(self.data_dir, label)
        os.makedirs(folder, exist_ok=True)
        fname = f"frame_{int(time.time()*1000)}.jpg"
        cv2.imwrite(os.path.join(folder, fname), frame)


# ═══════════════════════════════════════════════════════════════
#  Auto-Pilot GUI
# ═══════════════════════════════════════════════════════════════

class AutoPilotGUI:
    """Racing Auto-Pilot Dashboard — camera preview + autonomous steering."""

    BG        = "#1e1e2e"
    FG        = "#cdd6f4"
    ACCENT    = "#89b4fa"
    GREEN     = "#a6e3a1"
    RED       = "#f38ba8"
    YELLOW    = "#f9e2af"
    SURFACE   = "#313244"
    OVERLAY   = "#45475a"

    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Racing Auto-Pilot")
        self.root.geometry("860x780")
        self.root.configure(bg=self.BG)
        self.root.resizable(False, False)

        self.ctrl = ActuatorController()
        self.ctrl.on_response = self._on_serial_response
        self.ctrl.on_status = self._on_serial_status
        self.ctrl.on_error = self._on_serial_error
        self.ctrl.on_disconnect = self._on_serial_disconnect

        self.vision = VisionEngine()

        self._autopilot_active = False
        self._last_sent_action = None  # rate-limit: only send on change
        self._esp_state = "IDLE"

        self._build_ui()
        self._refresh_ports()
        self._update_loop()

    # ── UI ──────────────────────────────────────────────────────

    def _build_ui(self):
        # Title
        tk.Label(self.root, text="Racing Auto-Pilot",
                 font=("Segoe UI", 16, "bold"), bg=self.BG, fg=self.ACCENT
                 ).grid(row=0, column=0, columnspan=2, pady=(10, 2))
        tk.Label(self.root, text="Camera → AI → ESP32 Stepper",
                 font=("Segoe UI", 9), bg=self.BG, fg=self.OVERLAY
                 ).grid(row=1, column=0, columnspan=2)

        # ── Left column: camera + debug ─────────────────────────
        left = tk.Frame(self.root, bg=self.BG)
        left.grid(row=2, column=0, padx=(12, 6), pady=8, sticky="n")

        # Camera preview
        self.camera_label = tk.Label(left, bg="#000000", width=52, height=18)
        self.camera_label.pack()

        # Debug (edge density) preview
        self.debug_label = tk.Label(left, bg="#111111", width=52, height=8)
        self.debug_label.pack(pady=(6, 0))

        # ── Right column: controls ──────────────────────────────
        right = tk.Frame(self.root, bg=self.BG)
        right.grid(row=2, column=1, padx=(6, 12), pady=8, sticky="n")

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
        self.cam_spin = tk.Spinbox(r2, from_=0, to=5, textvariable=self.cam_var,
                                    width=3, font=("Segoe UI", 9))
        self.cam_spin.pack(side="left", padx=4)

        # State display
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
        self.btn_autopilot.pack(pady=8)

        # Live status
        status_f = tk.LabelFrame(right, text=" Live Status ", font=("Segoe UI", 9, "bold"),
                                  bg=self.SURFACE, fg=self.FG, padx=8, pady=6)
        status_f.pack(fill="x", pady=(0, 6))

        self.action_label = tk.Label(status_f, text="IDLE",
                                      bg=self.SURFACE, fg=self.YELLOW,
                                      font=("Consolas", 14, "bold"))
        self.action_label.pack()
        self.hz_label = tk.Label(status_f, text="0 Hz",
                                  bg=self.SURFACE, fg=self.FG,
                                  font=("Consolas", 10))
        self.hz_label.pack()
        self.fps_label = tk.Label(status_f, text="FPS: --",
                                   bg=self.SURFACE, fg=self.OVERLAY,
                                   font=("Segoe UI", 8))
        self.fps_label.pack()
        self.density_label = tk.Label(status_f, text="L: --  C: --  R: --",
                                       bg=self.SURFACE, fg=self.FG,
                                       font=("Consolas", 9))
        self.density_label.pack(pady=(4, 0))

        # Tuning sliders
        tune = tk.LabelFrame(right, text=" Tuning ", font=("Segoe UI", 9, "bold"),
                              bg=self.SURFACE, fg=self.FG, padx=8, pady=4)
        tune.pack(fill="x", pady=(0, 6))

        self.thresh_var = tk.DoubleVar(value=5.0)
        self._add_slider(tune, "Turn Threshold %", self.thresh_var, 0.5, 20.0)

        self.crop_var = tk.DoubleVar(value=75.0)
        self._add_slider(tune, "HUD Crop %", self.crop_var, 40.0, 100.0)

        self.emin_var = tk.IntVar(value=30)
        self._add_slider(tune, "Edge Min", self.emin_var, 0, 255)

        self.emax_var = tk.IntVar(value=100)
        self._add_slider(tune, "Edge Max", self.emax_var, 0, 255)

        # Data collection toggle
        self.collect_var = tk.BooleanVar(value=False)
        tk.Checkbutton(right, text="Collect training data",
                       variable=self.collect_var, bg=self.BG, fg=self.FG,
                       selectcolor=self.SURFACE, font=("Segoe UI", 9),
                       activebackground=self.BG, activeforeground=self.FG
                       ).pack(anchor="w")

        # Serial log
        log_f = tk.LabelFrame(self.root, text=" Serial Log ", font=("Segoe UI", 9, "bold"),
                               bg=self.SURFACE, fg=self.FG, padx=4, pady=2)
        log_f.grid(row=3, column=0, columnspan=2, padx=12, pady=(0, 10),
                   sticky="ew")

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
                self._log(f"Connected @ 115200 baud.")
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
        # Open camera
        cam_idx = self.cam_var.get()
        if not self.vision.open_camera(cam_idx):
            messagebox.showerror("Camera Error",
                                 f"Could not open camera index {cam_idx}.\n"
                                 "Try a different index.")
            return

        # Set racing mode + start on ESP32
        self.ctrl.set_racing_mode()
        time.sleep(0.3)
        self.ctrl.start()
        time.sleep(0.3)

        # Start vision loop
        self.vision.start()
        self._autopilot_active = True
        self._last_sent_action = None

        self.btn_autopilot.config(text="■  STOP AUTO-PILOT", bg=self.RED)
        self._log("Auto-pilot STARTED.")

    def _stop_autopilot(self):
        # Stop vision
        self.vision.stop()
        self.vision.close_camera()

        # Stop stepper + mode
        self.ctrl.steer_stop()
        time.sleep(0.1)
        self.ctrl.stop()
        time.sleep(0.1)
        self.ctrl.reset()

        self._autopilot_active = False
        self._last_sent_action = None

        self.btn_autopilot.config(text="▶  START AUTO-PILOT", bg=self.GREEN)
        self._log("Auto-pilot STOPPED.")

    # ── main update loop (runs on Tk main thread) ──────────────

    def _update_loop(self):
        # Push slider values to vision engine
        self.vision.turn_threshold = self.thresh_var.get()
        self.vision.hud_crop_pct = self.crop_var.get() / 100.0
        self.vision.canny_min = self.emin_var.get()
        self.vision.canny_max = self.emax_var.get()
        self.vision.collect_data = self.collect_var.get()

        if self._autopilot_active:
            # Update camera preview
            frame = self.vision.last_frame
            if frame is not None:
                self._show_image(self.camera_label, frame, max_w=420, max_h=280)

            debug = self.vision.last_debug
            if debug is not None:
                self._show_image(self.debug_label, debug, max_w=420, max_h=130)

            # Update status labels
            action = self.vision.last_action
            hz = self.vision.last_steer_hz
            ld, cd, rd = self.vision.last_densities

            action_colors = {"LEFT": self.ACCENT, "RIGHT": self.ACCENT,
                             "STRAIGHT": self.GREEN, "IDLE": self.YELLOW}
            self.action_label.config(text=f"⟵ {action}" if action == "LEFT"
                                     else f"{action} ⟶" if action == "RIGHT"
                                     else action,
                                     fg=action_colors.get(action, self.FG))
            self.hz_label.config(text=f"{hz} Hz" if hz > 0 else "Centered")
            self.fps_label.config(text=f"FPS: {self.vision.fps:.0f}")
            self.density_label.config(text=f"L: {ld:.1f}%  C: {cd:.1f}%  R: {rd:.1f}%")

            # Send steering command to ESP32 (only on change)
            self._send_steering(action, hz)

        self.root.after(33, self._update_loop)  # ~30 FPS GUI refresh

    def _send_steering(self, action, hz):
        """Send stepper command only when direction changes."""
        if not self.ctrl.is_connected:
            return

        key = (action, hz)

        # Always send on direction change; also resend if Hz changed significantly
        if self._last_sent_action is not None:
            last_action, last_hz = self._last_sent_action
            if last_action == action:
                # Same direction: only resend if speed changed by >50 Hz
                if abs(hz - last_hz) < 50:
                    return

        if action == "LEFT":
            self.ctrl.steer_left(hz)
        elif action == "RIGHT":
            self.ctrl.steer_right(hz)
        else:
            self.ctrl.steer_stop()

        self._last_sent_action = key

    def _show_image(self, label, cv_img, max_w, max_h):
        """Convert OpenCV BGR image to Tkinter PhotoImage and display."""
        h, w = cv_img.shape[:2]
        scale = min(max_w / w, max_h / h, 1.0)
        if scale < 1.0:
            new_w, new_h = int(w * scale), int(h * scale)
            cv_img = cv2.resize(cv_img, (new_w, new_h))
        rgb = cv2.cvtColor(cv_img, cv2.COLOR_BGR2RGB)
        pil_img = Image.fromarray(rgb)
        tk_img = ImageTk.PhotoImage(pil_img)
        label.config(image=tk_img)
        label._photo = tk_img  # prevent garbage collection

    # ── serial callbacks (from reader thread) ───────────────────

    def _on_serial_response(self, line):
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
                self._stop_autopilot()
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
            self._stop_autopilot()
        if self.ctrl.is_connected:
            self.ctrl.disconnect()
        self.root.destroy()


# ── standalone launch ───────────────────────────────────────────

if __name__ == "__main__":
    root = tk.Tk()
    app = AutoPilotGUI(root)
    root.protocol("WM_DELETE_WINDOW", app.on_close)
    root.mainloop()
