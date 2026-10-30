# Milestone 1 Review & Adversarial Stress Report

**Reviewer**: reviewer_m1_2 (teamwork_reviewer & critic)  
**Date**: 2026-10-30T15:27:00Z  
**Parent Conversation ID**: e69ff21d-c68b-4dc5-8b54-914987353bcd  
**Target Files**: `main.py`, `pacman/pacman_runner.py`  
**Verdict**: **APPROVE**  
**Integrity Status**: **CLEAN (Zero Integrity Violations)**

---

## 1. Observation

### 1.1 Direct Codebase Observations

#### 1.1.1 `pacman/pacman_runner.py` CLI Argument Parsing
In `pacman/pacman_runner.py` (lines 638–654):
```python
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
```
- Accepts explicit `args` list for unit testing or defaults to `sys.argv[1:]`.
- Supports both `--capture-mode` and alias `--capture_mode` with choices `["screen", "camera"]` and default `"camera"`.
- Supports `--camera` with integer type casting and default `0`.

#### 1.1.2 `pacman/pacman_runner.py` Camera Bypass in Screen Mode
In `pacman/pacman_runner.py` (lines 75–84):
```python
    def open_camera(self, index: int = 0) -> bool:
        if self.capture_mode == "screen":
            return True
        self.close_camera()
        self.cap = cv2.VideoCapture(index)
        if not self.cap.isOpened():
            self.cap = None
            return False
        return True
```
- When `self.capture_mode == "screen"`, `open_camera()` bypasses hardware camera initialization, returning `True` immediately without allocating `cv2.VideoCapture` or requiring a USB webcam.

#### 1.1.3 `pacman/pacman_runner.py` Screen Capture & Fallback
In `pacman/pacman_runner.py` (lines 90–116):
```python
    def grab_screen(self):
        """Capture local window or screen, returning BGR numpy array with safe fallback on error."""
        try:
            bbox = None
            if pygetwindow is not None:
                windows = pygetwindow.getWindowsWithTitle("Pac-Man")
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
```
- Locates window title containing `"Pac-Man"`. Window title in `pacman_game.py` line 355 is `"Pac-Man [MANUAL MODE]"` or `"Pac-Man [AUTONOMOUS READY]"`, which correctly matches.
- Bounding box extraction safely verifies `win.width > 0 and win.height > 0 and not getattr(win, "isMinimized", False)`.
- If window is missing, minimized, or `pygetwindow is None`, `bbox` defaults to `None` (full screen grab).
- Any exception in `ImageGrab.grab()` or OS screen grab failsafe returns a clean BGR numpy array `np.zeros((480, 640, 3), dtype=np.uint8)`.
- Frame color formats (RGBA, RGB, Gray) are uniformly converted to 3-channel BGR numpy arrays matching OpenCV expectations.

#### 1.1.4 `main.py` Menu Structure & Geometry Preservation
In `main.py` (lines 11, 42–49):
```python
        self.root.geometry("400x370")
...
        self.btn_pacman_auto = tk.Menubutton(self.pacman_frame, text="Auto Mode ▾", width=17, height=1,
                                             relief=tk.RAISED)
        self.pacman_auto_menu = tk.Menu(self.btn_pacman_auto, tearoff=0)
        self.pacman_auto_menu.add_command(label="In-Computer Game", command=self.run_pacman_auto_in_computer)
        self.pacman_auto_menu.add_command(label="External Computer", command=self.run_pacman_auto_external)
        self.btn_pacman_auto["menu"] = self.pacman_auto_menu
        self.auto_menu = self.pacman_auto_menu
        self.btn_pacman_auto.pack(side=tk.RIGHT, padx=5, expand=True)
```
- Existing geometry `400x370` is preserved.
- `btn_pacman_auto` uses `tk.Menubutton` with native dropdown menu.
- `pacman_auto_menu` and backwards-compatible alias `auto_menu` expose "In-Computer Game" and "External Computer".

