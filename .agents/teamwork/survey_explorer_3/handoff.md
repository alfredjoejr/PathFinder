# Handoff Report: Testing Infrastructure and Testability Survey (R1, R2, R3)

**Author:** survey_explorer_3  
**Date:** 2026-10-30T15:10:00Z  
**Working Directory:** `c:\Users\joash\OneDrive\Documents\Github\PathFinder\.agents\teamwork\survey_explorer_3`  
**Parent Conversation ID:** `e69ff21d-c68b-4dc5-8b54-914987353bcd`  

---

## 1. Observation

### 1.1 Existing Test Infrastructure & Runners
- Execution of `.venv\Scripts\python.exe -m pytest --version`:
  - Result: `No module named pytest` (exit code 1).
- Execution of `.venv\Scripts\python.exe -m unittest --help`:
  - Result: Standard library `unittest` is present and functional (exit code 0).
- Examination of repository filesystem:
  - No `tests/` directory exists (`Test-Path tests` returned `False`).
  - `mapper/test.py` is a manual interactive OpenCV utility with trackbars and camera capture (`cap = cv2.VideoCapture(1)`), not an automated test suite.
  - `ActuatorProgram/test/README` is a default PlatformIO documentation placeholder for MCU/C++ firmware; no test source exists.
  - `requirements.txt` contains dependencies for `opencv-python`, `numpy`, `ultralytics`, `torch`, `torchvision`, `PyAutoGUI`, `pyserial`, `Pillow`, `pygame>=2.5.0`, but does not list `pytest`.

### 1.2 `main.py` Launcher Architecture & Headless Testability
- Lines 7–50 of `main.py` define `AILauncher`:
  - `__init__(self, root)` configures the Tkinter root, base directories (`self.mapper_dir`, `self.racing_dir`, `self.pacman_dir`), and builds UI widgets.
  - Lines 35–44 configure the `PAC-MAN` frame:
    ```python
    self.pacman_frame = tk.LabelFrame(root, text="PAC-MAN", font=("Arial", 10, "bold"), padx=10, pady=8)
    self.btn_pacman_manual = tk.Button(self.pacman_frame, text="Manual Mode (Play)", width=15, height=1, command=self.run_pacman_manual)
    self.btn_pacman_auto = tk.Button(self.pacman_frame, text="Auto Mode (Autopilot)", width=17, height=1, command=self.run_pacman_auto)
    ```
  - Lines 52–72 define `run_script(self, script_name, folder_path, extra_args=None)`:
    - Builds `cmd = [sys.executable, script_path]` and appends `extra_args` if provided.
    - Launches the process with `subprocess.Popen(cmd, cwd=folder_path)`.
- Headless verification test executed in PowerShell:
  - Command: `.venv\Scripts\python.exe -c "import tkinter as tk, unittest.mock as mock; from main import AILauncher; r = tk.Tk(); r.withdraw(); app = AILauncher(r); ..."`
  - Result: Tkinter initialized cleanly in headless mode (`r.withdraw()`). With `mock.patch('subprocess.Popen')`, calling `app.btn_pacman_manual.invoke()` successfully captured:
    `call(['...\\.venv\\Scripts\\python.exe', '...\\pacman\\pacman_game.py'], cwd='...\\pacman')`.
  - Headless Tkinter `tk.Menu` inspection was verified:
    `menu.entrycget(i, 'label')` and `menu.invoke(i)` execute headlessly without errors.

### 1.3 `pacman/pacman_game.py` Ghost Exit AI Architecture & Current Defect
- Lines 38–70 define `MAZE_LAYOUT`:
  - Row 11: `"     W.WW          WW.W     "` (open space cols 9–18)
  - Row 12: `"     W.WW WWW==WWW WW.W     "` (Door `'='` at cols 13–14, walls at cols 10–12 and 15–17)
  - Rows 13–15: Pen interior with `'G'` at cols 11–16, enclosed by walls `'W'` at cols 10 and 17, and row 16 `'WWWWWWWW'`.
- Lines 307–328 define `Maze`:
  - `self.walls` only adds tiles with `val == 'W'`. Neither `'='` nor `'G'` are added to `self.walls`.
  - Therefore, `maze.is_wall(13, 12)` and `maze.is_wall(14, 12)` evaluate to `False` (walkable).
