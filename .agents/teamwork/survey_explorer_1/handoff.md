# Handoff Report: Launcher Control Center & Pac-Man Configuration Survey

**Date**: 2026-10-30T15:08:00Z  
**Author**: survey_explorer_1 (teamwork_explorer)  
**Parent Conversation ID**: e69ff21d-c68b-4dc5-8b54-914987353bcd  
**Scope**: Requirement R1 (Launcher Auto Mode Submenu Selection), Launcher Control Center Architecture (`main.py`), and Pac-Man Game & Runner Integration (`pacman/pacman_runner.py`, `pacman/pacman_game.py`).

---

## 1. Observation

### 1.1 `main.py` Architecture & Existing Pac-Man Launcher
Inspection of `main.py` (lines 7–94) revealed:
- **Application Class**: `AILauncher` using `tkinter`.
  - Window geometry: `self.root.geometry("400x370")` (line 11).
  - Directory anchors:
    ```python
    self.base_dir = os.path.dirname(os.path.abspath(__file__))
    self.mapper_dir = os.path.join(self.base_dir, "mapper")
    self.racing_dir = os.path.join(self.base_dir, "racing")
    self.pacman_dir = os.path.join(self.base_dir, "pacman")
    ```
- **PAC-MAN UI Section** (lines 34–44):
  ```python
  # Pac-Man Submenu Frame
  self.pacman_frame = tk.LabelFrame(root, text="PAC-MAN", font=("Arial", 10, "bold"), padx=10, pady=8)
  self.pacman_frame.pack(pady=10, fill="x")

  self.btn_pacman_manual = tk.Button(self.pacman_frame, text="Manual Mode (Play)", width=15, height=1,
                                     command=self.run_pacman_manual)
  self.btn_pacman_manual.pack(side=tk.LEFT, padx=5, expand=True)

  self.btn_pacman_auto = tk.Button(self.pacman_frame, text="Auto Mode (Autopilot)", width=17, height=1,
                                   command=self.run_pacman_auto)
  self.btn_pacman_auto.pack(side=tk.RIGHT, padx=5, expand=True)
  ```
- **Script Execution Helper** (lines 52–72):
  ```python
  def run_script(self, script_name, folder_path, extra_args=None):
      """ Executes the script from the specified folder using the active virtual environment """
      script_path = os.path.join(folder_path, script_name)
      if not os.path.exists(script_path):
          messagebox.showerror("Error", f"File not found:\n{script_path}\n\nMake sure the file exists.")
          return
      self.status_var.set(f"Launching {script_name}...")
      self.root.update()
      try:
          cmd = [sys.executable, script_path]
          if extra_args:
              cmd.extend(extra_args)
          subprocess.Popen(cmd, cwd=folder_path)
          self.status_var.set(f"{script_name} is running in the background.")
      except Exception as e:
          messagebox.showerror("Execution Error", str(e))
          self.status_var.set("Ready")
  ```
  *Key Observations*:
  - `run_script` already accepts `extra_args=None` and appends them to `cmd`.
  - `run_script` does NOT return the `subprocess.Popen` handle, discarding process references.
- **Current Pac-Man Launch Handlers** (lines 81–87):
  ```python
  def run_pacman_manual(self):
      # Launch Pac-Man local game for manual playing
      self.run_script("pacman_game.py", self.pacman_dir)

  def run_pacman_auto(self):
      # Route to pacman/pacman_runner.py (Full CV & ESP32 Auto-Pilot GUI)
      self.run_script("pacman_runner.py", self.pacman_dir)
  ```
  There is currently no submenu or prompt for Auto Mode; clicking `btn_pacman_auto` immediately spawns `pacman_runner.py` with no arguments.

### 1.2 `pacman/pacman_game.py` Execution & Argument Support
Inspection of `pacman/pacman_game.py` (lines 351–478) revealed:
- **CLI Argument Support** (lines 473–478):
  ```python
  if __name__ == "__main__":
      is_manual = True
      if len(sys.argv) > 1 and sys.argv[1].lower() == "--auto":
          is_manual = False
      run_pacman(manual_mode=is_manual)
  ```
- **Autonomous Mode Flag** (`manual_mode=False`):
  - Sets window caption: `title = "Pac-Man [MANUAL MODE]" if manual_mode else "Pac-Man [AUTONOMOUS READY]"` (line 355).
  - Skips manual arrow / WASD keyboard inputs in event loop: `elif manual_mode:` at line 397 protects lines 398–405.