#### 1.1.5 `main.py` Process Invocations & Working Directories
In `main.py` (lines 57–78 & 93–110):
```python
        cmd = [sys.executable, script_path]
        if extra_args:
            cmd.extend(extra_args)
        proc = subprocess.Popen(cmd, cwd=folder_path)
...
    def run_pacman_auto_in_computer(self):
        p_game = self.run_script("pacman_game.py", self.pacman_dir, ["--auto"])
        p_runner = self.run_script("pacman_runner.py", self.pacman_dir, ["--capture-mode", "screen"])
        self.status_var.set("Pac-Man Game & Runner (In-Computer) launched.")
        return (p_game, p_runner)

    def run_pacman_auto_external(self):
        p_runner = self.run_script("pacman_runner.py", self.pacman_dir, ["--capture-mode", "camera"])
        self.status_var.set("Pac-Man Runner (External Camera) launched.")
        return p_runner
```
- `cmd` is constructed as a list with `sys.executable` and `script_path` (`os.path.join(folder_path, script_name)`), correctly preserving arguments even on Windows paths with spaces.
- `cwd=folder_path` (`self.pacman_dir`) is explicitly passed.
- `run_pacman_auto_in_computer()` returns `(p_game, p_runner)` tuple.
- `run_pacman_auto_external()` returns `p_runner`.
- `run_pacman_auto(mode="in_computer")` provides backward compatibility.

### 1.2 Tool Execution Results

1. **Syntax & Compilation Verification**:
   ```powershell
   .\.venv\Scripts\python.exe -m py_compile main.py pacman/pacman_runner.py
   ```
   *Result*: Exit code 0, clean compilation.

2. **Automated Stress Test Suite Execution**:
   ```powershell
   .\.venv\Scripts\python.exe -m unittest discover -s tests -v
   ```
   *Result*: 45 tests ran across `test_capture_stress.py` and `test_launcher_stress.py`:
   - 11 CLI parsing stress tests (choices, defaults, non-int values, uppercase, missing args): **PASS**
   - 3 Camera open behavior tests (camera vs screen bypass, missing device): **PASS**
   - 5 Color conversion tests (RGB, RGBA, L to 3-channel BGR): **PASS**
   - 7 Screen capture fallback tests (headless OSError, None pygetwindow, minimized window): **PASS**
   - 5 Launcher menu tests (entry count, invoke 0, invoke 1, negative index): **PASS**
   - 3 Launcher R1 compliance tests (Popen args, python executable, cwd): **PASS**
   - 3 Rapid sequential stress tests (50x external, 50x in-computer, 50x alternating): **PASS**
   - 2 Live process spawning tests (real pacman_runner --help, process termination): **PASS**
   - 6 Edge cases tests (spaces in paths, missing script, non-string args, OSError): **PASS**
   *Total*: `Ran 45 tests in 1.184s; OK`.

---

## 2. Logic Chain

1. **R1 Submenu Contract Fulfillment**:
   - *Observation*: R1 requires Auto Mode to present "In-Computer Game" and "External Computer".
   - *Evidence*: `main.py` lines 42–49 instantiate a `Menubutton` displaying `"Auto Mode ▾"` containing both options with exact strings.
   - *Inference*: The menu structure is complete, conforms to Tkinter conventions, preserves the 400x370 layout, and provides backwards compatibility through `self.auto_menu`.

2. **Process Management Contract Fulfillment**:
   - *Observation*: Selecting "In-Computer Game" must launch `pacman_game.py --auto` and `pacman_runner.py --capture-mode screen`. Selecting "External Computer" must launch `pacman_runner.py --capture-mode camera`.
   - *Evidence*: `run_pacman_auto_in_computer` invokes both scripts with `extra_args` and returns `(p_game, p_runner)`. `run_pacman_auto_external` invokes the runner with `["--capture-mode", "camera"]` and returns `p_runner`.
   - *Evidence*: `run_script` passes `cwd=folder_path` (`self.pacman_dir`) and uses `sys.executable`. List formatting prevents whitespace quoting issues on Windows.
   - *Inference*: Process spawning meets all interface specifications outlined in `PROJECT.md`.

3. **Screen Grab Robustness & Headless Safety**:
   - *Observation*: In CI or headless test environments without real monitors or when Pac-Man window is not running, `ImageGrab.grab()` or `getWindowsWithTitle` could crash.
   - *Evidence*: `VisionEngine.grab_screen()` wraps window detection and screen grab in a `try ... except Exception:` block that returns `np.zeros((480, 640, 3), dtype=np.uint8)`.
   - *Evidence*: Downstream `_analyze()` accepts this 3-channel black frame, successfully executes HSV thresholding, Canny edge detection, and density calculations, producing valid joystick actions without crashing.
   - *Inference*: Autopilot execution will not crash under unexpected capture failures.

