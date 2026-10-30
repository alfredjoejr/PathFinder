"""
Comprehensive Adversarial Stress and Robustness Test Suite for Pac-Man Ghost AI.

Validates:
1. Pen exit sequence (all 24 pen tiles, <60 frames exit, door collision blocking).
2. Long-duration simulation (1200+ frames / 20+ seconds) with pen non-re-entry,
   strict oscillation prevention (no 2-tile cycling, >30 unique tiles in 600f),
   and Pac-Man interception.
3. Dynamic target pursuit (moving Pac-Man, 4 corners, pen-adjacent corridors).
4. Tunnel wrap navigation (row 14 left and right screen borders, wrap pursuit, multi-seed stress).
5. Scared mode and post-eaten reset egress cycles.
"""

import math
import os
import random
import unittest
from collections import defaultdict

os.environ["SDL_VIDEODRIVER"] = "dummy"

from pacman.pacman_game import (
    Maze,
    Ghost,
    Pacman,
    CELL_SIZE,
    SCREEN_WIDTH,
    DIR_UP,
    DIR_DOWN,
    DIR_LEFT,
    DIR_RIGHT,
    DIR_NONE,
)


class TestPenExitAndBounds(unittest.TestCase):
    """Stress tests on ghost house pen exit and boundary enforcement."""

    def setUp(self):
        self.maze = Maze()
        self.pacman = Pacman(14, 23)

    def test_default_ghosts_initial_states(self):
        """Verify initial state machine states for default ghost setup."""
        blinky = Ghost(col=13, row=11, color=(255, 0, 0), name="Blinky", initial_dir=DIR_LEFT)
        pinky = Ghost(col=14, row=11, color=(255, 183, 255), name="Pinky", initial_dir=DIR_RIGHT)
        inky = Ghost(col=12, row=14, color=(0, 255, 255), name="Inky", initial_dir=DIR_LEFT)
        clyde = Ghost(col=15, row=14, color=(255, 183, 81), name="Clyde", initial_dir=DIR_RIGHT)

        self.assertEqual(blinky.state, "CHASE")
        self.assertEqual(pinky.state, "CHASE")
        self.assertEqual(inky.state, "EXITING")
        self.assertEqual(clyde.state, "EXITING")

    def test_inky_and_clyde_exit_under_60_frames(self):
        """Inky and Clyde must ascend out through door and reach row 11 in <60 frames."""
        inky = Ghost(col=12, row=14, color=(0, 255, 255), name="Inky", initial_dir=DIR_LEFT)
        clyde = Ghost(col=15, row=14, color=(255, 183, 81), name="Clyde", initial_dir=DIR_RIGHT)

        inky_exit_frame = None
        clyde_exit_frame = None

        for frame in range(1, 61):
            if inky.state == "EXITING":
                inky.update(self.maze, (self.pacman.x, self.pacman.y))
                if inky.state == "CHASE":
                    inky_exit_frame = frame
            if clyde.state == "EXITING":
                clyde.update(self.maze, (self.pacman.x, self.pacman.y))
                if clyde.state == "CHASE":
                    clyde_exit_frame = frame

        self.assertIsNotNone(inky_exit_frame, "Inky did not exit pen within 60 frames")
        self.assertIsNotNone(clyde_exit_frame, "Clyde did not exit pen within 60 frames")
        self.assertLessEqual(inky_exit_frame, 50, f"Inky took {inky_exit_frame} frames")
        self.assertLessEqual(clyde_exit_frame, 50, f"Clyde took {clyde_exit_frame} frames")

        # Confirm coordinates outside pen at row 11
        for g in [inky, clyde]:
            cur_r = int(round((g.y - CELL_SIZE / 2.0) / CELL_SIZE))
            self.assertLessEqual(cur_r, 11)

    def test_all_24_pen_tiles_egress(self):
        """Exhaustively verify active egress from every tile in pen (cols 11-16, rows 12-15)."""
        for c in range(11, 17):
            for r in range(12, 16):
                with self.subTest(start_col=c, start_row=r):
                    ghost = Ghost(col=c, row=r, color=(200, 200, 200), name=f"Ghost_{c}_{r}")
                    self.assertEqual(ghost.state, "EXITING")
                    exited = False
                    for frame in range(100):
                        ghost.update(self.maze, (self.pacman.x, self.pacman.y))
                        if ghost.state == "CHASE":
                            cur_c = int(round((ghost.x - CELL_SIZE / 2.0) / CELL_SIZE))
                            cur_r = int(round((ghost.y - CELL_SIZE / 2.0) / CELL_SIZE))
                            self.assertLessEqual(cur_r, 11)
                            self.assertIn(cur_c, (13, 14))
                            exited = True
                            break
                    self.assertTrue(exited, f"Ghost failed to exit pen from ({c}, {r})")

    def test_pacman_blocked_by_doors(self):
        """Verify Pac-Man cannot enter pen through doors at row 12."""
        for door_c in (13, 14):
            with self.subTest(door_c=door_c):
                p = Pacman(col=door_c, row=11)
                p.set_direction(DIR_DOWN)
                for _ in range(30):
                    p.update(self.maze)
                cur_r = int(round((p.y - CELL_SIZE / 2.0) / CELL_SIZE))
                self.assertEqual(cur_r, 11, f"Pacman bypassed door at col {door_c} into row {cur_r}")