- **Window Specs**: Window size is 672x794 pixels (`SCREEN_WIDTH = COLS * CELL_SIZE = 28 * 24 = 672`, `SCREEN_HEIGHT = ROWS * CELL_SIZE + 50 = 744 + 50 = 794`).

### 1.3 `pacman/pacman_runner.py` VisionEngine & Capture Capabilities
Inspection of `pacman/pacman_runner.py` revealed:
- **Entry Point** (lines 592–597):
  ```python
  if __name__ == "__main__":
      root = tk.Tk()
      app = PacmanAutoPilotApp(root)
      root.protocol("WM_DELETE_WINDOW", lambda: (app._stop_autopilot(), app.ctrl.disconnect(), root.destroy()))
      root.mainloop()
  ```
  *Key Observation*: Accepts **zero** command-line arguments or flags; neither `sys.argv` nor `argparse` is implemented.
- **Capture Implementation** (`VisionEngine`, lines 69–81, 99–110):
  - Only supports camera capture via `cv2.VideoCapture(index)`:
    ```python
    def open_camera(self, index: int = 0) -> bool:
        self.close_camera()
        self.cap = cv2.VideoCapture(index)
        if not self.cap.isOpened():
            self.cap = None
            return False
        return True
    ```
  - `PacmanAutoPilotApp` provides a camera spinbox `cam_spin` (0 to 5) linked to `self.cam_var`.
  - There is currently **no local screen or window capture capability** implemented in `VisionEngine`.

### 1.4 Environment & Dependencies Verification
Tool tests executed in `.venv`:
- `PIL.ImageGrab` is available from `Pillow>=10.0`.
- `pygetwindow` is available (installed transitively via `PyAutoGUI`).
- Running `ImageGrab.grab()` in a headless/non-interactive shell produced:
  `OSError: screen grab failed` at `PIL\ImageGrab.py:99`.
  *Key Observation*: Screen capture must contain defensive error handling/fallbacks to avoid crashing in test or headless environments.
- Python standard `unittest` (`python -m unittest discover`) is present and functional.

---

## 2. Logic Chain

1. **Submenu Requirement in `main.py` (R1)**:
   - *Observation*: `ORIGINAL_REQUEST.md` R1 specifies: "Under the PAC-MAN section in `main.py`, the Auto Mode option must present two choices: 'In-Computer Game' and 'External Computer'".
   - *Observation*: `main.py` currently has a simple `tk.Button` for `btn_pacman_auto` that triggers `run_pacman_auto`.
   - *Reasoning*: To present two choices cleanly without breaking the existing UI layout or altering the `400x370` window geometry:
     - Option A: Convert `btn_pacman_auto` to a `tk.Menubutton` with a dropdown `tk.Menu` containing "In-Computer Game" and "External Computer".
     - Option B: Maintain `btn_pacman_auto` as a `tk.Button` with a popup menu (`tk.Menu.tk_popup`) triggered on click.
     - Option C: Add a modal dialog or secondary sub-buttons.
     - `tk.Menubutton` is the standard, native Tkinter pattern for in-button submenus. When clicked, it displays the two required choices.
   - *Reasoning*: For backward compatibility and testability, `AILauncher` must expose explicit methods:
     - `run_pacman_auto_in_computer()`
     - `run_pacman_auto_external()`
     - `run_pacman_auto(mode=...)` delegating appropriately.

2. **Process Execution for "In-Computer Game"**:
   - *Observation*: Requirement R1 states: "Selecting 'In-Computer Game' must launch the local game (`pacman/pacman_game.py`) alongside the GUI runner (`pacman/pacman_runner.py`), with the runner configured to capture the local game screen or window."
   - *Observation*: `run_script` uses non-blocking `subprocess.Popen`.
   - *Reasoning*: In `run_pacman_auto_in_computer()`, `main.py` should call:
     1. `self.run_script("pacman_game.py", self.pacman_dir, ["--auto"])`
     2. `self.run_script("pacman_runner.py", self.pacman_dir, ["--capture-mode", "screen"])`
   - *Reasoning*: Returning the `Popen` handle from `run_script` allows `AILauncher` to return both handles `(p_game, p_runner)` to facilitate verification tests and lifecycle tracking.

3. **Process Execution for "External Computer"**:
   - *Observation*: Requirement R1 states: "Selecting 'External Computer' must launch the GUI runner (`pacman/pacman_runner.py`) configured for external computer capture (e.g., via USB camera)."
   - *Reasoning*: In `run_pacman_auto_external()`, `main.py` must launch ONLY:
     `self.run_script("pacman_runner.py", self.pacman_dir, ["--capture-mode", "camera"])`.
     It must NOT launch `pacman_game.py`.

