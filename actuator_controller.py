"""
actuator_controller.py
Shared serial protocol handler for the ESP32 actuator.

Speaks the protocol defined in ActuatorProgram/include/README.md:
  MODE,SET,VALORANT / MODE,SET,RACING / MODE,START / MODE,STOP / MODE,RESET / MODE,STATUS
  SERVO,LJX,LJY,RJX,RJY,TRIGGER[,DURATION]  (Valorant mode)
  STEPPER,LEFT[,RATE_HZ] / STEPPER,RIGHT[,RATE_HZ] / STEPPER,STOP  (Racing mode)
"""

import threading
import time
import serial
import serial.tools.list_ports


class ActuatorController:
    """Thread-safe serial controller for the ESP32 actuator (Valorant + Racing)."""

    BAUD_RATE = 115200

    def __init__(self):
        self._ser = None
        self._lock = threading.Lock()
        self._reader_thread = None
        self._running = False

        # Callbacks – set by the GUI layer
        self.on_response = None   # callable(str)  – every raw line from ESP32
        self.on_status = None     # callable(mode: str, state: str)
        self.on_error = None      # callable(code: int, msg: str)
        self.on_ok = None         # callable()
        self.on_disconnect = None # callable()

    # ── connection ──────────────────────────────────────────────

    @staticmethod
    def list_ports():
        """Return a list of available COM port names."""
        return [p.device for p in serial.tools.list_ports.comports()]

    def connect(self, port: str) -> bool:
        """Open the serial port and start the background reader."""
        if self._ser and self._ser.is_open:
            return True
        try:
            self._ser = serial.Serial(port, self.BAUD_RATE, timeout=0.1)
            time.sleep(2)  # ESP32 resets on serial open; wait for boot
            self._running = True
            self._reader_thread = threading.Thread(
                target=self._read_loop, daemon=True
            )
            self._reader_thread.start()
            return True
        except serial.SerialException:
            self._ser = None
            return False

    def disconnect(self):
        """Stop the reader and close the serial port."""
        self._running = False
        if self._reader_thread:
            self._reader_thread.join(timeout=2)
            self._reader_thread = None
        with self._lock:
            if self._ser and self._ser.is_open:
                try:
                    self._ser.close()
                except Exception:
                    pass
            self._ser = None
        if self.on_disconnect:
            self.on_disconnect()

    @property
    def is_connected(self) -> bool:
        return self._ser is not None and self._ser.is_open

    # ── mode commands ───────────────────────────────────────────

    def set_valorant_mode(self):
        """MODE,SET,VALORANT"""
        self._send("MODE,SET,VALORANT")

    def set_racing_mode(self):
        """MODE,SET,RACING"""
        self._send("MODE,SET,RACING")

    def start(self):
        """MODE,START"""
        self._send("MODE,START")

    def stop(self):
        """MODE,STOP"""
        self._send("MODE,STOP")

    def reset(self):
        """MODE,RESET"""
        self._send("MODE,RESET")

    def get_status(self):
        """MODE,STATUS"""
        self._send("MODE,STATUS")

    # ── servo commands (Valorant) ───────────────────────────────

    def send_servo(self, ljx: int = 90, ljy: int = 90, rjx: int = 90,
                   rjy: int = 90, trigger: int = 0, duration: int = 200):
        """SERVO,LJX,LJY,RJX,RJY,TRIGGER,DURATION"""
        self._send(f"SERVO,{ljx},{ljy},{rjx},{rjy},{trigger},{duration}")

    # ── stepper commands (Racing) ───────────────────────────────

    def steer_left(self, rate_hz: int = 400):
        """STEPPER,LEFT,<rate_hz>"""
        self._send(f"STEPPER,LEFT,{rate_hz}")

    def steer_right(self, rate_hz: int = 400):
        """STEPPER,RIGHT,<rate_hz>"""
        self._send(f"STEPPER,RIGHT,{rate_hz}")

    def steer_stop(self):
        """STEPPER,STOP"""
        self._send("STEPPER,STOP")

    # ── internals ───────────────────────────────────────────────

    def _send(self, cmd: str):
        """Send a newline-terminated command to the ESP32."""
        with self._lock:
            if not self._ser or not self._ser.is_open:
                return
            try:
                self._ser.write((cmd + "\n").encode("utf-8"))
            except serial.SerialException:
                self.disconnect()

    def _read_loop(self):
        """Background thread: continuously read lines from ESP32."""
        while self._running:
            try:
                with self._lock:
                    if not self._ser or not self._ser.is_open:
                        break
                    raw = self._ser.readline()
                if not raw:
                    continue
                line = raw.decode("utf-8", errors="ignore").strip()
                if not line:
                    continue
                self._dispatch(line)
            except serial.SerialException:
                self._running = False
                self.disconnect()
                break
            except Exception:
                continue

    def _dispatch(self, line: str):
        """Parse a response line and invoke the appropriate callback."""
        # Always forward the raw line
        if self.on_response:
            self.on_response(line)

        parts = line.split(",")
        tag = parts[0] if parts else ""

        if tag == "OK":
            if self.on_ok:
                self.on_ok()

        elif tag == "ERR" and len(parts) >= 3:
            try:
                code = int(parts[1])
            except ValueError:
                code = -1
            msg = ",".join(parts[2:])
            if self.on_error:
                self.on_error(code, msg)

        elif tag == "STATUS" and len(parts) >= 3:
            mode = parts[1]
            state = parts[2]
            if self.on_status:
                self.on_status(mode, state)
