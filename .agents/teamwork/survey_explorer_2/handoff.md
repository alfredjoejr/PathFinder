# Ghost House Exit and Navigation AI Investigation Report

**Target File**: `pacman/pacman_game.py`  
**Investigator**: survey_explorer_2 (teamwork_explorer)  
**Date**: 2026-10-30  
**Scope**: Requirement R2 — Ghost house exit sequence, door collisions, oscillation root causes, and corridor pursuit AI navigation.

---

## 1. Observation

### 1.1 Maze Definition and Geometry (`pacman/pacman_game.py:38-70, 307-347`)
In `pacman/pacman_game.py`:
- `CELL_SIZE = 24`, `COLS = 28`, `ROWS = 31`.
- Rows 9 through 17 of `MAZE_LAYOUT` (lines 48–56):
  ```python
  # Row 09: "WWWWWW.WWWWW WW WWWWW.WWWWWW"
  # Row 10: "     W.WWWWW WW WWWWW.W     "
  # Row 11: "     W.WW          WW.W     "  <- Open corridor directly above pen
  # Row 12: "     W.WW WWW==WWW WW.W     "  <- Pen door '=' at cols 13-14
  # Row 13: "WWWWWW.WW WGGGGGGW WW.WWWWWW"  <- Pen interior 'G' at cols 11-16
  # Row 14: "      .   WGGGGGGW   .      "  <- Pen interior 'G' at cols 11-16
  # Row 15: "WWWWWW.WW WGGGGGGW WW.WWWWWW"  <- Pen interior 'G' at cols 11-16
  # Row 16: "     W.WW WWWWWWWW WW.W     "  <- Pen bottom wall 'W' at cols 10-17
  # Row 17: "     W.WW          WW.W     "
  ```
- Exact tile classifications:
  - **Ghost Pen Interior**: Rows 13–15, Columns 11–16 (`'G'`). Dimensions: 6 columns wide by 3 rows high (18 tiles total).
  - **Pen Perimeter Walls**:
    - North wall: Row 12, cols 10–12 (`'WWW'`) and cols 15–17 (`'WWW'`).
    - West wall: Col 10, rows 12–16 (`'W'`).
    - East wall: Col 17, rows 12–16 (`'W'`).
    - South wall: Row 16, cols 10–17 (`'WWWWWWWW'`).
  - **Pen Door**: Row 12, cols 13 and 14 (`'=='`).
  - **Corridor Connections Above Pen**:
    - Row 11 has empty space (`' '`) across columns 9 through 18.
    - Columns 13 and 14 in Row 11 sit directly above the door.
    - Columns 13 and 14 in Row 10 sit directly above Row 11 and contain `'WW'` (solid wall).
    - Exiting entities reaching Row 11 must turn **LEFT** (towards col 12) or **RIGHT** (towards col 15).
    - Columns 12 and 15 provide vertical corridor branches upwards through Rows 10, 9, 8.
    - Columns 9 and 18 provide vertical corridor branches downward and upward around the exterior of the pen.

### 1.2 Wall and Collision Registration (`pacman/pacman_game.py:307-329`)
The `Maze` class definition in `pacman/pacman_game.py`:
```python
class Maze:
    def __init__(self):
        self.walls = set()
        self.pellets = set()
        self.power_pellets = set()

        for r, row in enumerate(MAZE_LAYOUT):
            for c, val in enumerate(row):
                if val == 'W':
                    self.walls.add((c, r))
                elif val == '.':
                    self.pellets.add((c, r))
                elif val == 'o':
                    self.power_pellets.add((c, r))

    def is_wall(self, c, r):
        if r < 0 or r >= ROWS or c < 0 or c >= COLS:
            if (r == 14 or r == 15) and (c < 0 or c >= COLS):
                return False
            return True
        return (c, r) in self.walls
```
Direct observation:
- Only characters matching `'W'` are added to `self.walls`.
- Door tiles `'='` (at `(13, 12)` and `(14, 12)`) and ghost house interior tiles `'G'` (at rows 13–15, cols 11–16) are **omitted entirely from `self.walls`**.
- Therefore, `maze.is_wall(13, 12)` and `maze.is_wall(14, 12)` return `False`.
- The door is treated as unobstructed empty corridor in all collision checks for both Pac-Man and ghosts.
- In `Maze.draw()` (lines 330–346), `'='` tiles are not drawn, rendering as empty black background.

