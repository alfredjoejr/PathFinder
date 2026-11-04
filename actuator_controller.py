"""
actuator_controller.py
Shared serial protocol handler for the ESP32 actuator.

Speaks the official Actuator Protocol Guide:
  MODE,SET,VALORANT / MODE,SET,RACING / MODE,START / MODE,STOP / MODE,RESET / MODE,STATUS
  SERVO,LJX,LJY,RJX,RJY,TRIGGER[,DURATION]  (Valorant mode: servos 0-4)
  RACE,LEFT,<RATE_HZ>,<LEFT_PADDLE>,<RIGHT_PADDLE>  (Racing mode: combined stepper + paddles)
  RACE,RIGHT,<RATE_HZ>,<LEFT_PADDLE>,<RIGHT_PADDLE>
  RACE,STOP  (Halts stepper and resets paddles 5 & 6 to 90)
  STEPPER,LEFT[,RATE_HZ] / STEPPER,RIGHT[,RATE_HZ] / STEPPER,STOP  (Racing stepper only)

Includes a built-in "VIRTUAL_COM" mock mode so the full auto-pilot vision
pipeline and GUI can be tested on machines without physical ESP32 hardware attached.
"""

import threading
import time
import queue
import serial
import serial.tools.list_ports


class ActuatorController:
    """Thread-safe serial controller for the ESP32 actuator (Valorant + Racing)."""

    BAUD_RATE = 115200
    VIRTUAL_PORT = "VIRTUAL_COM"

    def __init__(self):
        self._ser = None
        self._lock = threading.Lock()
        self._reader_thread = None
        self._running = False
        self._is_virtual = False
        self._virt_queue = queue.Queue()
        self._virt_mode = "NONE"
        self._virt_state = "IDLE"

        # Synchronization support
        self._status_event = threading.Event()
        self._last_status = ("NONE", "IDLE")

        # Callbacks – set by the GUI layer
        self.on_response = None   # callable(str)  – every raw line from ESP32
        self.on_status = None     # callable(mode: str, state: str)
        self.on_error = None      # callable(code: int, msg: str)
        self.on_ok = None         # callable()
        self.on_disconnect = None # callable()

    # ── connection ──────────────────────────────────────────────

    @classmethod
    def list_ports(cls):
        """Return a list of available COM port names + VIRTUAL_COM for offline testing."""
        ports = [p.device for p in serial.tools.list_ports.comports()]
        if cls.VIRTUAL_PORT not in ports:
            ports.append(cls.VIRTUAL_PORT)
        return ports

    def connect(self, port: str) -> bool:
        """Open the serial port (or virtual mock) and start the background reader."""
        if self.is_connected:
            return True

        if port == self.VIRTUAL_PORT:
            self._is_virtual = True
            self._virt_mode = "NONE"
            self._virt_state = "IDLE"
            self._running = True
            self._reader_thread = threading.Thread(
                target=self._virtual_reader_loop, daemon=True
            )
            self._reader_thread.start()
            # Push initial firmware greeting
            self._virt_queue.put("DEBUG,Virtual ESP32 firmware initialized")
            self._virt_queue.put("STATUS,NONE,IDLE")
            return True

        try:
            self._is_virtual = False
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
        """Stop the reader and close the serial port / virtual mock."""
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
            self._is_virtual = False

        if self.on_disconnect:
            self.on_disconnect()

    @property
    def is_connected(self) -> bool:
        if self._is_virtual and self._running:
            return True
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

    # ── synchronous mode transitions ────────────────────────────

    def wait_for_status(self, expected_state: str, expected_mode: str = None, timeout: float = 2.0) -> bool:
        """Wait until a STATUS line with expected_state (and optional expected_mode) is received."""
        start = time.time()
        while time.time() - start < timeout:
            remaining = timeout - (time.time() - start)
            if remaining <= 0:
                break
            if self._status_event.wait(timeout=max(0.01, min(0.1, remaining))):
                mode, state = self._last_status
                if state == expected_state:
                    if expected_mode is None or mode == expected_mode:
                        return True
                self._status_event.clear()
        return False

    def set_racing_mode_sync(self, timeout: float = 2.0) -> bool:
        """Send MODE,SET,RACING and await STATUS,RACING,MODE_SET."""
        self._status_event.clear()
        self.set_racing_mode()
        return self.wait_for_status("MODE_SET", "RACING", timeout=timeout)

    def set_valorant_mode_sync(self, timeout: float = 2.0) -> bool:
        """Send MODE,SET,VALORANT and await STATUS,VALORANT,MODE_SET."""
        self._status_event.clear()
        self.set_valorant_mode()
        return self.wait_for_status("MODE_SET", "VALORANT", timeout=timeout)

    def start_sync(self, timeout: float = 2.0) -> bool:
        """Send MODE,START and await STATUS,*,RUNNING."""
        self._status_event.clear()
        self.start()
        return self.wait_for_status("RUNNING", timeout=timeout)

    def stop_sync(self, timeout: float = 2.0) -> bool:
        """Send MODE,STOP and await STATUS,*,STOPPED."""
        self._status_event.clear()
        self.stop()
        return self.wait_for_status("STOPPED", timeout=timeout)

    def reset_sync(self, timeout: float = 2.0) -> bool:
        """Send MODE,RESET and await STATUS,NONE,IDLE."""
        self._status_event.clear()
        self.reset()
        return self.wait_for_status("IDLE", "NONE", timeout=timeout)

    # ── servo commands (Valorant) ───────────────────────────────

    def send_servo(self, ljx: int = 90, ljy: int = 90, rjx: int = 90,
                   rjy: int = 90, trigger: int = 0, duration: int = 200):
        """SERVO,LJX,LJY,RJX,RJY,TRIGGER,DURATION (servos 0-4)"""
        ljx = max(0, min(180, int(ljx)))
        ljy = max(0, min(180, int(ljy)))
        rjx = max(0, min(180, int(rjx)))
        rjy = max(0, min(180, int(rjy)))
        trigger = max(0, min(180, int(trigger)))
        duration = max(50, min(2000, int(duration)))
        self._send(f"SERVO,{ljx},{ljy},{rjx},{rjy},{trigger},{duration}")

    # ── race commands (Trackmania combined steering + paddles) ───

    def send_race(self, direction: str, rate_hz: int, left_paddle: int = 90, right_paddle: int = 90):
        """
        RACE,<LEFT|RIGHT>,<RATE_HZ>,<LEFT_PADDLE>,<RIGHT_PADDLE>
        Combined racing packet:
          - direction: 'LEFT' or 'RIGHT'
          - rate_hz: 10-2000
          - left_paddle: 0-180 (servo 5, brake; neutral 90)
          - right_paddle: 0-180 (servo 6, gas; neutral 90)
        """
        direction = direction.upper()
        if direction not in ("LEFT", "RIGHT"):
            direction = "LEFT"
        rate_hz = max(10, min(2000, int(rate_hz)))
        left_paddle = max(0, min(180, int(left_paddle)))
        right_paddle = max(0, min(180, int(right_paddle)))
        self._send(f"RACE,{direction},{rate_hz},{left_paddle},{right_paddle}")

    def race_stop(self):
        """RACE,STOP: Halts steering stepper and returns both paddles to 90 neutral."""
        self._send("RACE,STOP")

    # ── stepper commands (Racing steering jog/halt) ─────────────

    def steer_left(self, rate_hz: int = 400):
        """STEPPER,LEFT,<rate_hz>"""
        rate_hz = max(10, min(2000, int(rate_hz)))
        self._send(f"STEPPER,LEFT,{rate_hz}")

    def steer_right(self, rate_hz: int = 400):
        """STEPPER,RIGHT,<rate_hz>"""
        rate_hz = max(10, min(2000, int(rate_hz)))
        self._send(f"STEPPER,RIGHT,{rate_hz}")

    def steer_stop(self):
        """STEPPER,STOP: Halts wheel stepper without resetting paddles."""
        self._send("STEPPER,STOP")

    # ── internals ───────────────────────────────────────────────

    def _send(self, cmd: str):
        """Send a newline-terminated command to the real or virtual ESP32."""
        if self._is_virtual:
            self._handle_virtual_command(cmd)
            return

        with self._lock:
            if not self._ser or not self._ser.is_open:
                return
            try:
                self._ser.write((cmd + "\n").encode("ascii"))
            except serial.SerialException:
                self.disconnect()

    def _read_loop(self):
        """Background thread: continuously read lines from real ESP32."""
        while self._running:
            try:
                with self._lock:
                    if not self._ser or not self._ser.is_open:
                        break
                    raw = self._ser.readline()
                if not raw:
                    continue
                line = raw.decode("ascii", errors="ignore").strip()
                if not line:
                    continue
                self._dispatch(line)
            except serial.SerialException:
                self._running = False
                self.disconnect()
                break
            except Exception:
                continue

    def _virtual_reader_loop(self):
        """Background thread: dispatch mock responses from virtual ESP32 queue."""
        while self._running:
            try:
                msg = self._virt_queue.get(timeout=0.05)
                if msg:
                    self._dispatch(msg)
            except queue.Empty:
                continue
            except Exception:
                break

    def _handle_virtual_command(self, cmd: str):
        """Simulate real ESP32 firmware state machine & responses."""
        parts = cmd.strip().split(",")
        tag = parts[0] if parts else ""

        if tag == "MODE":
            sub = parts[1] if len(parts) > 1 else ""
            if sub == "SET" and len(parts) > 2:
                mode_name = parts[2]
                if self._virt_state == "RUNNING":
                    self._virt_queue.put("ERR,101,Cannot change mode while running")
                elif self._virt_state != "IDLE":
                    self._virt_queue.put("ERR,102,Invalid mode transition")
                elif mode_name not in ("VALORANT", "RACING"):
                    self._virt_queue.put("ERR,100,Invalid mode name")
                else:
                    self._virt_mode = mode_name
                    self._virt_state = "MODE_SET"
                    self._virt_queue.put(f"STATUS,{self._virt_mode},{self._virt_state}")
            elif sub == "START":
                if self._virt_state != "MODE_SET":
                    self._virt_queue.put("ERR,102,Invalid mode transition")
                else:
                    self._virt_state = "RUNNING"
                    self._virt_queue.put(f"STATUS,{self._virt_mode},{self._virt_state}")
            elif sub == "STOP":
                if self._virt_state != "RUNNING":
                    self._virt_queue.put("ERR,102,Cannot stop in current state")
                else:
                    self._virt_state = "STOPPED"
                    self._virt_queue.put(f"STATUS,{self._virt_mode},{self._virt_state}")
            elif sub == "RESET":
                if self._virt_state != "STOPPED":
                    self._virt_queue.put("ERR,102,Can only reset from STOPPED state")
                else:
                    self._virt_mode = "NONE"
                    self._virt_state = "IDLE"
                    self._virt_queue.put("STATUS,NONE,IDLE")
            elif sub == "STATUS":
                self._virt_queue.put(f"STATUS,{self._virt_mode},{self._virt_state}")
            else:
                self._virt_queue.put("ERR,300,Malformed MODE command")

        elif tag == "SERVO":
            if self._virt_state != "RUNNING":
                self._virt_queue.put("ERR,201,Mode not in RUNNING state")
            elif len(parts) < 6:
                self._virt_queue.put("ERR,202,Incomplete SERVO command")
            else:
                self._virt_queue.put("OK")

        elif tag == "RACE":
            if self._virt_mode != "RACING" or self._virt_state != "RUNNING":
                self._virt_queue.put("ERR,204,Racing command not allowed in current state")
            elif len(parts) == 2 and parts[1] == "STOP":
                self._virt_queue.put("OK")
            elif len(parts) == 5 and parts[1] in ("LEFT", "RIGHT"):
                try:
                    rate = int(parts[2])
                    lp = int(parts[3])
                    rp = int(parts[4])
                    if 10 <= rate <= 2000 and 0 <= lp <= 180 and 0 <= rp <= 180:
                        self._virt_queue.put("OK")
                    else:
                        self._virt_queue.put("ERR,300,Invalid RACE parameters")
                except ValueError:
                    self._virt_queue.put("ERR,300,Malformed RACE command")
            else:
                self._virt_queue.put("ERR,300,Malformed RACE command")

        elif tag == "STEPPER":
            sub = parts[1] if len(parts) > 1 else ""
            if sub == "STOP":
                # STEPPER,STOP is allowed even outside racing (per protocol)
                self._virt_queue.put("OK")
            elif sub in ("LEFT", "RIGHT"):
                if self._virt_mode != "RACING" or self._virt_state != "RUNNING":
                    self._virt_queue.put("ERR,204,Racing stepper not allowed in current state")
                else:
                    self._virt_queue.put("OK")
            else:
                self._virt_queue.put("ERR,300,Malformed STEPPER command")

        else:
            self._virt_queue.put("ERR,301,Unknown command type")

    def _dispatch(self, line: str):
        """Parse a response line and invoke the appropriate callback."""
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
            self._last_status = (mode, state)
            self._status_event.set()
            if self.on_status:
                self.on_status(mode, state)
