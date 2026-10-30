## 2026-10-30T15:29:55Z
You are worker_m2 (teamwork_worker).
Your working directory is: c:\Users\joash\OneDrive\Documents\Github\PathFinder\.agents\teamwork\worker_m2
Your parent conversation ID is: e69ff21d-c68b-4dc5-8b54-914987353bcd

MANDATORY FIRST STEP:
Read c:\Users\joash\OneDrive\Documents\Github\PathFinder\.agents\teamwork\ORIGINAL_REQUEST.md before doing any work.
Also read c:\Users\joash\OneDrive\Documents\Github\PathFinder\PROJECT.md and c:\Users\joash\OneDrive\Documents\Github\PathFinder\.agents\teamwork\survey_explorer_2\handoff.md.

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

WRITE OWNERSHIP:
You exclusively own and may edit:
- `pacman/pacman_game.py`
- Optionally `pacman/pacman_runner.py` (only if applying the runner window title exclusion fix from reviewer finding: `[w for w in pygetwindow.getWindowsWithTitle("Pac-Man") if "Auto-Pilot" not in w.title]`).
Do NOT edit `main.py`.

YOUR MISSION (Milestone 2: Ghost House Exit & Navigation AI):
Implement the ghost house exit and navigation AI in `pacman/pacman_game.py` according to Requirement R2:
1. In `Maze` class:
   - Identify '=' door tiles in `__init__` and store in `self.doors = set()`.
   - Update `is_wall(self, c, r, allow_door=False)`:
     - Return True if `(c, r) in self.walls`.
     - Return True if `(c, r) in self.doors and not allow_door`.
   - In `draw(screen)`: Render the door in `PINK` (`pygame.draw.rect(screen, PINK, (c * CELL_SIZE, r * CELL_SIZE + CELL_SIZE // 2 - 2, CELL_SIZE, 4))`).
2. In `Ghost` class:
   - In `reset()`:
     - If spawned inside pen (`11 <= self.start_col <= 16 and 12 <= self.start_row <= 15`):
       `self.state = "EXITING"`
     - Else:
       `self.state = "CHASE"`
   - In `update(self, maze, pacman_pos)`:
     - Handle `self.state == "EXITING"`:
       - Target door column: `target_col = 13 if cur_col <= 13 else 14`
       - Align horizontally: if `abs(self.x - target_door_x) > self.speed`: `self.dir = DIR_LEFT if self.x > target_door_x else DIR_RIGHT`
       - When horizontally aligned (`self.x = target_door_x`):
         - If `cur_row > 11`: `self.dir = DIR_UP` (move up through the door)
         - Once outside (`cur_row <= 11`): snap `self.y = 11 * CELL_SIZE + CELL_SIZE / 2.0`, set `self.dir = DIR_LEFT if target_col == 13 else DIR_RIGHT`, set `self.state = "CHASE"`, and set `self._last_tile = (cur_col, 11)`.
       - Advance `self.x += self.dir[0] * self.speed`, `self.y += self.dir[1] * self.speed`, and return.
     - Handle `self.state == "CHASE"`:
       - In direction selection, use `not maze.is_wall(next_c, next_r, allow_door=False)` so ghosts in CHASE mode (including Blinky and Pinky at row 11) never plunge through row 12 door tiles into the pen.
       - Use Euclidean distance minimization to `pacman_pos` (80% greedy best direction, 20% random choice) avoiding immediate 180° reversals.
       - Ensure tunnel wrap logic is preserved.
3. Verification:
   - Verify code compiles cleanly: `.\.venv\Scripts\python.exe -m py_compile pacman/pacman_game.py`.
   - Run the headless simulation test to confirm that Inky and Clyde exit the pen within 60 frames, Blinky and Pinky do not enter the pen, and all ghosts pursue Pac-Man through corridors without oscillating.

Write your report in:
`c:\Users\joash\OneDrive\Documents\Github\PathFinder\.agents\teamwork\worker_m2\handoff.md`
Update your `progress.md` in your working directory.
When done, send a message to your parent (`e69ff21d-c68b-4dc5-8b54-914987353bcd`) with the path to your handoff report.