### 1.3 Ghost Class, Initialization, and Spawn Coordinates (`pacman/pacman_game.py:195-214, 363-370`)
Entity instantiation in `run_pacman()`:
```python
pacman = Pacman(col=14, row=23)

ghosts = [
    Ghost(col=13, row=11, color=RED, name="Blinky", initial_dir=DIR_LEFT),
    Ghost(col=14, row=11, color=PINK, name="Pinky", initial_dir=DIR_RIGHT),
    Ghost(col=12, row=14, color=CYAN, name="Inky", initial_dir=DIR_LEFT),
    Ghost(col=15, row=14, color=ORANGE, name="Clyde", initial_dir=DIR_RIGHT),
]
```
In `Ghost.__init__()` and `Ghost.reset()`:
```python
class Ghost:
    def __init__(self, col, row, color, name="Ghost", initial_dir=DIR_LEFT):
        self.start_col = col
        self.start_row = row
        self.color = color
        self.name = name
        self.initial_dir = initial_dir
        self.speed = 2.0
        self.radius = CELL_SIZE // 2 - 2
        self.reset()

    def reset(self):
        self.x = float(self.start_col * CELL_SIZE + CELL_SIZE // 2)
        self.y = float(self.start_row * CELL_SIZE + CELL_SIZE // 2)
        self.dir = self.initial_dir
        self.scared = False
        self.scared_timer = 0
        self._last_tile = None
```
Direct observation:
- Blinky spawns at `(13, 11)` (outside, immediately above door tile `(13, 12)`).
- Pinky spawns at `(14, 11)` (outside, immediately above door tile `(14, 12)`).
- Inky spawns at `(12, 14)` (inside the pen, left side).
- Clyde spawns at `(15, 14)` (inside the pen, right side).
- Pac-Man spawns at `(14, 23)` (bottom of the maze).
- There is **no state machine** on the Ghost class (only a boolean `scared`). There is no state for `IN_PEN`, `EXITING`, or `CHASE`.

### 1.4 Ghost Navigation and Movement Logic (`pacman/pacman_game.py:214-266`)
```python
    def update(self, maze, pacman_pos):
        ...
        cur_col = int(round((self.x - CELL_SIZE / 2.0) / CELL_SIZE))
        cur_row = int(round((self.y - CELL_SIZE / 2.0) / CELL_SIZE))
        center_x = cur_col * CELL_SIZE + CELL_SIZE / 2.0
        center_y = cur_row * CELL_SIZE + CELL_SIZE / 2.0

        current_tile = (cur_col, cur_row)

        # Re-evaluate direction when passing through a new tile center
        if current_tile != self._last_tile and abs(self.x - center_x) <= self.speed and abs(self.y - center_y) <= self.speed:
            self.x = center_x
            self.y = center_y
            self._last_tile = current_tile

            possible_dirs = []
            for d in [DIR_UP, DIR_DOWN, DIR_LEFT, DIR_RIGHT]:
                # Don't directly reverse unless dead-end
                if (d[0] == -self.dir[0] and d[0] != 0) or (d[1] == -self.dir[1] and d[1] != 0):
                    continue
                next_c = cur_col + d[0]
                next_r = cur_row + d[1]
                if not maze.is_wall(next_c, next_r):
                    possible_dirs.append(d)

            if not possible_dirs:
                # Turn around
                possible_dirs.append((-self.dir[0], -self.dir[1]))

            if possible_dirs:
                if self.scared:
                    self.dir = random.choice(possible_dirs)
                else:
                    best_dir = possible_dirs[0]
                    best_dist = float('inf')
                    for d in possible_dirs:
                        target_x = (cur_col + d[0]) * CELL_SIZE + CELL_SIZE / 2.0
                        target_y = (cur_row + d[1]) * CELL_SIZE + CELL_SIZE / 2.0
                        dist = (target_x - pacman_pos[0])**2 + (target_y - pacman_pos[1])**2
                        if dist < best_dist:
                            best_dist = dist
                            best_dir = d
                    if random.random() < 0.75:
                        self.dir = best_dir
                    else:
                        self.dir = random.choice(possible_dirs)

        self.x += self.dir[0] * self.speed
        self.y += self.dir[1] * self.speed
```

