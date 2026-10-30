# Project: PathFinder Launcher Auto Mode & Ghost AI Navigation

## Architecture
- **Control Center & Launcher (`main.py`)**: Tkinter GUI application providing application launching for Mapper, Racing, and Pac-Man. Manages child process execution via `subprocess.Popen`.
- **Pac-Man Autonomous Runner (`pacman/pacman_runner.py`)**: Vision and control autopilot GUI. Captures visual frames (via camera or local window), detects game state, and issues control commands.
- **Pac-Man Local Game (`pacman/pacman_game.py`)**: Pygame simulation of 28x31 Pac-Man maze, ghost state machines, tile collisions, and Pac-Man movement.
- **Automated Verification Test Suite (`tests/`)**: Python standard `unittest` test suites executing headless verification of launcher options and ghost AI navigation.

## Feature Inventory
| # | Feature | Description | Milestone | Source |
|---|---------|-------------|-----------|--------|
| 1 | Launcher Auto Mode Submenu | `main.py` Auto Mode displays accessible submenu with "In-Computer Game" and "External Computer" options | M1 | ORIGINAL_REQUEST §R1 |
| 2 | In-Computer Game Launch Execution | Selecting "In-Computer Game" launches `pacman_game.py` (`--auto`) and `pacman_runner.py` (`--capture-mode screen`) | M1 | ORIGINAL_REQUEST §R1 |
| 3 | External Computer Launch Execution | Selecting "External Computer" launches `pacman_runner.py` (`--capture-mode camera`) | M1 | ORIGINAL_REQUEST §R1 |
| 4 | Runner CLI & Screen Capture | `pacman_runner.py` CLI argument parsing (`--capture-mode`, `--camera`) and `VisionEngine` window grab support with headless fallback | M1 | Survey Explorer 1 |
| 5 | Maze Pen Door Wall Collision | `pacman_game.py` registers '=' door tiles in `Maze.doors` and blocks entry for ghosts in CHASE mode | M2 | ORIGINAL_REQUEST §R2 |
| 6 | Ghost Active Exit State Machine | Ghosts inside pen (rows 12-15) initialize in `EXITING` state, aligning to col 13/14 and ascending through door row 12 | M2 | ORIGINAL_REQUEST §R2 |
| 7 | Ghost Corridor Pursuit AI | Ghosts exiting pen transition to `CHASE` mode, pursuing Pac-Man in corridor paths without oscillating or pen re-entry | M2 | ORIGINAL_REQUEST §R2 |
| 8 | Blinky & Pinky Pen-Entry Prevention | Ghosts starting at row 11 do not dive down into pen on game start | M2 | Survey Explorer 2 |
| 9 | Automated Launcher Verification Tests | `tests/test_launcher.py` verifying submenu UI options and `Popen` launch invocations | M3 | ORIGINAL_REQUEST §R3 |
| 10 | Automated Ghost AI Navigation Tests | `tests/test_ghost_ai.py` verifying door traversal, corridor entry (row < 12), and non-oscillation | M3 | ORIGINAL_REQUEST §R3 |
| 11 | Full Test Suite Execution & Integration | All unit and integration tests passing cleanly via unittest discovery | M3 | ORIGINAL_REQUEST §R3 |

## Milestones
| # | Name | Scope | Dependencies | Status |
|---|------|-------|-------------|--------|
| M1 | Launcher Submenu & Runner Capture | `main.py` submenu UI + `pacman_runner.py` CLI & screen capture | None | DONE |
| M2 | Ghost House Exit & Navigation AI | `pacman/pacman_game.py` door collision, exit sequence & pursuit | None | DONE |
| M3 | Automated Verification Tests & E2E Validation | `tests/test_launcher.py`, `tests/test_ghost_ai.py` test suite & clean pass | M1, M2 | DONE |

## Interface Contracts
### `main.py` ↔ `pacman/pacman_game.py`
- Executable invocation: `python pacman/pacman_game.py --auto`
- Working directory: `pacman/`
- Effect: Starts game in autonomous mode (`manual_mode=False`), window title contains `"Pac-Man"`.

### `main.py` ↔ `pacman/pacman_runner.py`
- In-Computer command: `python pacman/pacman_runner.py --capture-mode screen`
- External Computer command: `python pacman/pacman_runner.py --capture-mode camera`
- Working directory: `pacman/`
- Effect: Starts runner GUI configured for specified capture source.

### `main.py` Method Interface
- `run_pacman_auto_in_computer() -> tuple[subprocess.Popen, subprocess.Popen]`
- `run_pacman_auto_external() -> subprocess.Popen`
- `run_pacman_auto(mode="in_computer")`
- `run_script(script_name, folder_path, extra_args=None) -> subprocess.Popen`

### `pacman/pacman_game.py` Interface
- `Maze.is_wall(c, r, allow_door=False) -> bool`
- `Ghost.state`: `"EXITING"` or `"CHASE"`
- Door coordinates: `(13, 12)` and `(14, 12)`
- Target corridor row upon exit: `row <= 11`

## Code Layout
- `main.py`: Launcher GUI and process dispatcher
- `pacman/pacman_runner.py`: Autopilot vision engine and GUI
- `pacman/pacman_game.py`: Pac-Man game simulation, maze, ghost AI
- `tests/test_launcher.py`: Automated tests for launcher submenu and launch commands
- `tests/test_ghost_ai.py`: Automated tests for ghost pen exit and corridor navigation
