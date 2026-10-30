## 2026-10-30T15:10:41Z
You are worker_m1 (teamwork_worker).
Your working directory is: c:\Users\joash\OneDrive\Documents\Github\PathFinder\.agents\teamwork\worker_m1
Your parent conversation ID is: e69ff21d-c68b-4dc5-8b54-914987353bcd

MANDATORY FIRST STEP:
Read c:\Users\joash\OneDrive\Documents\Github\PathFinder\.agents\teamwork\ORIGINAL_REQUEST.md before doing any work.
Also read c:\Users\joash\OneDrive\Documents\Github\PathFinder\PROJECT.md and c:\Users\joash\OneDrive\Documents\Github\PathFinder\.agents\teamwork\survey_explorer_1\handoff.md.

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

WRITE OWNERSHIP:
You exclusively own and may edit:
- `main.py`
- `pacman/pacman_runner.py`
Do NOT edit `pacman/pacman_game.py` (owned by Milestone 2) or test files yet.

YOUR MISSION (Milestone 1: Launcher Submenu & Runner Capture):
1. In `main.py`:
   - Replace the single `btn_pacman_auto` button with an accessible Auto Mode submenu: use a `tk.Menubutton` displaying "Auto Mode ▾" linked to a `tk.Menu` (stored as `self.pacman_auto_menu` or `self.auto_menu`) presenting two clear choices:
     - "In-Computer Game"
     - "External Computer"
   - Implement handler methods on `AILauncher`:
     - `run_pacman_auto_in_computer(self)`: Launches local game `pacman_game.py` with `["--auto"]` and runner `pacman_runner.py` with `["--capture-mode", "screen"]`. Returns tuple of `(p_game, p_runner)`.
     - `run_pacman_auto_external(self)`: Launches runner `pacman_runner.py` with `["--capture-mode", "camera"]`. Returns `p_runner`.
     - `run_pacman_auto(self, mode="in_computer")`: Backward-compatible delegation.
   - Update `run_script` to return the `subprocess.Popen` handle (or None on error).
2. In `pacman/pacman_runner.py`:
   - Add CLI argument parsing for `--capture-mode` (accepting `'screen'` / `'camera'`, default `'camera'`) and `--camera` (integer index, default 0).
   - In `VisionEngine`, add support for local window/screen capture when `capture_mode == 'screen'`:
     - Use `pygetwindow.getWindowsWithTitle("Pac-Man")` to locate the local game window if available, or fall back to full screen.
     - Capture via `PIL.ImageGrab.grab(bbox=...)` and convert from RGB to BGR numpy array (`cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)`).
     - Protect screen grabbing with `try ... except Exception as e` returning a valid blank/black frame if grabbing fails (e.g., in headless/CI environments) so it never crashes.
   - Pass the parsed `--capture-mode` to `PacmanAutoPilotApp` and `VisionEngine`.
3. Verify your implementation:
   - Check compilation with `.venv\Scripts\python.exe -m py_compile main.py pacman/pacman_runner.py`.
   - Run a headless check of `main.py` and menu callbacks.

Write your complete handoff report in:
`c:\Users\joash\OneDrive\Documents\Github\PathFinder\.agents\teamwork\worker_m1\handoff.md`
Update your `progress.md` in your working directory.
When done, send a message to your parent (`e69ff21d-c68b-4dc5-8b54-914987353bcd`) with the path to your handoff report.