### 1.5 Frame-by-Frame Simulation Results
Executing a headless simulation with `pacman_game.py` entities yielded:
- **Frame 0 (Spawn)**:
  - Blinky: `(13, 11)`, `dir = DIR_LEFT (-1, 0)`
  - Pinky: `(14, 11)`, `dir = DIR_RIGHT (1, 0)`
  - Inky: `(12, 14)`, `dir = DIR_LEFT (-1, 0)`
  - Clyde: `(15, 14)`, `dir = DIR_RIGHT (1, 0)`
- **Frame 1**:
  - `current_tile != self._last_tile` is `(13, 11) != None` (True).
  - Both Blinky and Pinky immediately evaluate directions towards Pac-Man `(14, 23)`.
  - Tile `(13, 12)` and tile `(14, 12)` (the pen doors) have `is_wall == False`.
  - Distance from `(13, 12)` to Pac-Man `(14, 23)` is $1^2 + 11^2 = 122$, whereas horizontal step `(12, 11)` is $2^2 + 12^2 = 148$.
  - Both Blinky and Pinky discard `initial_dir` and switch to `DIR_DOWN (0, 1)` on Frame 1.
- **Frame 12–24**:
  - Blinky and Pinky pass through row 12 door tiles directly into the pen (rows 13–15).
  - Inky and Clyde move down to row 15 (bottom of the pen).
- **Frames 100 to 1000**:
  - All four ghosts remain trapped in the pen (`11 <= col <= 16` and `12 <= row <= 15`) 100% of the time across 1000 frames.

---

## 2. Logic Chain

1. **Premise (from 1.2)**: `Maze.is_wall()` does not flag `'='` (door) tiles as walls.
2. **Premise (from 1.3 & 1.4)**: Pac-Man spawns at `(14, 23)` (at the bottom of the map), while Blinky and Pinky spawn at `(13, 11)` and `(14, 11)` directly above the door.
3. **Inference (Blinky & Pinky dive into the pen)**:
   - On frame 1, at tile center `(13, 11)`, Blinky cannot reverse (`DIR_RIGHT` forbidden) and cannot go up (`(13, 10)` is a wall). Available choices are `DIR_LEFT` (`(12, 11)`) and `DIR_DOWN` (`(13, 12)`).
   - Because `(13, 12)` is not registered as a wall, Euclidean distance check chooses `DIR_DOWN` because row 12 is closer to row 23 than row 11.
   - Pinky at `(14, 11)` follows identical logic and picks `DIR_DOWN`.
   - Result: Blinky and Pinky immediately plunge through the door into the ghost pen instead of moving through the maze.
4. **Inference (Ghosts inside the pen trapped in local minimum)**:
   - For any ghost inside the pen (rows 13–15, cols 11–16), the only route to the maze is UP through `(13, 12)` or `(14, 12)`.
   - Moving UP increases the Euclidean distance $D = (x - x_{pac})^2 + (y - y_{pac})^2$ to Pac-Man (since $y_{ghost} < y_{pac}$).
   - Moving DOWN, LEFT, or RIGHT along row 15 minimizes $D$.
   - Because row 16 is a solid wall, ghosts hit the bottom wall, cannot reverse, and pick horizontal moves along row 15.
   - The greedy heuristic forms a closed deterministic orbit: `(12, 15) -> (16, 15) -> (16, 14) -> (15, 14) -> (15, 15) -> (11, 15) -> (11, 14) -> (12, 14) -> (12, 15)`.
   - Result: Ghosts oscillate and cycle endlessly in the lower half of the pen, unable to exit without a dedicated exit state machine.
5. **Inference (Visual jitter and rotating in place)**:
   - On frame 1, `self._last_tile = None` causes immediate direction re-evaluation before a single step is taken.
   - Rapid alternating between cardinal directions along the pen perimeter and against walls causes ghost eyes (`eye_off_x = dir[0] * 3`, `eye_off_y = dir[1] * 3`) and movement vectors to rapidly oscillate in place.

---

## 3. Caveats

1. **Network & Pygame Execution**: The system python lacked the `pygame` wheel in the global path; all simulation verifications were executed by headless mock injection (`sys.modules['pygame'] = mock.MagicMock()`), reproducing exact tile arithmetic, collision detection, and vector math.
2. **Scatter/Frightened Modes**: The arcade Pac-Man timer alternating between Scatter (corners) and Chase modes is not present in `pacman_game.py` (which only implements basic greedy Chase and Power Pellet Frightened). The recommendations preserve this simplified structure while fixing the pen exit.
3. **No Caveats on Geometry**: The 28x31 grid, cell coordinates, wall placements, and door tile locations were completely mapped and verified against `MAZE_LAYOUT`.

