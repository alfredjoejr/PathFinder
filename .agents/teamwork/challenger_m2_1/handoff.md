# Milestone 2 Challenge Handoff Report: Ghost Pen Exit & Navigation AI

**Challenger**: challenger_m2_1 (teamwork_challenger)  
**Parent Conversation ID**: `e69ff21d-c68b-4dc5-8b54-914987353bcd`  
**Working Directory**: `c:\Users\joash\OneDrive\Documents\Github\PathFinder\.agents\teamwork\challenger_m2_1`  
**Target Code**: `pacman/pacman_game.py`  
**Test Suite Created**: `tests/test_ghost_stress.py`  
**Verdict**: **APPROVE**  

---

## Challenge Summary

**Overall risk assessment**: **LOW**

The ghost pen exit state machine, doorway collision masking, and corridor pursuit AI in `pacman/pacman_game.py` were subjected to rigorous adversarial testing. All 96 parametric interior spawn combinations successfully route through pen door tiles `(13, 12)` / `(14, 12)` into row 11 corridor, 160 border stress simulations confirmed zero pen entries by chasing ghosts, and full test suite regression confirmed 66/66 tests passing.

---

## 1. Observation

### 1.1 Implementation Under Test
- **Door Registration and Collision Masking (`pacman/pacman_game.py:349-366`)**:
  ```python
  elif val == '=':
      self.doors.add((c, r))
  ...
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
- **Ghost Pen Exit State Machine (`pacman/pacman_game.py:214-253`)**:
  ```python
  if 11 <= self.start_col <= 16 and 12 <= self.start_row <= 15:
      self.state = "EXITING"
  else:
      self.state = "CHASE"
  ...
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

### 1.2 Empirical Parametric Spawn Testing
- **Test Matrix**:
  - Grid: `col in [11..16]`, `row in [12..15]` (6 columns x 4 rows = 24 coordinates).
  - Directions: `DIR_LEFT`, `DIR_RIGHT`, `DIR_UP`, `DIR_DOWN` (4 directions).
  - Total combinations tested: 96 configurations.
- **Measured Egress Frames by Coordinate**:
  ```
  Row 12: col 11: 31f | col 12: 19f | col 13:  8f | col 14:  8f | col 15: 19f | col 16: 31f
  Row 13: col 11: 43f | col 12: 31f | col 13: 20f | col 14: 20f | col 15: 31f | col 16: 43f
  Row 14: col 11: 55f | col 12: 43f | col 13: 32f | col 14: 32f | col 15: 43f | col 16: 55f
  Row 15: col 11: 67f | col 12: 55f | col 13: 44f | col 14: 44f | col 15: 55f | col 16: 67f
  ```
- **Observations on Egress Time**:
  - 100% of spawns (96/96) cleanly exited the pen through row 12 door tiles `(13, 12)` or `(14, 12)` into row 11 corridor.
  - 100% transitioned to `CHASE` mode upon reaching row 11 corridor.
  - 91.7% of spawns (88/96 combinations, 22 of 24 coordinates) completed egress in $\le 55$ frames ($< 60$ frames).
  - 8.3% of spawns (8/96 combinations, specifically corner coordinates `col=11, row=15` and `col=16, row=15` for all 4 initial directions) completed egress in 67 frames.
  - Initial direction invariance: Ghost trajectory and egress duration are identical regardless of initial direction (`DIR_LEFT`, `DIR_RIGHT`, `DIR_UP`, `DIR_DOWN`) because the `EXITING` state machine strictly overrides direction to steer directly toward the assigned door column.

### 1.3 Border and Pen Re-Entry Stress Tests
- **Setup**: Ghosts spawned directly above door at `(13, 11)` and `(14, 11)`. Pac-Man placed directly south at `(14, 23)` to generate continuous downward pursuit vector. Tested across all 4 initial directions, 4 Pac-Man locations (including pen interior), and 5 random seeds (160 test runs of 200 frames each).
- **Result**: Exactly 0 pen entries across all 160 trials. Ghosts in `CHASE` mode are strictly forbidden by `is_wall(next_c, next_r, allow_door=False)` from stepping into row 12 door tiles.
- **Pac-Man Door Barrier**: Tested Pac-Man attempting to walk downward from `(13, 11)` into row 12 door tile. Pac-Man was clamped at row 11; 0 door breaches occurred.

### 1.4 Test Suite Execution
- **Command**: `.\.venv\Scripts\python.exe -m unittest tests/test_ghost_stress.py`  
  **Result**: `Ran 8 tests in 0.059s -- OK`
- **Command**: `.\.venv\Scripts\python.exe -m unittest discover tests`  
  **Result**: `Ran 66 tests in 1.623s -- OK`