class TestLongDurationSimulation(unittest.TestCase):
    """Long-duration simulation (1200+ frames) asserting non-oscillation, non-reentry, and pursuit."""

    def test_1200_frames_stationary_target(self):
        """1200 frames with stationary Pacman at (14, 23)."""
        random.seed(1337)
        maze = Maze()
        pacman = Pacman(14, 23)
        ghosts = [
            Ghost(col=13, row=11, color=(255, 0, 0), name="Blinky", initial_dir=DIR_LEFT),
            Ghost(col=14, row=11, color=(255, 183, 255), name="Pinky", initial_dir=DIR_RIGHT),
            Ghost(col=12, row=14, color=(0, 255, 255), name="Inky", initial_dir=DIR_LEFT),
            Ghost(col=15, row=14, color=(255, 183, 81), name="Clyde", initial_dir=DIR_RIGHT),
        ]

        pen_entries = defaultdict(int)
        visited_600 = defaultdict(set)
        visited_1200 = defaultdict(set)
        recent_tiles = defaultdict(list)
        two_tile_oscillations = defaultdict(int)
        intercepts = defaultdict(int)

        for frame in range(1200):
            for g in ghosts:
                g.update(maze, (pacman.x, pacman.y))
                c = int(round((g.x - CELL_SIZE / 2.0) / CELL_SIZE))
                r = int(round((g.y - CELL_SIZE / 2.0) / CELL_SIZE))

                if frame >= 60:
                    if 11 <= c <= 16 and 12 <= r <= 15:
                        pen_entries[g.name] += 1

                if frame < 600:
                    visited_600[g.name].add((c, r))
                visited_1200[g.name].add((c, r))

                # Track tile history for 2-tile oscillations
                hist = recent_tiles[g.name]
                if not hist or hist[-1] != (c, r):
                    hist.append((c, r))
                    if len(hist) >= 4 and hist[-1] == hist[-3] and hist[-2] == hist[-4] and hist[-1] != hist[-2]:
                        two_tile_oscillations[g.name] += 1

                dist = math.hypot(pacman.x - g.x, pacman.y - g.y)
                if dist < (pacman.radius + g.radius):
                    intercepts[g.name] += 1

        for g in ghosts:
            with self.subTest(ghost=g.name):
                # 1. No pen re-entry
                self.assertEqual(pen_entries[g.name], 0, f"{g.name} re-entered the ghost pen!")
                # 2. Strict tile diversity (>30 unique tiles over 600 frames)
                self.assertGreater(
                    len(visited_600[g.name]), 30,
                    f"{g.name} tile diversity too low over 600 frames: {len(visited_600[g.name])}"
                )
                self.assertGreater(
                    len(visited_1200[g.name]), 40,
                    f"{g.name} tile diversity too low over 1200 frames: {len(visited_1200[g.name])}"
                )
                # 3. No 2-tile oscillation loops
                self.assertEqual(
                    two_tile_oscillations[g.name], 0,
                    f"{g.name} engaged in 2-tile oscillation {two_tile_oscillations[g.name]} times!"
                )
                # 4. Intercepted Pac-Man
                self.assertGreater(
                    intercepts[g.name], 0,
                    f"{g.name} failed to intercept stationary Pac-Man"
                )