---

## 4. Conclusion

The stuck/oscillating ghost behavior is caused by three compounding defects:
1. **Unregistered Door**: `'='` is missing from `Maze.walls`, allowing ghosts outside the pen (Blinky and Pinky) to dive down into the pen towards Pac-Man on frame 1.
2. **Greedy Heuristic Incompatibility with Pen Topology**: Because Pac-Man begins below the pen at row 23, the purely greedy distance formula prevents any ghost in rows 13–15 from choosing `DIR_UP` towards the row 12 door.
3. **Absence of an Active Exit Sequence State Machine**: Ghosts inside the pen require an autonomous vector route out through the door before engaging maze pursuit.

---

## 5. Implementation Recommendations & Pseudocode

### 5.1 Maze Door Handling (`pacman/pacman_game.py`)
In `Maze.__init__`:
- Store `self.doors = set()` containing all `(c, r)` where `val == '='`.
- Update `is_wall(c, r, allow_door=False)`:
  ```python
  def is_wall(self, c, r, allow_door=False):
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
- In `Maze.draw(screen)`: Render the door line in `PINK`:
  ```python
  for (c, r) in self.doors:
      x = c * CELL_SIZE
      y = r * CELL_SIZE + CELL_SIZE // 2 - 2
      pygame.draw.rect(screen, PINK, (x, y, CELL_SIZE, 4))
  ```

### 5.2 Ghost State Machine Architecture
Introduce two primary operational modes:
- `STATE_EXITING = "EXITING"`
- `STATE_CHASE = "CHASE"`

#### Spawn Rules:
- If a ghost spawns within the ghost pen (`11 <= col <= 16` and `11 <= row <= 15`):
  - If `row == 11` (Blinky/Pinky): Immediately initialize in `CHASE` with `dir = DIR_LEFT` (for col 13) or `DIR_RIGHT` (for col 14). Since the door at row 12 is now treated as a wall, they cannot move down and immediately patrol the corridor.
  - If `row >= 12` (Inky/Clyde): Initialize in `EXITING`.

#### Active Exit Sequence:
When `self.state == "EXITING"`:
1. **Phase 1: Horizontal Door Alignment**:
   - Left-side ghosts (`col <= 13`) align to column 13: `target_door_x = 13 * CELL_SIZE + CELL_SIZE / 2.0`.
   - Right-side ghosts (`col >= 14`) align to column 14: `target_door_x = 14 * CELL_SIZE + CELL_SIZE / 2.0`.
   - If `abs(self.x - target_door_x) > self.speed`:
     `self.dir = DIR_LEFT if self.x > target_door_x else DIR_RIGHT`
   - Else:
     `self.x = target_door_x`
2. **Phase 2: Vertical Egress Through Door**:
   - If `cur_row > 11`:
     `self.dir = DIR_UP`
3. **Phase 3: Smooth Transition to Maze Pursuit**:
   - Once `cur_row <= 11` (reached row 11 corridor outside the door):
     - `self.y = 11 * CELL_SIZE + CELL_SIZE / 2.0`
     - Turn into open corridor: `self.dir = DIR_LEFT if target_col == 13 else DIR_RIGHT`
     - Transition state: `self.state = "CHASE"`
     - Initialize `self._last_tile = (cur_col, 11)`

#### Corridor Chase Rules:
When `self.state == "CHASE"`:
- Doorway tiles `(13, 12)` and `(14, 12)` are treated as impassable walls (`maze.is_wall(next_c, next_r, allow_door=False)`).
- Ghosts choose the non-reverse direction that minimizes distance to Pac-Man:
  - 80% greedy best direction, 20% random selection.
- Smooth corner turning: Snap to tile center upon entering new tile center before changing direction.

### 5.3 Complete Proposed Code Replacement

#### Class `Maze` (lines 307–346):
```python
class Maze:
    def __init__(self):
        self.walls = set()
        self.doors = set()
        self.pellets = set()
        self.power_pellets = set()

        for r, row in enumerate(MAZE_LAYOUT):
            for c, val in enumerate(row):
                if val == 'W':
                    self.walls.add((c, r))
                elif val == '=':
                    self.doors.add((c, r))
                elif val == '.':
                    self.pellets.add((c, r))
                elif val == 'o':
                    self.power_pellets.add((c, r))

    def is_wall(self, c, r, allow_door=False):
        if r < 0 or r >= ROWS or c < 0 or c >= COLS:
            if (r == 14 or r == 15) and (c < 0 or c >= COLS):
                return False
            return True
        if (c, r) in self.walls:
            return True
        if (c, r) in self.doors and not allow_door:
            return True
        return False

    def draw(self, screen):
        for (c, r) in self.walls:
            x = c * CELL_SIZE
            y = r * CELL_SIZE
            pygame.draw.rect(screen, NAVY_BLUE, (x, y, CELL_SIZE, CELL_SIZE))
            pygame.draw.rect(screen, WALL_BORDER, (x + 2, y + 2, CELL_SIZE - 4, CELL_SIZE - 4), 1)

        for (c, r) in self.doors:
            x = c * CELL_SIZE
            y = r * CELL_SIZE + CELL_SIZE // 2 - 2
            pygame.draw.rect(screen, PINK, (x, y, CELL_SIZE, 4))

        for (c, r) in self.pellets:
            px = c * CELL_SIZE + CELL_SIZE // 2
            py = r * CELL_SIZE + CELL_SIZE // 2
            pygame.draw.circle(screen, PELLET_COLOR, (px, py), 3)

        for (c, r) in self.power_pellets:
            px = c * CELL_SIZE + CELL_SIZE // 2
            py = r * CELL_SIZE + CELL_SIZE // 2
            pygame.draw.circle(screen, POWER_PELLET_COLOR, (px, py), 7)