4. **Runner Configuration & Capture Integration**:
   - *Observation*: `pacman_runner.py` does not currently parse arguments or support screen capture.
   - *Reasoning*: To fulfill R1, `pacman_runner.py` needs:
     - CLI parsing (`argparse` or `sys.argv`) for `--capture-mode` (values: `'screen'`, `'camera'`, aliased to `'local'`, `'external'`) and `--camera` (index).
     - `VisionEngine` capture abstraction:
       - If mode is `'camera'`: use `cv2.VideoCapture(index)` (existing).
       - If mode is `'screen'`: capture the local display window using `pygetwindow.getWindowsWithTitle("Pac-Man")` with `PIL.ImageGrab.grab(bbox=...)` (or full screen fallback).
       - If `ImageGrab.grab()` fails with `OSError` (e.g. headless CI), catch the exception, generate a synthetic/blank BGR frame, and log a warning instead of crashing.
     - `PacmanAutoPilotApp` GUI updates: reflect the active capture mode in the connection panel.

---

## 3. Caveats

1. **Headless Execution Environment**:
   - As observed in tool testing, `PIL.ImageGrab.grab()` raises `OSError: screen grab failed` when executed in Windows services, virtual environments, or headless sessions without an interactive desktop surface.
   - The implementer of `pacman_runner.py` screen capture must include try/except wrapping with mockable fallback to allow tests to run headlessly.
2. **Pygame Window Title Synchronization**:
   - In `pacman_game.py`, the window title is `"Pac-Man [AUTONOMOUS READY]"` when `--auto` is given, and `"Pac-Man [MANUAL MODE]"` when run manually. The window search in `pacman_runner.py` should search for `"Pac-Man"` substring to match either title.
3. **Ghost House Exit (R2)**:
   - Requirement R2 pertains to ghost AI navigation inside `pacman/pacman_game.py`. This investigation focused specifically on Requirement R1 (Launcher Control Center architecture and configuration). Ghost AI behavior is surveyed in parallel by `survey_explorer_2`.
4. **Input Control in In-Computer Auto Mode**:
   - `pacman_runner.py` currently commands an ESP32 hardware actuator over serial. In pure local in-computer execution, actual joystick actuation requires the ESP32 hardware or software key emulation (`pyautogui`). However, Requirement R1 specifically defines the scope as launcher configuration and runner capture configuration.

---

## 4. Conclusion

### Summary of System Changes for Requirement R1

| Component | Target File | Line(s) | Required Change |
|---|---|---|---|
| **Auto Mode Submenu** | `main.py` | 42–44 | Replace standard Button with `tk.Menubutton` displaying "Auto Mode ▾", attached to a `tk.Menu` with options: `"In-Computer Game"` and `"External Computer"`. |
| **Launch Handlers** | `main.py` | 85–87 | Implement `run_pacman_auto_in_computer()` and `run_pacman_auto_external()`. Update `run_pacman_auto()` for backward compatibility. |
| **Process Tracking** | `main.py` | 52–72 | Modify `run_script` to return `subprocess.Popen` (or `None` on error) to enable automated testing and process lifecycle management. |
| **CLI Argument Parsing** | `pacman/pacman_runner.py` | 592–597 | Add `argparse` support for `--capture-mode` (`screen` vs `camera`) and `--camera` index. |
| **Local Screen Capture** | `pacman/pacman_runner.py` | 41–133 | Extend `VisionEngine` to support `capture_mode="screen"` using `pygetwindow` + `PIL.ImageGrab.grab()`, converting RGB PIL image to BGR numpy array. |
| **Defensive Fallback** | `pacman/pacman_runner.py` | 99–133 | Wrap screen grab in `try/except OSError` returning blank/test frame for headless test environments. |

### Concrete Implementation Blueprint for `main.py`

