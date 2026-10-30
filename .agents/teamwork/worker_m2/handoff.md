# Milestone 2: Ghost House Exit & Navigation AI Handoff Report

**Target Files**: `pacman/pacman_game.py`, `pacman/pacman_runner.py`  
**Implementer**: worker_m2 (teamwork_worker)  
**Date**: 2026-10-30  
**Scope**: Milestone 2 — Requirement R2: Ghost house exit, door collision handling, pen re-entry prevention, and corridor pursuit AI navigation.

---

## 1. Observation

1. **Maze Class and Door Registration (`pacman/pacman_game.py:338-378`)**:
   - `MAZE_LAYOUT` line 51 contains pen doors `'='` at row 12, columns 13 and 14: `"     W.WW WWW==WWW WW.W     "`.
   - In `Maze.__init__`:
     ```python
     self.walls = set()
     self.doors = set()
     self.pellets = set()
     self.power_pellets = set()
     ...
     elif val == '=':
         self.doors.add((c, r))
     ```
   - In `Maze.is_wall(self, c, r, allow_door=False)`:
     ```python
     if r < 0 or r >= ROWS or c < 0 or c >= COLS:
         if (r == 14 or r == 15) and (c < 0 or c >= COLS):
             return False
         return True
     if (c, r) in self.walls:
         return True
     if (c, r) in self.doors and not allow_door:
         return True
     return False
     ```
   - In `Maze.draw(screen)`:
     ```python
     for (c, r) in self.doors:
         x = c * CELL_SIZE
         y = r * CELL_SIZE + CELL_SIZE // 2 - 2
         pygame.draw.rect(screen, PINK, (x, y, CELL_SIZE, 4))
     ```

2. **Ghost State Machine & Active Pen Exit (`pacman/pacman_game.py:206-273`)**:
   - In `Ghost.reset()`:
     ```python
     if 11 <= self.start_col <= 16 and 12 <= self.start_row <= 15:
         self.state = "EXITING"
     else:
         self.state = "CHASE"
     ```
   - In `Ghost.update(self, maze, pacman_pos)`:
     ```python
     if self.state == "EXITING":
         target_col = 13 if cur_col <= 13 else 14
         target_door_x = target_col * CELL_SIZE + CELL_SIZE / 2.0

         if abs(self.x - target_door_x) > self.speed:
             self.dir = DIR_LEFT if self.x > target_door_x else DIR_RIGHT
         else:
             self.x = target_door_x
             if cur_row > 11:
                 self.dir = DIR_UP
             else:
                 self.y = 11 * CELL_SIZE + CELL_SIZE / 2.0
                 self.dir = DIR_LEFT if target_col == 13 else DIR_RIGHT
                 self.state = "CHASE"
                 self._last_tile = (cur_col, 11)

         self.x += self.dir[0] * self.speed
         self.y += self.dir[1] * self.speed
         return
     ```
   - In `CHASE` mode:
     ```python
     if not maze.is_wall(next_c, next_r, allow_door=False):
         possible_dirs.append(d)
     ...
     if random.random() < 0.80:
         self.dir = best_dir
     else:
         self.dir = random.choice(possible_dirs)
     ```

3. **Autopilot Runner Window Title Exclusion (`pacman/pacman_runner.py:94-96`)**:
   - In `pacman/pacman_runner.py`, `grab_screen`:
     ```python
     if pygetwindow is not None:
         windows = [w for w in pygetwindow.getWindowsWithTitle("Pac-Man") if "Auto-Pilot" not in w.title]
         if windows:
             win = windows[0]
     ```

4. **Compiler Verification**:
   Command: `.\.venv\Scripts\python.exe -m py_compile pacman/pacman_game.py pacman/pacman_runner.py`
   Output: Clean exit code 0, no errors.

5. **Test Suite Verification**:
   Command: `.\.venv\Scripts\python.exe -m unittest discover tests`
   Output: `Ran 58 tests in 1.690s -- OK`

---

## 2. Logic Chain

1. **Premise (Door Collision Enforcement)**:
   - Previously, `'='` door tiles were neither in `self.walls` nor tracked in `self.doors`. This allowed ghosts directly above the door (Blinky and Pinky at row 11) to plunge into the pen towards Pac-Man at row 23.
   - By adding `self.doors` to `Maze` and having `is_wall(c, r, allow_door=False)` return `True` for doors, the door behaves as an impassable barrier for both Pac-Man and ghosts in `CHASE` mode.
2. **Premise (Active Pen Egress)**:
   - Ghosts starting inside the pen (Inky at `(12, 14)` and Clyde at `(15, 14)`) initialize with `self.state = "EXITING"`.
   - Inky aligns to column 13 (12 frames), Clyde aligns to column 14 (12 frames).
   - Once horizontally centered under their door column, they move `DIR_UP` through rows 14, 13, and 12 into row 11 (31 frames).
   - Total egress duration: 43 frames (< 60 frames requirement).
   - Upon reaching row 11 (`cur_row <= 11`), their coordinates snap to the corridor centerline (`y = 11 * CELL_SIZE + CELL_SIZE / 2.0`), direction turns into the open corridor (`DIR_LEFT` for col 13, `DIR_RIGHT` for col 14), state transitions to `"CHASE"`, and `self._last_tile` is recorded as `(cur_col, 11)` to ensure smooth entry into the maze without abrupt reversal.