4. **Hardware Decoupling in Screen Capture Mode**:
   - *Observation*: Autonomous in-computer play should not fail when run on a laptop/desktop without an attached USB webcam.
   - *Evidence*: `VisionEngine.open_camera()` immediately returns `True` when `self.capture_mode == "screen"`, leaving `self.cap = None`. The capture thread `_loop()` routes directly to `self.grab_screen()`.
   - *Inference*: Software testing and in-computer gameplay are fully decoupled from webcam hardware.

5. **Integrity Verification**:
   - *Observation*: Reviewer adversarial inspection for hardcoded test responses, dummy mocks in source code, or shortcuts.
   - *Evidence*: All methods in `main.py` and `pacman/pacman_runner.py` contain actual functional logic; no test-specific conditionals or mocked returns exist in production files.
   - *Inference*: Zero integrity violations detected.

---

## 3. Caveats

1. **Multiple Process Spawning on Repeated Clicks**:
   If a user clicks "In-Computer Game" or "External Computer" multiple times rapidly in the GUI, multiple instances of the game or runner will be spawned simultaneously. This is standard Tkinter launcher behavior and does not violate requirements, but operators should avoid spamming menu options.
2. **Window Occlusion During Live In-Computer CV Autopilot**:
   In live in-computer play on a single monitor, if the Pac-Man window is obscured or placed off-screen, CV frame capture will see the overlapping window. Users should tile windows side-by-side.
3. **Milestone 2 Scope Boundary**:
   Milestone 1 only covers the launcher submenu and runner capture abstraction. Ghost AI pen exit logic in `pacman/pacman_game.py` is Milestone 2 scope and was intentionally not modified in this milestone.

---

## 4. Conclusion

**Verdict: APPROVE**

The implementation of Milestone 1 in `main.py` and `pacman/pacman_runner.py`:
- Fully implements Requirement R1 and Milestone 1 features from `PROJECT.md`.
- Conforms to interface contracts for CLI args (`--capture-mode`, `--camera`), process execution commands, and return types.
- Correctly handles camera bypass in screen mode and defensive fallback on missing windows or headless OS capture errors.
- Passed 45 adversarial stress tests without failures.
- No integrity violations found.

---

## 5. Verification Method

To independently reproduce and verify this assessment:

1. **Run Compilation**:
   ```powershell
   .\.venv\Scripts\python.exe -m py_compile main.py pacman/pacman_runner.py
   ```
   *Expected outcome*: Exit code 0, no output.

2. **Run Full Test Suite**:
   ```powershell
   .\.venv\Scripts\python.exe -m unittest discover -s tests -v
   ```
   *Expected outcome*: All 45 tests pass with `OK`.

3. **Verify Headless Capture & Fallback**:
   ```powershell
   .\.venv\Scripts\python.exe -c "import pacman.pacman_runner as runner; v = runner.VisionEngine(capture_mode='screen'); assert v.open_camera(); f = v.grab_screen(); assert f.shape == (480, 640, 3); a, s, d, dbg = v._analyze(f); assert len(s) == 5; print('Verification PASS')"
   ```
   *Expected outcome*: Outputs `Verification PASS`.

4. **Verify Launcher Menu & Process Invocation**:
   ```powershell
   .\.venv\Scripts\python.exe -c "import tkinter as tk; from unittest.mock import patch, MagicMock; from main import AILauncher; root = tk.Tk(); root.withdraw(); app = AILauncher(root); assert app.pacman_auto_menu.entrycget(0, 'label') == 'In-Computer Game'; assert app.pacman_auto_menu.entrycget(1, 'label') == 'External Computer'; root.destroy(); print('Launcher PASS')"
   ```
   *Expected outcome*: Outputs `Launcher PASS`.

5. **Invalidation Conditions**:
   - `parse_args` fails to reject invalid `--capture-mode` choices.
   - `VisionEngine.open_camera()` fails when no webcam is connected under `capture_mode="screen"`.
   - `main.py` fails to return `Popen` handles or spawns processes in wrong directories.