class TestDynamicTargetTesting(unittest.TestCase):
    """Dynamic target tests: moving Pac-Man, corners, and pen perimeter."""

    def test_dynamic_moving_pacman_chase(self):
        """Ghosts must chase, intercept, and maintain diversity with moving Pac-Man."""
        random.seed(2026)
        maze = Maze()
        pacman = Pacman(14, 23)
        ghosts = [
            Ghost(col=13, row=11, color=(255, 0, 0), name="Blinky", initial_dir=DIR_LEFT),
            Ghost(col=14, row=11, color=(255, 183, 255), name="Pinky", initial_dir=DIR_RIGHT),
            Ghost(col=12, row=14, color=(0, 255, 255), name="Inky", initial_dir=DIR_LEFT),
            Ghost(col=15, row=14, color=(255, 183, 81), name="Clyde", initial_dir=DIR_RIGHT),
        ]
        pacman.set_direction(DIR_LEFT)

        pen_entries = defaultdict(int)
        visited = defaultdict(set)
        intercept_frames = 0

        for frame in range(1200):
            # Pacman autopilot turns at intersections
            pc = int(round((pacman.x - CELL_SIZE / 2.0) / CELL_SIZE))
            pr = int(round((pacman.y - CELL_SIZE / 2.0) / CELL_SIZE))
            pac_cx = pc * CELL_SIZE + CELL_SIZE / 2.0
            pac_cy = pr * CELL_SIZE + CELL_SIZE / 2.0
            if abs(pacman.x - pac_cx) <= pacman.speed and abs(pacman.y - pac_cy) <= pacman.speed:
                valid_dirs = []
                for d in [DIR_UP, DIR_DOWN, DIR_LEFT, DIR_RIGHT]:
                    if (d[0] == -pacman.dir[0] and d[0] != 0) or (d[1] == -pacman.dir[1] and d[1] != 0):
                        continue
                    if not maze.is_wall(pc + d[0], pr + d[1]):
                        valid_dirs.append(d)
                if valid_dirs:
                    pacman.set_direction(random.choice(valid_dirs))
                elif not maze.is_wall(pc - pacman.dir[0], pr - pacman.dir[1]):
                    pacman.set_direction((-pacman.dir[0], -pacman.dir[1]))

            pacman.update(maze)

            for g in ghosts:
                g.update(maze, (pacman.x, pacman.y))
                gc = int(round((g.x - CELL_SIZE / 2.0) / CELL_SIZE))
                gr = int(round((g.y - CELL_SIZE / 2.0) / CELL_SIZE))
                if frame >= 60 and (11 <= gc <= 16 and 12 <= gr <= 15):
                    pen_entries[g.name] += 1
                visited[g.name].add((gc, gr))
                dist = math.hypot(pacman.x - g.x, pacman.y - g.y)
                if dist < (pacman.radius + g.radius):
                    intercept_frames += 1

        self.assertGreater(intercept_frames, 50, "Insufficient intercepts against moving Pac-Man")
        for g in ghosts:
            with self.subTest(ghost=g.name):
                self.assertEqual(pen_entries[g.name], 0, f"{g.name} entered pen during pursuit")
                self.assertGreater(len(visited[g.name]), 50, f"{g.name} visited too few tiles")

    def test_corner_targets_pursuit(self):
        """Verify ghosts actively pursue Pac-Man parked in all 4 extreme corners."""
        corners = [(1, 1), (26, 1), (1, 29), (26, 29)]
        for corner_col, corner_row in corners:
            with self.subTest(corner=(corner_col, corner_row)):
                random.seed(42)
                maze = Maze()
                pacman = Pacman(corner_col, corner_row)
                ghosts = [
                    Ghost(col=13, row=11, color=(255, 0, 0), name="Blinky"),
                    Ghost(col=14, row=11, color=(255, 183, 255), name="Pinky"),
                    Ghost(col=12, row=14, color=(0, 255, 255), name="Inky"),
                    Ghost(col=15, row=14, color=(255, 183, 81), name="Clyde"),
                ]

                intercepted = False
                for frame in range(1000):
                    for g in ghosts:
                        g.update(maze, (pacman.x, pacman.y))
                        gc = int(round((g.x - CELL_SIZE / 2.0) / CELL_SIZE))
                        gr = int(round((g.y - CELL_SIZE / 2.0) / CELL_SIZE))
                        if frame >= 60:
                            self.assertFalse(
                                11 <= gc <= 16 and 12 <= gr <= 15,
                                f"{g.name} entered pen while pursuing corner {corner_col},{corner_row}"
                            )
                        dist = math.hypot(pacman.x - g.x, pacman.y - g.y)
                        if dist < (pacman.radius + g.radius):
                            intercepted = True
                            break
                    if intercepted:
                        break
                self.assertTrue(intercepted, f"Failed to intercept Pac-Man at corner ({corner_col}, {corner_row})")

    def test_pen_adjacent_walkable_targets(self):
        """Verify ghosts pursue Pac-Man stationed adjacent to pen doors and walls without pen penetration."""
        adjacent_positions = [(13, 11), (14, 11), (13, 17), (14, 17), (9, 14), (18, 14)]
        for target_c, target_r in adjacent_positions:
            with self.subTest(target=(target_c, target_r)):
                random.seed(42)
                maze = Maze()
                pacman = Pacman(target_c, target_r)
                ghosts = [
                    Ghost(col=13, row=11, color=(255, 0, 0), name="Blinky"),
                    Ghost(col=14, row=11, color=(255, 183, 255), name="Pinky"),
                    Ghost(col=12, row=14, color=(0, 255, 255), name="Inky"),
                    Ghost(col=15, row=14, color=(255, 183, 81), name="Clyde"),
                ]

                intercepted = False
                for frame in range(600):
                    for g in ghosts:
                        g.update(maze, (pacman.x, pacman.y))
                        gc = int(round((g.x - CELL_SIZE / 2.0) / CELL_SIZE))
                        gr = int(round((g.y - CELL_SIZE / 2.0) / CELL_SIZE))
                        if frame >= 60:
                            self.assertFalse(
                                11 <= gc <= 16 and 12 <= gr <= 15,
                                f"{g.name} entered pen while pursuing adjacent target ({target_c}, {target_r})"
                            )
                        dist = math.hypot(pacman.x - g.x, pacman.y - g.y)
                        if dist < (pacman.radius + g.radius):
                            intercepted = True
                self.assertTrue(intercepted, f"Failed to intercept at ({target_c}, {target_r})")


