# Forensic Audit Report: Milestone 1

**Work Product**: Milestone 1 changes in `main.py` and `pacman/pacman_runner.py`  
**Profile**: General Project (Development Mode per `ORIGINAL_REQUEST.md`)  
**Verdict**: **CLEAN**  
**Date**: 2026-10-30T15:27:00Z  
**Auditor**: auditor_m1 (teamwork_auditor)  
**Parent Conversation ID**: e69ff21d-c68b-4dc5-8b54-914987353bcd  

---

## 1. Observation

### 1.1 Scope & Integrity Mode
- `ORIGINAL_REQUEST.md` line 7 explicitly defines `Integrity mode: development`.
- Under Development Mode, the forensic checks focus on verifying that implementation logic is authentic and prohibiting:
  1. Hardcoded test results / strings
  2. Facade implementations
  3. Fabricated verification outputs
  4. Self-certifying tests
  5. Production mock bypasses

### 1.2 Static Analysis & Codebase Inspection
- **Pre-populated Artifact Scan**:
  Command executed:
  ```powershell
  Get-ChildItem -Path . -Exclude .venv,.git -Recurse | Where-Object { $_.FullName -notmatch '\\\.venv\\' -and $_.FullName -notmatch '\\\.git\\' -and ($_.Name -match '\.log$' -or $_.Name -match 'result' -or $_.Name -match 'output') }
  ```
  Result: Zero matching files. No pre-populated logs or result artifacts exist in the repository.

- **Hardcoded String & Mock Scan in Production Code**:
  - `grep_search` for `"PASS"`, `"FAIL"`, `"assert"` in `main.py`: 0 matches.
  - `grep_search` for `"PASS"`, `"FAIL"`, `"assert"` in `pacman/pacman_runner.py`: 0 matches.
  - `grep_search` for `"mock"`, `"dummy"`, `"fake"` in `main.py` and `pacman/pacman_runner.py`: 0 matches.

- **Implementation in `main.py`**:
  - Lines 42–50: Genuine `tk.Menubutton` and attached `tk.Menu`:
    ```python
    self.btn_pacman_auto = tk.Menubutton(self.pacman_frame, text="Auto Mode ▾", width=17, height=1,
                                         relief=tk.RAISED)
    self.pacman_auto_menu = tk.Menu(self.btn_pacman_auto, tearoff=0)
    self.pacman_auto_menu.add_command(label="In-Computer Game", command=self.run_pacman_auto_in_computer)
    self.pacman_auto_menu.add_command(label="External Computer", command=self.run_pacman_auto_external)
    self.btn_pacman_auto["menu"] = self.pacman_auto_menu
    self.auto_menu = self.pacman_auto_menu
    self.btn_pacman_auto.pack(side=tk.RIGHT, padx=5, expand=True)
    ```
  - Lines 59–83: Genuine process management in `run_script`:
    ```python
    cmd = [sys.executable, script_path]
    if extra_args:
        cmd.extend(extra_args)
    proc = subprocess.Popen(cmd, cwd=folder_path)
    self.status_var.set(f"{script_name} is running in the background.")
    return proc
    ```
  - Lines 98–117: Dedicated launch dispatchers:
    - `run_pacman_auto_in_computer()` launches `pacman_game.py` with `["--auto"]` and `pacman_runner.py` with `["--capture-mode", "screen"]`, returning `(p_game, p_runner)`.
    - `run_pacman_auto_external()` launches `pacman_runner.py` with `["--capture-mode", "camera"]`, returning `p_runner`.
    - `run_pacman_auto(mode="in_computer")` provides backward-compatible routing.

- **Implementation in `pacman/pacman_runner.py`**:
  - Lines 638–654: Genuine `argparse.ArgumentParser` defining `--capture-mode` (`choices=["screen", "camera"]`, default `"camera"`) and `--camera` (`type=int`, default `0`).
  - Lines 75–83: `VisionEngine.open_camera()` bypasses camera hardware checks when `capture_mode == "screen"` by returning `True` immediately, while still opening `cv2.VideoCapture` when in camera mode.
  - Lines 90–116: `VisionEngine.grab_screen()` uses `pygetwindow.getWindowsWithTitle("Pac-Man")` to locate the target game window bounding box `(left, top, right, bottom)` if present and active, captures pixels using `PIL.ImageGrab.grab(bbox=bbox)`, converts RGBA/RGB/Grayscale to BGR 3-channel numpy array, and includes defensive exception handling returning `np.zeros((480, 640, 3), dtype=np.uint8)` on headless/OS grab failure.
  - Lines 302–384: `PacmanAutoPilotApp` receives `capture_mode` and `camera_index`, passes them to `VisionEngine`, and renders a visual `[SCREEN]` badge when in screen capture mode.

### 1.3 Behavioral & Empirical Verification Results
1. **Compilation Validation**:
   - Command: `.\.venv\Scripts\python.exe -m py_compile main.py pacman/pacman_runner.py`
   - Result: Exit code 0, cleanly compiled without warnings or syntax errors.

2. **Auditor Independent Forensic Verification Suite**:
   Executed 9 independent forensic checks verifying real objects and behavior:
   ```
   [PASS] Check 1: Tkinter Menubutton & Menu hierarchy - Labels match In-Computer Game and External Computer
   [PASS] Check 2: In-Computer Game command & args - Launches pacman_game.py [--auto] and pacman_runner.py [--capture-mode, screen]
   [PASS] Check 3: External Computer command & args - Launches pacman_runner.py [--capture-mode, camera]
   [PASS] Check 4: Backward-compatible run_pacman_auto delegation - Delegates mode=in_computer and mode=external cleanly
   [PASS] Check 5: Nonexistent script error handling - Returns None and displays error messagebox
   [PASS] Check 6: Live Popen execution of pacman_runner.py --help - Process completed with returncode 0
   [PASS] Check 7: CLI argument parsing - Defaults to camera:0, parses screen, parses custom camera index
   [PASS] Check 8: VisionEngine screen capture live grab - Grabbed frame shape: (480, 640, 3), dtype: uint8
   [PASS] Check 9: VisionEngine defensive fallback - Fails gracefully to (480, 640, 3) uint8 black frame on error
   ```

