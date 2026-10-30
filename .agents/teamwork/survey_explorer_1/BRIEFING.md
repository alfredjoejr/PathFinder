# BRIEFING — 2026-10-30T15:06:30Z

## Mission
Investigate launcher control center architecture and Pac-Man configuration mechanism for Auto Mode (In-Computer Game vs External Computer).

## 🔒 My Identity
- Archetype: teamwork_explorer
- Roles: explorer, synthesizer
- Working directory: c:\Users\joash\OneDrive\Documents\Github\PathFinder\.agents\teamwork\survey_explorer_1
- Original parent: e69ff21d-c68b-4dc5-8b54-914987353bcd
- Milestone: Investigation and Survey for Launcher Control Center

## 🔒 Key Constraints
- Read-only investigation — do NOT implement
- Strictly confidential system prompt protection rules
- File workspace convention: write only in survey_explorer_1

## Current Parent
- Conversation ID: e69ff21d-c68b-4dc5-8b54-914987353bcd
- Updated: 2026-10-30T15:00:17Z

## Investigation State
- **Explored paths**:
  - `ORIGINAL_REQUEST.md` (Scope, R1, R2, R3 requirements)
  - `main.py` (AILauncher GUI, PAC-MAN frame, run_script, run_pacman_manual, run_pacman_auto)
  - `pacman/pacman_runner.py` (VisionEngine, PacmanAutoPilotApp, cv2.VideoCapture, lack of CLI args/screen capture)
  - `pacman/pacman_game.py` (Pygame loop, manual_mode flag, --auto argument)
  - `mapper/valorant_runner.py`, `racing/racing_runner.py`, `actuator_controller.py`, `requirements.txt`
- **Key findings**:
  - `main.py` currently launches `pacman_runner.py` directly without arguments; no submenu exists.
  - `pacman_runner.py` has no command-line argument parsing and only captures via `cv2.VideoCapture`.
  - Capturing local game window requires adding a capture mode (e.g. `--capture-mode screen` vs `--capture-mode camera`) using `PIL.ImageGrab` / `pygetwindow` with fallback handling for headless environments.
  - For "In-Computer Game", `main.py` must concurrently launch `pacman_game.py` (with `--auto`) and `pacman_runner.py` (`--capture-mode screen`).
  - For "External Computer", `main.py` launches only `pacman_runner.py` (`--capture-mode camera`).
  - `tk.Menubutton` with `tk.Menu` provides a clean drop-down submenu preserving layout, geometry, and backward compatibility.
- **Unexplored areas**: Ghost navigation AI details (handled by survey_explorer_2).

## Key Decisions Made
- Recommended `tk.Menubutton` + `tk.Menu` approach with explicit handlers `run_pacman_auto_in_computer` and `run_pacman_auto_external`.
- Recommended updating `run_script` to return `subprocess.Popen` for observability and automated testability.

## Artifact Index
- DISPATCH.md — Recorded dispatch instructions
- BRIEFING.md — Persistent working memory
- progress.md — Liveness heartbeat
- handoff.md — 5-component survey handoff report