class TestTunnelWrapNavigation(unittest.TestCase):
    """Stress tests on side tunnel wrapping at row 14."""

    def setUp(self):
        self.maze = Maze()

    def test_left_to_right_wrap(self):
        """Ghost moving LEFT through tunnel wraps from left edge to right edge."""
        pacman = Pacman(col=26, row=14)
        ghost = Ghost(col=2, row=14, color=(255, 0, 0), name="Blinky", initial_dir=DIR_LEFT)
        ghost.state = "CHASE"
        ghost.x = 2 * CELL_SIZE + CELL_SIZE / 2.0
        ghost.y = 14 * CELL_SIZE + CELL_SIZE / 2.0
        ghost.dir = DIR_LEFT
        ghost._last_tile = (2, 14)

        wrapped = False
        for frame in range(120):
            ghost.update(self.maze, (pacman.x, pacman.y))
            gc = int(round((ghost.x - CELL_SIZE / 2.0) / CELL_SIZE))
            if ghost.x > SCREEN_WIDTH - CELL_SIZE and gc >= 25:
                wrapped = True
                break
        self.assertTrue(wrapped, f"Ghost failed to wrap left-to-right (x={ghost.x})")

    def test_right_to_left_wrap(self):
        """Ghost moving RIGHT through tunnel wraps from right edge to left edge."""
        pacman = Pacman(col=1, row=14)
        ghost = Ghost(col=25, row=14, color=(255, 183, 255), name="Pinky", initial_dir=DIR_RIGHT)
        ghost.state = "CHASE"
        ghost.x = 25 * CELL_SIZE + CELL_SIZE / 2.0
        ghost.y = 14 * CELL_SIZE + CELL_SIZE / 2.0
        ghost.dir = DIR_RIGHT
        ghost._last_tile = (25, 14)

        wrapped = False
        for frame in range(120):
            ghost.update(self.maze, (pacman.x, pacman.y))
            gc = int(round((ghost.x - CELL_SIZE / 2.0) / CELL_SIZE))
            if ghost.x < CELL_SIZE and gc <= 2:
                wrapped = True
                break
        self.assertTrue(wrapped, f"Ghost failed to wrap right-to-left (x={ghost.x})")

    def test_multi_seed_tunnel_reentry_stress(self):
        """Across 50 random seeds, ghosts traversing tunnel never get stuck outside bounds."""
        for seed in range(50):
            random.seed(seed)
            ghost = Ghost(col=27, row=14, color=(255, 0, 0), name="Blinky", initial_dir=DIR_RIGHT)
            ghost.state = "CHASE"
            ghost.x = 27 * CELL_SIZE + CELL_SIZE / 2.0
            ghost.y = 14 * CELL_SIZE + CELL_SIZE / 2.0
            ghost.dir = DIR_RIGHT
            ghost._last_tile = (27, 14)

            pacman = Pacman(14, 23)
            reentered = False
            for frame in range(150):
                ghost.update(self.maze, (pacman.x, pacman.y))
                gc = int(round((ghost.x - CELL_SIZE / 2.0) / CELL_SIZE))
                gr = int(round((ghost.y - CELL_SIZE / 2.0) / CELL_SIZE))
                if 0 <= gc < 28 and not self.maze.is_wall(gc, gr):
                    if frame > 25:
                        reentered = True
                        break
            self.assertTrue(reentered, f"Ghost stuck outside bounds under seed {seed}")


