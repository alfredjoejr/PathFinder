## 2026-10-30T14:58:35Z

Enhance the launcher control center with Auto Mode submenu selection for local in-computer game and external computer execution, and fix the ghost AI in `pacman/pacman_game.py` so ghosts exit the pen immediately and pursue Pac-Man.

Integrity mode: development

## Requirements

### R1. Auto Mode Submenu Selection in Launcher
Under the PAC-MAN section in `main.py`, the Auto Mode option must present two choices: "In-Computer Game" and "External Computer".
- Selecting "In-Computer Game" must launch the local game (`pacman/pacman_game.py`) alongside the GUI runner (`pacman/pacman_runner.py`), with the runner configured to capture the local game screen or window.
- Selecting "External Computer" must launch the GUI runner (`pacman/pacman_runner.py`) configured for external computer capture (e.g., via USB camera).

### R2. Ghost House Exit and Navigation AI
In `pacman/pacman_game.py`, ghosts starting inside the ghost pen (rows 11-15, cols 11-16) must not oscillate or remain stuck rotating at their initial spawn points during the opening seconds. Ghosts must execute an active exit sequence that routes them out through the pen door ('=' tiles at row 12, cols 13-14) and into the maze corridors to actively pursue Pac-Man.

### R3. Automated Verification Tests
The team must provide automated verification tests covering:
- Launcher Auto Mode submenu execution triggers the expected launch commands for "In-Computer Game" and "External Computer".
- Ghost navigation logic reliably moves ghosts out of the pen through the door tiles and into active corridor navigation without getting stuck or oscillating.

## Acceptance Criteria

### Launcher Submenus
- [ ] In `main.py`, Auto Mode provides accessible options for "In-Computer Game" and "External Computer".
- [ ] Selecting "In-Computer Game" launches `pacman/pacman_game.py` alongside `pacman/pacman_runner.py` configured for local capture.
- [ ] Selecting "External Computer" launches `pacman/pacman_runner.py` configured for camera capture.

### Ghost AI Navigation
- [ ] In `pacman/pacman_game.py`, ghosts spawned inside the pen successfully navigate out through the pen door ('=' tiles at row 12, cols 13-14).
- [ ] Ghosts do not remain oscillating or trapped at their start positions upon game start.
- [ ] Once outside the pen, ghosts actively pursue Pac-Man through the maze corridors.

### Verification
- [ ] Automated tests verify the launcher options and ghost exit navigation behavior.
- [ ] All automated tests execute and pass cleanly.

## 2026-10-30T16:30:20Z
Sentinel check: Please update your progress.md with your latest milestone status and worker_m3 progress.
