# Progress — worker_m1

Last visited: 2026-10-30T15:20:00Z

- [x] Initialized DISPATCH.md and BRIEFING.md
- [x] Read ORIGINAL_REQUEST.md, PROJECT.md, and survey_explorer_1/handoff.md
- [x] Inspected current `main.py` and `pacman/pacman_runner.py`
- [x] Implemented changes in `main.py`
  - [x] Replaced `btn_pacman_auto` with `tk.Menubutton` ("Auto Mode ▾") and `tk.Menu` (`self.pacman_auto_menu` / `self.auto_menu`)
  - [x] Added "In-Computer Game" and "External Computer" menu choices
  - [x] Implemented `run_pacman_auto_in_computer` returning `(p_game, p_runner)`
  - [x] Implemented `run_pacman_auto_external` returning `p_runner`
  - [x] Implemented `run_pacman_auto(mode="in_computer")` backward-compatible delegation
  - [x] Updated `run_script` to return `subprocess.Popen` handle (or None on error)
- [x] Implemented changes in `pacman/pacman_runner.py`
  - [x] Added `parse_args` supporting `--capture-mode` (`screen`/`camera`) and `--camera` (device index)
  - [x] Extended `VisionEngine` to accept `capture_mode`
  - [x] Implemented `grab_screen()` and `_grab_screen()` targeting `"Pac-Man"` window via `pygetwindow` or full screen, capturing via `PIL.ImageGrab.grab(bbox=...)` and converting to BGR numpy array
  - [x] Added defensive exception handling returning `np.zeros((480, 640, 3), dtype=np.uint8)` on screen grab failure
  - [x] Handled `open_camera` returning `True` in screen capture mode without requiring physical camera
  - [x] Updated `PacmanAutoPilotApp` to accept and display `capture_mode` and `camera_index`
  - [x] Passed CLI args from `__main__`
- [x] Verified changes:
  - [x] `py_compile main.py pacman/pacman_runner.py` passed with exit code 0
  - [x] Automated unit test suite executed and passed (5/5 tests in 0.527s)
  - [x] Headless `PacmanAutoPilotApp` and `AILauncher` delegation tests passed
- [x] Documented in `handoff.md`
