# BRIEFING — 2026-10-30T15:08:45Z

## Mission
Investigate ghost house exit and navigation AI in `pacman/pacman_game.py` to diagnose why ghosts oscillate/remain stuck in pen and design an active exit sequence and smooth pursuit transition.

## 🔒 My Identity
- Archetype: teamwork_explorer
- Roles: survey_explorer_2, read-only investigation and synthesis
- Working directory: c:\Users\joash\OneDrive\Documents\Github\PathFinder\.agents\teamwork\survey_explorer_2
- Original parent: e69ff21d-c68b-4dc5-8b54-914987353bcd
- Milestone: ghost_ai_investigation

## 🔒 Key Constraints
- Read-only investigation — do NOT implement
- Output strictly in .agents/teamwork/survey_explorer_2/
- Follow 5-component handoff report structure
- Communicate back to parent via send_message

## Current Parent
- Conversation ID: e69ff21d-c68b-4dc5-8b54-914987353bcd
- Updated: 2026-10-30T15:07:57Z (Parent pinged for status)

## Investigation State
- **Explored paths**: `pacman/pacman_game.py`, `pacman/pacman_runner.py`, `main.py`, `.agents/teamwork/ORIGINAL_REQUEST.md`
- **Key findings**:
  1. Door '=' at (13,12) and (14,12) is omitted from `Maze.walls`, making it bidirectionally transparent to greedy Euclidean targeting.
  2. Blinky (13,11) and Pinky (14,11) start outside but immediately dive DOWN into the ghost house because Pac-Man is below at row 23.
  3. Inside the pen (rows 13-15, cols 11-16), moving UP towards the door increases distance to Pac-Man, trapping all ghosts in a closed deterministic orbit along the bottom of the pen.
  4. Frame-1 tile-center snapping causes instant direction flip, discarding initial direction.
  5. Implemented simulation proving a 2-segment vector exit state machine exits all 18 pen spawn locations in <100 frames and achieves smooth pursuit in ~200-265 frames without oscillations.
- **Unexplored areas**: None. Investigation complete.

## Key Decisions Made
- Confirmed root cause mathematically and with frame-by-frame simulation.
- Designed 2-state (`EXITING` -> `CHASE`) architecture where '=' is treated as a wall in CHASE mode and for Pac-Man, and used as exit gateway in EXITING mode.

## Artifact Index
- DISPATCH.md — record of initial dispatch and parent status check
- progress.md — liveness and progress tracking
- handoff.md — comprehensive 5-component handoff report