```python
# 1. Update PAC-MAN section in __init__:
self.pacman_frame = tk.LabelFrame(root, text="PAC-MAN", font=("Arial", 10, "bold"), padx=10, pady=8)
self.pacman_frame.pack(pady=10, fill="x")

self.btn_pacman_manual = tk.Button(self.pacman_frame, text="Manual Mode (Play)", width=15, height=1,
                                   command=self.run_pacman_manual)
self.btn_pacman_manual.pack(side=tk.LEFT, padx=5, expand=True)

# Menubutton providing Auto Mode submenu
self.btn_pacman_auto = tk.Menubutton(self.pacman_frame, text="Auto Mode ▾", width=17, height=1,
                                     relief=tk.RAISED, font=("Arial", 9))
self.auto_menu = tk.Menu(self.btn_pacman_auto, tearoff=0)
self.auto_menu.add_command(label="In-Computer Game", command=self.run_pacman_auto_in_computer)
self.auto_menu.add_command(label="External Computer", command=self.run_pacman_auto_external)
self.btn_pacman_auto["menu"] = self.auto_menu
self.btn_pacman_auto.pack(side=tk.RIGHT, padx=5, expand=True)

# 2. Update run_script to return proc:
def run_script(self, script_name, folder_path, extra_args=None):
    ...
    proc = subprocess.Popen(cmd, cwd=folder_path)
    self.status_var.set(f"{script_name} is running in the background.")
    return proc

# 3. Add explicit handler methods:
def run_pacman_auto_in_computer(self):
    """Launch local game and runner configured for local screen/window capture."""
    p_game = self.run_script("pacman_game.py", self.pacman_dir, ["--auto"])
    p_runner = self.run_script("pacman_runner.py", self.pacman_dir, ["--capture-mode", "screen"])
    self.status_var.set("Pac-Man Game & Runner (In-Computer) launched.")
    return (p_game, p_runner)

def run_pacman_auto_external(self):
    """Launch runner configured for external computer camera capture."""
    p_runner = self.run_script("pacman_runner.py", self.pacman_dir, ["--capture-mode", "camera"])
    self.status_var.set("Pac-Man Runner (External Camera) launched.")
    return p_runner

def run_pacman_auto(self, mode="in_computer"):
    """Backward-compatible Auto Mode invocation."""
    if mode == "external":
        return self.run_pacman_auto_external()
    return self.run_pacman_auto_in_computer()
```

---

## 5. Verification Method

### 5.1 Verification Commands
To verify the implementation once applied:

1. **Syntax and Import Validation**:
   ```powershell
   .\.venv\Scripts\python.exe -m py_compile main.py pacman/pacman_runner.py pacman/pacman_game.py
   ```

2. **Automated Unit Testing** (Requirement R3):
   Run automated test suite:
   ```powershell
   .\.venv\Scripts\python.exe -m unittest discover tests -p "test_*.py" -v
   ```

### 5.2 Test Blueprint for Submenu Verification (`tests/test_launcher_menu.py`)
```python
import unittest
from unittest.mock import patch, MagicMock
import tkinter as tk
from main import AILauncher

class TestLauncherMenu(unittest.TestCase):
    def setUp(self):
        self.root = tk.Tk()
        self.app = AILauncher(self.root)

    def tearDown(self):
        self.root.destroy()

    @patch("subprocess.Popen")
    def test_in_computer_game_launches_both(self, mock_popen):
        mock_popen.return_value = MagicMock()
        # Invoke In-Computer Game submenu entry (index 0)
        self.app.auto_menu.invoke(0)
        
        self.assertEqual(mock_popen.call_count, 2)
        # Check first call: pacman_game.py with --auto
        first_call_args = mock_popen.call_args_list[0][0][0]
        self.assertTrue(any("pacman_game.py" in str(a) for a in first_call_args))
        self.assertIn("--auto", first_call_args)

        # Check second call: pacman_runner.py with screen capture
        second_call_args = mock_popen.call_args_list[1][0][0]
        self.assertTrue(any("pacman_runner.py" in str(a) for a in second_call_args))
        self.assertIn("--capture-mode", second_call_args)
        self.assertIn("screen", second_call_args)

    @patch("subprocess.Popen")
    def test_external_computer_launches_runner_only(self, mock_popen):
        mock_popen.return_value = MagicMock()
        # Invoke External Computer submenu entry (index 1)
        self.app.auto_menu.invoke(1)
        
        self.assertEqual(mock_popen.call_count, 1)
        call_args = mock_popen.call_args_list[0][0][0]
        self.assertTrue(any("pacman_runner.py" in str(a) for a in call_args))
        self.assertIn("--capture-mode", call_args)
        self.assertIn("camera", call_args)
```

### 5.3 Invalidation Conditions
This survey is invalidated if:
- `main.py` UI transitions away from Tkinter to a different framework (e.g. Qt or Web-based UI).
- Requirements change to require hardware ESP32 connection validation before allowing Auto Mode selection.
- `pacman_runner.py` is restructured into separate standalone scripts for screen vs camera capture rather than parameterized CLI modes.