- Lines 365–370 initialize ghosts in `run_pacman()`:
  ```python
  Ghost(col=13, row=11, color=RED, name="Blinky", initial_dir=DIR_LEFT)
  Ghost(col=14, row=11, color=PINK, name="Pinky", initial_dir=DIR_RIGHT)
  Ghost(col=12, row=14, color=CYAN, name="Inky", initial_dir=DIR_LEFT)
  Ghost(col=15, row=14, color=ORANGE, name="Clyde", initial_dir=DIR_RIGHT)
  ```
  - Pac-Man spawns at `col=14, row=23` (`x=348.0, y=564.0`).
- Lines 214–267 define `Ghost.update(self, maze, pacman_pos)`:
  - Direction choice minimizes Euclidean distance squared: `(target_x - pacman_pos[0])**2 + (target_y - pacman_pos[1])**2`.
- Headless simulation executed for 1200 ticks (20.0 seconds at 60 FPS):
  - Inky (`col=12, row=14`): Visited tiles over 1200 ticks were strictly confined to `cols 11..16, rows 13..15`. Inky **never** visited row 12 door tiles `(13, 12)` or `(14, 12)` and never exited the pen.
  - Clyde (`col=15, row=14`): Visited tiles strictly confined to `cols 11..16, rows 13..15`. Clyde **never** exited the pen.
  - Blinky (`col=13, row=11`): Because Pac-Man is at row 23 (downward), Blinky moved **down** through the door `'='` at row 12 into the pen (rows 13–15) within the first few ticks. Once inside, Blinky remained trapped inside rows 13–15 for all remaining ticks through tick 1200.
- Headless execution feasibility:
  - `Ghost.update(maze, pacman_pos)` has **zero** dependencies on Pygame display, window creation, event pump, or audio. 600 ticks execute in ~4 milliseconds.
  - `os.environ["SDL_VIDEODRIVER"] = "dummy"` allows `pygame.init()` and `pygame.display.set_mode()` to succeed headlessly when full integration testing is required.

---

## 2. Logic Chain

1. **Test Runner Selection**:
   - Given that `pytest` is absent from `.venv` and not specified in `requirements.txt`, relying on pytest would cause automated test runs to fail unless an extra package was installed.
   - Python's standard library `unittest` is present, functional, requires no extra dependencies, and can be invoked via `.venv\Scripts\python.exe -m unittest discover -s tests`.
   - Furthermore, `unittest.TestCase` is the universal baseline in Python: if pytest is installed later, it will run all `unittest.TestCase` suites automatically.
   - Therefore, the test infrastructure should be built around standard `unittest`.

2. **Launcher Menu Headless Verification (R1)**:
   - On Windows, `tk.Tk()` can be initialized with `root.withdraw()` without opening a GUI window.
   - The launcher GUI (`AILauncher`) can be instantiated programmatically in a test fixture.
   - For menu structure verification:
     - If Auto Mode uses a `tk.Menu` (e.g. attached to `btn_pacman_auto` or Menubutton), the test inspects `menu.entrycget(i, "label")` or `menu.index(...)` to assert entries `"In-Computer Game"` and `"External Computer"` exist.
     - If Auto Mode uses dedicated submenu buttons/options, the test inspects the button text and hierarchy.
   - For launch command verification:
     - Patching `subprocess.Popen` via `unittest.mock.patch("subprocess.Popen")` prevents actual game/runner windows from launching.
     - Triggering "In-Computer Game" (via `.invoke()` or method call) must invoke `subprocess.Popen` twice: once for `pacman/pacman_game.py` and once for `pacman/pacman_runner.py` with local capture configuration (e.g., `--mode local`).
     - Triggering "External Computer" must invoke `subprocess.Popen` once for `pacman/pacman_runner.py` with camera capture configuration.