class TestScaredModeAndResetDynamics(unittest.TestCase):
    """Stress tests on scared behavior and post-eaten reset re-egress."""

    def test_scared_mode_pen_blocking(self):
        """Ghosts in scared mode (random wandering) must never enter the pen."""
        random.seed(777)
        maze = Maze()
        pacman = Pacman(14, 23)
        ghosts = [
            Ghost(col=13, row=11, color=(255, 0, 0), name="Blinky"),
            Ghost(col=14, row=11, color=(255, 183, 255), name="Pinky"),
            Ghost(col=12, row=14, color=(0, 255, 255), name="Inky"),
            Ghost(col=15, row=14, color=(255, 183, 81), name="Clyde"),
        ]

        for g in ghosts:
            g.scared = True
            g.scared_timer = 999999

        for frame in range(600):
            for g in ghosts:
                g.update(maze, (pacman.x, pacman.y))
                gc = int(round((g.x - CELL_SIZE / 2.0) / CELL_SIZE))
                gr = int(round((g.y - CELL_SIZE / 2.0) / CELL_SIZE))
                if frame >= 60:
                    self.assertFalse(
                        11 <= gc <= 16 and 12 <= gr <= 15,
                        f"{g.name} entered pen in scared mode at frame {frame}"
                    )

    def test_repeated_eaten_and_reset_cycles(self):
        """When ghosts are eaten and reset(), pen ghosts must re-exit reliably multiple times."""
        maze = Maze()
        pacman = Pacman(14, 23)
        inky = Ghost(col=12, row=14, color=(0, 255, 255), name="Inky", initial_dir=DIR_LEFT)

        for cycle in range(5):
            inky.reset()
            self.assertEqual(inky.state, "EXITING")
            exited = False
            for frame in range(60):
                inky.update(maze, (pacman.x, pacman.y))
                if inky.state == "CHASE":
                    cur_r = int(round((inky.y - CELL_SIZE / 2.0) / CELL_SIZE))
                    self.assertLessEqual(cur_r, 11)
                    exited = True
                    break
            self.assertTrue(exited, f"Inky failed to re-exit pen on cycle {cycle}")


if __name__ == "__main__":
    unittest.main()