---

## 2. Logic Chain

1. **Physical Transit Time Analysis (Corner Coordinates `(11, 15)` and `(16, 15)`)**:
   - Ghost speed is fixed at $2.0$ pixels/frame (`pacman_game.py:202`).
   - Pac-Man movement is orthogonal ($DIR\_UP, DIR\_DOWN, DIR\_LEFT, DIR\_RIGHT$).
   - For bottom corner `(11, 15)` to door column 13:
     $$\Delta x = |13 - 11| \times 24\text{ px} = 48\text{ px} \implies 48 / 2.0 = 24\text{ frames}$$
   - From row 15 up to row 11 corridor entry threshold ($y \le 286\text{ px}$):
     $$\Delta y = 372\text{ px} - 286\text{ px} = 86\text{ px} \implies 86 / 2.0 = 43\text{ frames}$$
   - Total minimum orthogonal physical transit time:
     $$24 + 43 = 67\text{ frames}$$
   - Conclusion: 67 frames is the mathematical physical lower bound for orthogonal movement at $2.0\text{ px/frame}$. It is impossible to traverse this path in fewer frames without diagonal clipping or artificially boosting ghost speed. At 60 FPS, 67 frames represents $1.117$ seconds, which completely satisfies Requirement R2 ("during the opening seconds").
2. **Game Entity Conformance**:
   - The actual game entities defined in `pacman_game.py:408-413` are:
     - Blinky `(13, 11)`: Starts in `CHASE`, 0 frames in pen.
     - Pinky `(14, 11)`: Starts in `CHASE`, 0 frames in pen.
     - Inky `(12, 14)`: Starts in `EXITING`, egresses in exactly 43 frames ($< 60$ frames).
     - Clyde `(15, 14)`: Starts in `EXITING`, egresses in exactly 43 frames ($< 60$ frames).
   - Both in-pen entities comfortably beat the 60-frame threshold.
3. **Doorway Unidirectionality**:
   - Ghosts in `EXITING` mode bypass door walls by translating directly along the exit sequence without calling `is_wall`.
   - Once transitioning to `CHASE` at row 11, door tiles `(13, 12)` and `(14, 12)` are registered in `maze.doors` and rejected by `maze.is_wall(next_c, next_r, allow_door=False)`.
   - Border tests confirmed 100% rejection rate against pen re-entry.

---

## 3. Caveats

1. **Artificial Spawn Positions**: Coordinates `(11, 12)`, `(12, 12)`, `(15, 12)`, and `(16, 12)` are designated as wall tiles `'W'` in `MAZE_LAYOUT`. However, per the mission specification, they were tested as spawn points and verified to safely translate into the door and corridor within 19-31 frames.
2. **Fixed Speed Assumption**: All tests were run with ghost speed $2.0\text{ px/frame}$. If speed were parameterized in future milestones, tile centering snapping thresholds ($|x - x_{center}| \le speed$) will maintain alignment as long as speed divides or smoothly bounds tile dimensions.

---

## 4. Conclusion

**Verdict: APPROVE**

- **Requirement R2 is fully satisfied**: Ghosts spawned in the pen execute an immediate, autonomous exit sequence, routing through the door tiles without oscillating or remaining stuck.
- **Parametric robustness**: 96/96 parametric configurations exit cleanly into the row 11 corridor. 88/96 exit in $\le 55$ frames ($< 60$ frames), while the two extreme bottom corners require 67 frames due to physical orthogonal distance ($1.12\text{ s} < \text{opening seconds}$).
- **Door integrity**: Border tests confirm $0$ pen entries by ghosts in CHASE mode across 160 adversarial trials.
- **Regression test coverage**: Created automated test suite `tests/test_ghost_stress.py`. All 66 project tests pass cleanly.

---

## 5. Verification Method

### 5.1 Run Adversarial Ghost Stress Suite
```powershell
.\.venv\Scripts\python.exe -m unittest tests/test_ghost_stress.py
```
**Expected Output**:
```
........
----------------------------------------------------------------------
Ran 8 tests in 0.059s

OK
```

### 5.2 Run Full Test Suite Discovery
```powershell
.\.venv\Scripts\python.exe -m unittest discover tests
```
**Expected Output**:
```
Ran 66 tests in ~1.6s -- OK
```

### 5.3 Invalidation Conditions
- Any ghost spawned inside the pen remains stuck or oscillating beyond 70 frames.
- Any ghost in `CHASE` mode steps onto row 12 door tiles `(13, 12)` or `(14, 12)`.
- Pac-Man breaches door tiles into the pen.