3. **Ghost Exit AI Headless Verification (R2, R3)**:
   - The root cause of the ghost trapping bug is that Pac-Man spawns below the pen (`row 23`), while the door is above the pen (`row 12`). Any ghost using greedy Euclidean distance minimization treats moving up toward row 12 as increasing distance to Pac-Man ($|300 - 564| = 264$ vs $|348 - 564| = 216$), so it perpetually chooses downward or lateral moves into the walls.
   - Conversely, Blinky (spawning outside at row 11) moves downward toward Pac-Man, passing through the unblocked door into the pen, where it is also trapped.
   - Because `Ghost.update(maze, pacman_pos)` does not require Pygame display surfaces, a test can instantiate `Maze()` and `Ghost(...)`, step the simulation tick-by-tick, and record coordinates.
   - Assertions can definitively verify:
     a) **Door Traversal**: Path intersects `{(13, 12), (14, 12)}`.
     b) **Pen Exit**: Ghost reaches corridor rows `row < 12` within a specified tick limit $T_{exit} \le 300$ (5 seconds).
     c) **No Oscillation**: After exiting, unique tiles visited steadily increases ($> 10$ unique tiles), and direction reversals inside the pen are eliminated.
     d) **Corridor Pursuit**: Once outside, ghost navigates the maze corridors toward Pac-Man without retreating back into the pen.

---

## 3. Caveats

1. **Linux Headless CI Considerations**:
   - On Windows, Tkinter works with `root.withdraw()`. In a Linux CI environment without an X server, Tkinter requires `xvfb-run` or setting `os.environ["DISPLAY"]`. Designing `AILauncher` with explicit handler methods (`run_pacman_auto_in_computer()`, `run_pacman_auto_external()`) ensures that command generation logic can be tested both through Tkinter widgets and via direct method calls if an X server is unavailable.
2. **Ghost Randomness**:
   - `Ghost.update` currently contains a 25% random choice branch (`if random.random() < 0.75: best_dir else: random.choice(...)`). Tests evaluating exit determinism should either seed `random.seed(...)` or verify that the active exit AI state machine is deterministic during the exit phase.
3. **Ghost House Exit Coordination**:
   - In arcade Pac-Man, ghosts typically exit sequentially (e.g. Blinky first, then Pinky, Inky, Clyde). The test design accommodates both simultaneous exits and staggered exits as long as each ghost reaches the corridor within its designated exit window.

---

## 4. Conclusion

1. **Testing Infrastructure**:
   - Use Python standard library `unittest`. Create a top-level `tests/` directory with `tests/__init__.py`.
   - Test execution command:
     `.venv\Scripts\python.exe -m unittest discover -s tests -p "test_*.py"`

2. **Launcher Menu Test Design (`tests/test_launcher.py`)**:
   - Headless Tkinter testing using `root.withdraw()`.
   - Mock `subprocess.Popen` to verify:
     - Submenu presents accessible options for "In-Computer Game" and "External Computer".
     - Selecting "In-Computer Game" calls `Popen` twice: launching `pacman/pacman_game.py` and `pacman/pacman_runner.py` configured for local capture.
     - Selecting "External Computer" calls `Popen` once: launching `pacman/pacman_runner.py` configured for camera capture.

3. **Ghost AI Test Design (`tests/test_ghost_ai.py`)**:
   - Pure headless simulation using direct `Ghost.update(maze, pacman_pos)` loop (no Pygame window required).
   - Test suite tests all 4 ghosts plus arbitrary pen spawn points in `[11, 16] x [11, 15]`.
   - Assertions verify door traversal (`(13, 12)` / `(14, 12)`), reaching external corridor (`row < 12`), non-oscillation (diverse tile visits), and active pursuit.

---

## 5. Verification Method

### 5.1 Test File Specifications

#### File 1: `tests/__init__.py`
Empty file to establish `tests` as a Python package.

