# BRIEFING — 2026-10-30T15:18:00Z

## Mission
Milestone 1: Implement Launcher Auto Mode Submenu (In-Computer Game / External Computer) in `main.py` and Screen/Camera capture mode CLI & support in `pacman/pacman_runner.py`.

## 🔒 My Identity
- Archetype: teamwork_worker
- Roles: implementer, qa, specialist
- Working directory: c:\Users\joash\OneDrive\Documents\Github\PathFinder\.agents\teamwork\worker_m1
- Original parent: e69ff21d-c68b-4dc5-8b54-914987353bcd
- Milestone: Milestone 1: Launcher Submenu & Runner Capture

## 🔒 Key Constraints
- Exclusively own and edit `main.py` and `pacman/pacman_runner.py`.
- Do NOT edit `pacman/pacman_game.py` or test files.
- Genuine implementation only, no dummy/facade implementations or hardcoding.
- Return subprocess.Popen in `run_script`.
- Support `--capture-mode` (`screen` / `camera`) and `--camera` in `pacman_runner.py`.
- Safe screen grabbing with fallback on failure.

## Current Parent
- Conversation ID: e69ff21d-c68b-4dc5-8b54-914987353bcd
- Updated: not yet

## Task Summary
- **What to build**: Menubutton submenu in `main.py` with choices "In-Computer Game" and "External Computer", handler methods (`run_pacman_auto_in_computer`, `run_pacman_auto_external`, `run_pacman_auto`), `subprocess.Popen` return in `run_script`. In `pacman/pacman_runner.py`, add CLI parsing for `--capture-mode` and `--camera`, screen capture via `pygetwindow`/`PIL.ImageGrab` fallback to full screen and black frame fallback on error.
- **Success criteria**: Py_compile passes, headless unit tests / manual checks pass, robust screen capture fallback.
- **Interface contracts**: PROJECT.md & ORIGINAL_REQUEST.md
- **Code layout**: Root `main.py` and module `pacman/pacman_runner.py`.

## Key Decisions Made
- Replaced `btn_pacman_auto` with `tk.Menubutton` displaying "Auto Mode ▾", bound to `tk.Menu` providing "In-Computer Game" and "External Computer". Linked menu to both `self.pacman_auto_menu` and `self.auto_menu` alias for full backwards/test compatibility.
- `run_script` modified to return `subprocess.Popen` instance or `None` on error.
- `run_pacman_auto_in_computer` launches `pacman_game.py` with `["--auto"]` and `pacman_runner.py` with `["--capture-mode", "screen"]`, returning `(p_game, p_runner)`.
- `run_pacman_auto_external` launches `pacman_runner.py` with `["--capture-mode", "camera"]`, returning `p_runner`.
- `run_pacman_auto(mode="in_computer")` backward-compatible delegation.
- In `pacman_runner.py`, implemented `parse_args` supporting `--capture-mode` (`screen`/`camera`) and `--camera` index.
- In `VisionEngine`, added `capture_mode`, `grab_screen()` and `_grab_screen()` using `pygetwindow.getWindowsWithTitle("Pac-Man")` with `PIL.ImageGrab.grab(bbox=...)` converting RGB/RGBA to BGR numpy array with try/except fallback returning a black frame (`np.zeros((480, 640, 3), dtype=np.uint8)`). In `open_camera()`, returns `True` immediately if `capture_mode == "screen"` to avoid camera dependency.

## Artifact Index
- DISPATCH.md — assignment details
- BRIEFING.md — working memory
- progress.md — liveness heartbeat
- handoff.md — 5-component handoff report

## Change Tracker
- **Files modified**:
  - `main.py`: Replaced button with Menubutton and auto_menu; returned Popen from run_script; added run_pacman_auto_in_computer, run_pacman_auto_external, and updated run_pacman_auto.
  - `pacman/pacman_runner.py`: Added argparse parsing, capture_mode/camera args; added screen grabbing to VisionEngine with pygetwindow/ImageGrab and black frame fallback; updated PacmanAutoPilotApp.
- **Build status**: Pass (`py_compile` succeeded on both files, test suite 5/5 pass)
- **Pending issues**: None

## Quality Status
- **Build/test result**: Pass (5 unit tests in 0.527s)
- **Lint status**: Clean
- **Tests added/modified**: Verified via in-memory unittest suite covering menu attributes, launch arguments, Popen return, invoke callbacks, and CLI argument parsing.

## Loaded Skills
- None specified