3. **Premise (Corridor Navigation & Pen Re-entry Prevention)**:
   - In `CHASE` mode, `maze.is_wall(next_c, next_r, allow_door=False)` forbids any ghost from entering row 12 door tiles. Blinky and Pinky never enter the pen from row 11, and Inky and Clyde never return to the pen.
   - Non-reversal filtering (`d[0] == -self.dir[0]` etc.) prevents 180° back-and-forth oscillation at corridor centers.
   - 80% greedy Euclidean distance minimization to `(pacman.x, pacman.y)` + 20% random exploration creates active pursuit that reliably intercepts Pac-Man.

---

## 3. Caveats

1. **Scatter Mode**: Standard arcade Pac-Man alternates between Scatter and Chase timers. The existing implementation does not implement arcade scatter timers; per specifications, the simplified greedy pursuit with 20% exploration was maintained and refined.
2. **Speed Values**: Ghost speed is fixed at 2.0 pixels/frame. Tile center snapping ensures that non-integer speeds or fractional coordinates will not cause overshoot or phase errors.
3. **No Other Caveats**: All geometric constraints, coordinate systems, door positions, and collision masks conform strictly to `MAZE_LAYOUT` and `PROJECT.md`.

---

## 4. Conclusion

Requirement R2 is completely satisfied:
- Doorway collision registration blocks pen re-entry for all chasing ghosts and prevents Pac-Man from entering the ghost pen.
- Inky and Clyde execute an autonomous exit sequence through door columns 13 and 14, reaching row 11 in 43 frames (< 60 frames).
- Blinky and Pinky remain outside the pen and immediately patrol row 11.
- All four ghosts actively pursue Pac-Man without oscillating or cycling endlessly in the pen.
- The optional runner window title exclusion fix was applied to prevent the autopilot runner from capturing its own GUI dashboard.

---

## 5. Verification Method

### 5.1 Compilation
Run:
```powershell
.\.venv\Scripts\python.exe -m py_compile pacman/pacman_game.py pacman/pacman_runner.py
```
Expected: Clean exit code 0.

### 5.2 Unit Test Discovery
Run:
```powershell
.\.venv\Scripts\python.exe -m unittest discover tests
```
Expected: All 58 tests pass cleanly.

### 5.3 Headless Ghost Simulation Test
Run:
```powershell
.\.venv\Scripts\python.exe -c "
import sys, math
from pacman.pacman_game import Maze, Ghost, Pacman, DIR_LEFT, DIR_RIGHT, CELL_SIZE

maze = Maze()
pacman = Pacman(14, 23)
ghosts = [
    Ghost(col=13, row=11, color=(255,0,0), name='Blinky', initial_dir=DIR_LEFT),
    Ghost(col=14, row=11, color=(255,183,255), name='Pinky', initial_dir=DIR_RIGHT),
    Ghost(col=12, row=14, color=(0,255,255), name='Inky', initial_dir=DIR_LEFT),
    Ghost(col=15, row=14, color=(255,183,81), name='Clyde', initial_dir=DIR_RIGHT),
]

# 1. Verify pen exit within 60 frames and no pen entry by Blinky/Pinky
for frame in range(1, 61):
    for g in ghosts:
        g.update(maze, (pacman.x, pacman.y))
        c = int(round((g.x - CELL_SIZE / 2.0) / CELL_SIZE))
        r = int(round((g.y - CELL_SIZE / 2.0) / CELL_SIZE))
        if g.name in ('Blinky', 'Pinky'):
            assert not (11 <= c <= 16 and 12 <= r <= 15), f'{g.name} entered pen at frame {frame}'

for g in ghosts:
    c = int(round((g.x - CELL_SIZE / 2.0) / CELL_SIZE))
    r = int(round((g.y - CELL_SIZE / 2.0) / CELL_SIZE))
    assert not (11 <= c <= 16 and 12 <= r <= 15), f'{g.name} failed to exit pen: ({c}, {r})'
    assert g.state == 'CHASE'

print('PASS: Pen exit and non-entry verified.')

# 2. Verify corridor pursuit without oscillation
intercepted = False
positions = {g.name: [] for g in ghosts}
for frame in range(61, 400):
    for g in ghosts:
        g.update(maze, (pacman.x, pacman.y))
        c = int(round((g.x - CELL_SIZE / 2.0) / CELL_SIZE))
        r = int(round((g.y - CELL_SIZE / 2.0) / CELL_SIZE))
        assert not (11 <= c <= 16 and 12 <= r <= 15), f'{g.name} re-entered pen during CHASE'
        positions[g.name].append((round(g.x), round(g.y)))
        if math.hypot(pacman.x - g.x, pacman.y - g.y) < (pacman.radius + g.radius):
            intercepted = True

for name, pos_list in positions.items():
    assert len(set(pos_list)) > 50, f'{name} oscillating in place!'

assert intercepted, 'Corridor pursuit failed to intercept Pac-Man!'
print('PASS: Active pursuit and Pac-Man interception verified.')
"
```
Expected: Prints `PASS: Pen exit and non-entry verified.` and `PASS: Active pursuit and Pac-Man interception verified.`, with clean exit code 0.

### 5.4 Invalidation Conditions
- Any ghost spawned inside the pen remains inside after 60 frames.
- Blinky or Pinky enters row 12 or pen interior.
- Ghosts oscillate or reverse between two corridor tiles every frame.
- Pac-Man walks through door tiles into the pen.