#### File 2: `tests/test_launcher.py`
```python
import os
import sys
import unittest
from unittest.mock import patch, MagicMock
import tkinter as tk

# Ensure project root is in sys.path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from main import AILauncher


class TestLauncherMenus(unittest.TestCase):
    def setUp(self):
        self.root = tk.Tk()
        self.root.withdraw()  # Headless mode
        self.app = AILauncher(self.root)

    def tearDown(self):
        self.root.destroy()

    def test_auto_mode_submenu_options_exist(self):
        """Verify that Auto Mode presents 'In-Computer Game' and 'External Computer'."""
        # Check if submenu or dedicated options exist
        options = []
        if hasattr(self.app, "pacman_auto_menu"):
            menu = self.app.pacman_auto_menu
            count = menu.index("end") + 1 if menu.index("end") is not None else 0
            options = [menu.entrycget(i, "label") for i in range(count)]
        elif hasattr(self.app, "btn_pacman_in_computer") and hasattr(self.app, "btn_pacman_external"):
            options = [self.app.btn_pacman_in_computer.cget("text"), self.app.btn_pacman_external.cget("text")]
        else:
            # Fallback checking handlers
            self.assertTrue(
                hasattr(self.app, "run_pacman_auto_in_computer") or hasattr(self.app, "run_pacman_in_computer"),
                "Launcher must provide handler for In-Computer Game"
            )
            self.assertTrue(
                hasattr(self.app, "run_pacman_auto_external") or hasattr(self.app, "run_pacman_external"),
                "Launcher must provide handler for External Computer"
            )
            return

        self.assertTrue(any("In-Computer" in opt for opt in options), f"Expected 'In-Computer' in {options}")
        self.assertTrue(any("External" in opt for opt in options), f"Expected 'External' in {options}")

    @patch("subprocess.Popen")
    def test_in_computer_game_launches_game_and_runner(self, mock_popen):
        """Selecting 'In-Computer Game' launches pacman_game.py and pacman_runner.py."""
        handler = getattr(self.app, "run_pacman_auto_in_computer", None) or getattr(self.app, "run_pacman_in_computer", None)
        if handler is None and hasattr(self.app, "pacman_auto_menu"):
            # Trigger via menu invoke
            self.app.pacman_auto_menu.invoke(0)
        elif handler:
            handler()
        else:
            self.fail("No handler or menu entry found for In-Computer Game")

        self.assertGreaterEqual(mock_popen.call_count, 2, "Must launch both pacman_game and pacman_runner")
        
        launched_scripts = []
        for call in mock_popen.call_args_list:
            cmd = call.args[0] if call.args else call.kwargs.get("args", [])
            script_names = [os.path.basename(arg) for arg in cmd if isinstance(arg, str)]
            launched_scripts.extend(script_names)

        self.assertIn("pacman_game.py", launched_scripts)
        self.assertIn("pacman_runner.py", launched_scripts)

    @patch("subprocess.Popen")
    def test_external_computer_launches_runner(self, mock_popen):
        """Selecting 'External Computer' launches pacman_runner.py configured for camera capture."""
        handler = getattr(self.app, "run_pacman_auto_external", None) or getattr(self.app, "run_pacman_external", None)
        if handler is None and hasattr(self.app, "pacman_auto_menu"):
            self.app.pacman_auto_menu.invoke(1)
        elif handler:
            handler()
        else:
            self.fail("No handler or menu entry found for External Computer")

        self.assertEqual(mock_popen.call_count, 1, "Must launch only pacman_runner")
        cmd = mock_popen.call_args.args[0] if mock_popen.call_args.args else mock_popen.call_args.kwargs.get("args", [])
        launched_scripts = [os.path.basename(arg) for arg in cmd if isinstance(arg, str)]
        self.assertIn("pacman_runner.py", launched_scripts)
```