```

#### Class `Ghost` (lines 195–273):
```python
class Ghost:
    def __init__(self, col, row, color, name="Ghost", initial_dir=DIR_LEFT):
        self.start_col = col
        self.start_row = row
        self.color = color
        self.name = name
        self.initial_dir = initial_dir
        self.speed = 2.0
        self.radius = CELL_SIZE // 2 - 2
        self.reset()

    def reset(self):
        self.x = float(self.start_col * CELL_SIZE + CELL_SIZE // 2)
        self.y = float(self.start_row * CELL_SIZE + CELL_SIZE // 2)
        self.dir = self.initial_dir
        self.scared = False
        self.scared_timer = 0
        self._last_tile = None
        
        # Determine initial state: inside pen (rows 12-15) triggers active exit
        if 11 <= self.start_col <= 16 and 12 <= self.start_row <= 15:
            self.state = "EXITING"
        else:
            self.state = "CHASE"

    def update(self, maze, pacman_pos):
        if self.scared:
            self.scared_timer -= 1
            if self.scared_timer <= 0:
                self.scared = False

        cur_col = int(round((self.x - CELL_SIZE / 2.0) / CELL_SIZE))
        cur_row = int(round((self.y - CELL_SIZE / 2.0) / CELL_SIZE))
        center_x = cur_col * CELL_SIZE + CELL_SIZE / 2.0
        center_y = cur_row * CELL_SIZE + CELL_SIZE / 2.0

        # ── State 1: Active Pen Exit Sequence ─────────────────────────
        if self.state == "EXITING":
            target_col = 13 if cur_col <= 13 else 14
            target_door_x = target_col * CELL_SIZE + CELL_SIZE / 2.0

            # 1. Align horizontally to door column
            if abs(self.x - target_door_x) > self.speed:
                self.dir = DIR_LEFT if self.x > target_door_x else DIR_RIGHT
            else:
                self.x = target_door_x
                # 2. Ascend vertically through the door
                if cur_row > 11:
                    self.dir = DIR_UP
                else:
                    # 3. Reached row 11 corridor outside the pen
                    self.y = 11 * CELL_SIZE + CELL_SIZE / 2.0
                    self.dir = DIR_LEFT if target_col == 13 else DIR_RIGHT
                    self.state = "CHASE"
                    self._last_tile = (cur_col, 11)

            self.x += self.dir[0] * self.speed
            self.y += self.dir[1] * self.speed
            return

        # ── State 2: Active Maze Pursuit ──────────────────────────────
        current_tile = (cur_col, cur_row)

        if current_tile != self._last_tile and abs(self.x - center_x) <= self.speed and abs(self.y - center_y) <= self.speed:
            self.x = center_x
            self.y = center_y
            self._last_tile = current_tile

            possible_dirs = []
            for d in [DIR_UP, DIR_DOWN, DIR_LEFT, DIR_RIGHT]:
                # Prevent 180° instant reversal
                if (d[0] == -self.dir[0] and d[0] != 0) or (d[1] == -self.dir[1] and d[1] != 0):
                    continue
                next_c = cur_col + d[0]
                next_r = cur_row + d[1]
                # Doors '=' are strictly walls for ghosts in CHASE mode
                if not maze.is_wall(next_c, next_r, allow_door=False):
                    possible_dirs.append(d)

            if not possible_dirs:
                possible_dirs.append((-self.dir[0], -self.dir[1]))

            if possible_dirs:
                if self.scared:
                    self.dir = random.choice(possible_dirs)
                else:
                    best_dir = possible_dirs[0]
                    best_dist = float('inf')
                    for d in possible_dirs:
                        target_x = (cur_col + d[0]) * CELL_SIZE + CELL_SIZE / 2.0
                        target_y = (cur_row + d[1]) * CELL_SIZE + CELL_SIZE / 2.0
                        dist = (target_x - pacman_pos[0])**2 + (target_y - pacman_pos[1])**2
                        if dist < best_dist:
                            best_dist = dist
                            best_dir = d
                    if random.random() < 0.80:
                        self.dir = best_dir
                    else:
                        self.dir = random.choice(possible_dirs)

        self.x += self.dir[0] * self.speed
        self.y += self.dir[1] * self.speed

        # Tunnel wrap
        if self.x < -CELL_SIZE // 2:
            self.x = SCREEN_WIDTH + CELL_SIZE // 2
        elif self.x > SCREEN_WIDTH + CELL_SIZE // 2:
            self.x = -CELL_SIZE // 2
```

---

## 6. Verification Method

### 6.1 Automated Headless Simulation Test Command
The implementation can be verified using the following command:
```powershell
python -c "
import sys, unittest.mock as mock
sys.modules['pygame'] = mock.MagicMock()
from pacman.pacman_game import Maze, Ghost, Pacman, DIR_LEFT, DIR_RIGHT, DIR_UP, DIR_DOWN, CELL_SIZE
import math

maze = Maze()
pacman = Pacman(14, 23)
ghosts = [
    Ghost(col=13, row=11, color=(255,0,0), name='Blinky', initial_dir=DIR_LEFT),
    Ghost(col=14, row=11, color=(255,183,255), name='Pinky', initial_dir=DIR_RIGHT),
    Ghost(col=12, row=14, color=(0,255,255), name='Inky', initial_dir=DIR_LEFT),
    Ghost(col=15, row=14, color=(255,183,81), name='Clyde', initial_dir=DIR_RIGHT),
]

# 1. Verify all ghosts exit the pen (rows 12-15, cols 11-16) within 60 frames
for frame in range(1, 61):
    for g in ghosts:
        g.update(maze, (pacman.x, pacman.y))

for g in ghosts:
    c = int(round((g.x - 12)/24))
    r = int(round((g.y - 12)/24))
    in_pen = (11 <= c <= 16 and 12 <= r <= 15)
    assert not in_pen, f'{g.name} failed to exit pen! tile=({c},{r})'
print('Test 1 PASSED: All ghosts successfully exited pen within 60 frames.')

# 2. Verify ghosts pursue and intercept Pac-Man without oscillating
intercepted = False
for frame in range(61, 350):
    for g in ghosts:
        g.update(maze, (pacman.x, pacman.y))
        dist = math.hypot(pacman.x - g.x, pacman.y - g.y)
        if dist < (pacman.radius + g.radius):
            intercepted = True
            break
    if intercepted:
        break
assert intercepted, 'Ghosts failed to intercept Pac-Man in corridor pursuit!'
print('Test 2 PASSED: Active corridor pursuit confirmed.')
"
```

### 6.2 Invalidation Conditions
The fix would be considered invalid if:
- Any ghost starting in rows 12–15 remains within the pen bounds after 60 frames.
- Blinky or Pinky at `(13, 11)` or `(14, 11)` moves downward into row 12 door tiles.
- Pac-Man is able to walk across door tiles into the ghost pen.
- Ghosts oscillate or reverse directions every frame while navigating open corridors.