3. **Full Automated Discovery Test Suite Execution**:
   - Command: `.\.venv\Scripts\python.exe -m unittest discover -s tests -v`
   - Result: `Ran 58 tests in 1.580s; OK` (Exit code 0).
   - Covers:
     - `tests/test_launcher.py`: 5 tests
     - `tests/test_launcher_stress.py`: 19 tests
     - `tests/test_capture_stress.py`: 34 tests

---

## 2. Logic Chain

1. **Absence of Prohibited Artifacts**:
   - *Observation*: Ripgrep and filesystem queries yielded 0 instances of hardcoded "PASS"/"FAIL" strings in production code, 0 mock objects or dummy bypasses in production modules, and 0 pre-populated log or output files.
   - *Logic*: The codebase contains no pre-fabricated results or fake shortcuts designed to trick test runners.

2. **Authenticity of UI & Process Dispatch in `main.py`**:
   - *Observation*: `app.btn_pacman_auto` is an instantiated `tk.Menubutton`; `app.pacman_auto_menu` is an instantiated `tk.Menu` containing index 0 ("In-Computer Game") and index 1 ("External Computer").
   - *Observation*: `run_script` builds executable commands using `sys.executable` and `subprocess.Popen(cmd, cwd=folder_path)`, and returns the live `Popen` handle.
   - *Logic*: The launcher genuinely constructs the Tkinter submenu hierarchy required by R1 and genuinely spawns the respective child processes with exact arguments and directory contexts.

3. **Authenticity of Runner CLI & Screen Capture in `pacman/pacman_runner.py`**:
   - *Observation*: `parse_args` utilizes `argparse.ArgumentParser` to validate `--capture-mode` against `["screen", "camera"]` and parse `--camera` integers.
   - *Observation*: `VisionEngine.grab_screen()` uses `pygetwindow` for window location and `PIL.ImageGrab.grab` for live desktop frame capture, returning a 3-channel BGR numpy ndarray (`uint8`).
   - *Observation*: When `ImageGrab.grab` fails or raises an OS error, `grab_screen()` safely falls back to a blank 3-channel frame of dimensions `(480, 640, 3)` rather than crashing.
   - *Logic*: The runner implementation is genuine, functionally complete, and defensively engineered to operate robustly in both live desktop and headless/virtual environments.

4. **Adversarial Resilience**:
   - *Observation*: All 58 unit and adversarial stress tests across `test_launcher.py`, `test_capture_stress.py`, and `test_launcher_stress.py` execute and pass cleanly.
   - *Logic*: The solution withstands rigorous input variation, rapid repeated invocations, missing script handling, and headless fallback requirements.

---

## 3. Caveats

1. **Milestone 2 Separation**:
   Ghost AI house exit and corridor pursuit (`pacman/pacman_game.py`) was not modified in Milestone 1 and is scoped exclusively to Milestone 2.
2. **Serial Hardware Dependency**:
   Autopilot commands to the ESP32 actuator controller require physical COM port hardware for live servo movement. In the absence of an ESP32 device, the runner operates in disconnected CV vision mode without errors.

---

## 4. Conclusion

**Verdict: CLEAN**

Milestone 1 satisfies all integrity criteria and functional specifications:
- Zero prohibited patterns detected (no hardcoding, no facades, no pre-populated outputs, no mock bypasses).
- `main.py` authentically implements the Auto Mode `tk.Menubutton` and `tk.Menu` with "In-Computer Game" and "External Computer" actions, correctly launching processes via `subprocess.Popen` and returning process handles.
- `pacman/pacman_runner.py` authentically implements CLI parsing and screen capture with resilient fallback.
- The work product is approved without integrity violations.

---

## 5. Verification Method

To independently reproduce and verify this audit:

1. **Compilation Check**:
   ```powershell
   .\.venv\Scripts\python.exe -m py_compile main.py pacman/pacman_runner.py
   ```
   *Expected result*: Exit code 0, no output.

2. **Automated Discovery Test Suite**:
   ```powershell
   .\.venv\Scripts\python.exe -m unittest discover -s tests -v
   ```
   *Expected result*: `Ran 58 tests in ~1.5s; OK` (Exit code 0).

3. **Submenu & Capture Integration Check**:
   ```powershell
   .\.venv\Scripts\python.exe -c "import tkinter as tk; from main import AILauncher; import pacman.pacman_runner as runner; root = tk.Tk(); root.withdraw(); app = AILauncher(root); assert app.pacman_auto_menu.entrycget(0, 'label') == 'In-Computer Game'; assert app.pacman_auto_menu.entrycget(1, 'label') == 'External Computer'; root.destroy(); args = runner.parse_args(['--capture-mode', 'screen']); assert args.capture_mode == 'screen'; engine = runner.VisionEngine(capture_mode='screen'); assert engine.open_camera(); f = engine.grab_screen(); assert f is not None and len(f.shape) == 3; print('Independent Verification PASS')"
   ```
   *Expected result*: `Independent Verification PASS`.

4. **Invalidation Conditions**:
   - Any commit introducing hardcoded test result strings or dummy return values in `main.py` or `pacman/pacman_runner.py`.
   - Failure of `app.pacman_auto_menu` to provide the specified R1 menu labels.
   - Failure of `pacman_runner.py` to parse `--capture-mode screen` or handle headless capture.