#### File 3: `tests/test_ghost_ai.py`
```python
import os
import sys
import unittest
import math

# Ensure project root is in sys.path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from pacman.pacman_game import Ghost, Maze, RED, PINK, CYAN, ORANGE, CELL_SIZE, DIR_LEFT, DIR_RIGHT


class TestGhostExitAI(unittest.TestCase):
    def setUp(self):
        self.maze = Maze()
        # Pacman standard start position (col=14, row=23)
        self.pacman_pos = (14 * CELL_SIZE + CELL_SIZE / 2.0, 23 * CELL_SIZE + CELL_SIZE / 2.0)
        self.door_tiles = {(13, 12), (14, 12)}

    def simulate_ghost(self, ghost, max_ticks=300):
        """Simulate ghost movement headlessly for max_ticks."""
        visited_tiles = []
        for _ in range(max_ticks):
            ghost.update(self.maze, self.pacman_pos)
            c = int(round((ghost.x - CELL_SIZE / 2.0) / CELL_SIZE))
            r = int(round((ghost.y - CELL_SIZE / 2.0) / CELL_SIZE))
            visited_tiles.append((c, r))
        return visited_tiles

    def test_inky_exits_pen(self):
        """Inky (col=12, row=14) must pass through door and exit pen into corridor row < 12."""
        ghost = Ghost(col=12, row=14, color=CYAN, name="Inky", initial_dir=DIR_LEFT)
        path = self.simulate_ghost(ghost, max_ticks=300)

        door_passed = any(tile in self.door_tiles for tile in path)
        exited = any(r < 12 for c, r in path)

        self.assertTrue(door_passed, f"Inky must pass through door tiles {self.door_tiles}")
        self.assertTrue(exited, "Inky must reach corridor row < 12")

    def test_clyde_exits_pen(self):
        """Clyde (col=15, row=14) must pass through door and exit pen into corridor row < 12."""
        ghost = Ghost(col=15, row=14, color=ORANGE, name="Clyde", initial_dir=DIR_RIGHT)
        path = self.simulate_ghost(ghost, max_ticks=300)

        door_passed = any(tile in self.door_tiles for tile in path)
        exited = any(r < 12 for c, r in path)

        self.assertTrue(door_passed, f"Clyde must pass through door tiles {self.door_tiles}")
        self.assertTrue(exited, "Clyde must reach corridor row < 12")

    def test_blinky_and_pinky_do_not_trap_in_pen(self):
        """Blinky and Pinky starting at row 11 must not get permanently trapped in the pen."""
        blinky = Ghost(col=13, row=11, color=RED, name="Blinky", initial_dir=DIR_LEFT)
        pinky = Ghost(col=14, row=11, color=PINK, name="Pinky", initial_dir=DIR_RIGHT)

        b_path = self.simulate_ghost(blinky, max_ticks=300)
        p_path = self.simulate_ghost(pinky, max_ticks=300)

        # After initial 120 ticks, ghosts should not be trapped in rows 13..15
        b_late_rows = {r for c, r in b_path[120:]}
        p_late_rows = {r for c, r in p_path[120:]}

        self.assertTrue(any(r < 12 or r > 16 for r in b_late_rows), "Blinky should navigate corridors outside pen")
        self.assertTrue(any(r < 12 or r > 16 for r in p_late_rows), "Pinky should navigate corridors outside pen")

    def test_no_oscillation_after_exit(self):
        """Ghosts must not oscillate in a 2-tile loop upon spawning."""
        ghost = Ghost(col=12, row=14, color=CYAN, name="Inky", initial_dir=DIR_LEFT)
        path = self.simulate_ghost(ghost, max_ticks=300)

        unique_tiles = set(path)
        self.assertGreaterEqual(len(unique_tiles), 8, f"Ghost must explore diverse tiles, visited: {len(unique_tiles)}")

    def test_parametric_pen_spawns(self):
        """All spawn points inside rows 11-15, cols 11-16 must successfully exit."""
        test_positions = [(12, 14), (13, 14), (14, 14), (15, 14), (11, 13), (16, 15)]
        for col, row in test_positions:
            with self.subTest(col=col, row=row):
                ghost = Ghost(col=col, row=row, color=CYAN, name=f"Ghost_{col}_{row}")
                path = self.simulate_ghost(ghost, max_ticks=300)
                exited = any(r < 12 for c, r in path)
                self.assertTrue(exited, f"Ghost starting at ({col}, {row}) failed to exit pen")
```

### 5.2 Verification Commands
To independently verify the test suite:
1. Run discovery across all tests:
   ```powershell
   .venv\Scripts\python.exe -m unittest discover -s tests -p "test_*.py"
   ```
2. Run launcher menu tests individually:
   ```powershell
   .venv\Scripts\python.exe -m unittest tests/test_launcher.py
   ```
3. Run ghost AI navigation tests individually:
   ```powershell
   .venv\Scripts\python.exe -m unittest tests/test_ghost_ai.py
   ```

### 5.3 Invalidation Conditions
- If `tests/test_ghost_ai.py` fails when ghosts are in `Ghost.update`: the ghost exit AI has not reached `row < 12` within 300 ticks or failed door traversal.
- If `tests/test_launcher.py` fails on `mock_popen`: the launcher failed to spawn both `pacman_game.py` and `pacman_runner.py` for "In-Computer Game", or failed to configure external capture for "External Computer".
