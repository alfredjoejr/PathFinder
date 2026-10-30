"""
Unit and Integration Tests for Ghost AI Navigation and House Exit (R2).
Validates:
- Ghosts spawned inside the pen (Inky, Clyde) navigate out through the pen door ('=' tiles at row 12, cols 13-14).
- Ghosts do not oscillate or remain trapped at start positions upon game start.
- Blinky and Pinky (starting at row 11) do not enter the pen through the door.
- Once outside the pen, ghosts actively pursue Pac-Man through the maze corridors without returning to the pen.
- Parametric pen spawns: verify all positions inside pen bounds (cols 11-16, rows 12-15) successfully exit.
- Maze pen door collision registration and access control.
"""

import os
import sys
import unittest

# Ensure SDL uses headless dummy driver
os.environ["SDL_VIDEODRIVER"] = "dummy"

# Ensure project root is in sys.path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from pacman.pacman_game import (
    Ghost,
    Maze,
    CELL_SIZE,
    RED,
    PINK,
    CYAN,
    ORANGE,
    DIR_UP,
    DIR_DOWN,
    DIR_LEFT,
    DIR_RIGHT,
)


class TestGhostExitAI(unittest.TestCase):
    """Test suite validating ghost house exit, corridor pursuit, and non-oscillation."""

    def setUp(self):
        self.maze = Maze()
        # Pac-Man standard spawn position (col=14, row=23)
        self.pacman_pos = (14 * CELL_SIZE + CELL_SIZE / 2.0, 23 * CELL_SIZE + CELL_SIZE / 2.0)
        self.door_tiles = {(13, 12), (14, 12)}
        self.pen_tiles = {
            (c, r) for c in range(11, 17) for r in range(13, 16)
        }

    def simulate_ghost(self, ghost, max_ticks=300):
        """Simulate ghost movement headlessly for max_ticks and record tile path."""
        path = []
        for _ in range(max_ticks):
            ghost.update(self.maze, self.pacman_pos)
            col = int(round((ghost.x - CELL_SIZE / 2.0) / CELL_SIZE))
            row = int(round((ghost.y - CELL_SIZE / 2.0) / CELL_SIZE))
            path.append((col, row))
        return path

    def test_door_collision_registration(self):
        """Verify maze registers door tiles and blocks entry when allow_door=False."""
        self.assertEqual(self.maze.doors, self.door_tiles)
        for tile in self.door_tiles:
            self.assertTrue(
                self.maze.is_wall(tile[0], tile[1], allow_door=False),
                f"Door tile {tile} must act as a wall when allow_door=False."
            )
            self.assertFalse(
                self.maze.is_wall(tile[0], tile[1], allow_door=True),
                f"Door tile {tile} must be passable when allow_door=True."
            )

    def test_inky_exits_pen_through_door(self):
        """Inky (col=12, row=14) must pass through door and exit pen into corridor row <= 11."""
        ghost = Ghost(col=12, row=14, color=CYAN, name="Inky", initial_dir=DIR_LEFT)
        self.assertEqual(ghost.state, "EXITING", "Inky should initialize in EXITING state.")

        path = []
        exited_tick = None
        for tick in range(1, 301):
            ghost.update(self.maze, self.pacman_pos)
            col = int(round((ghost.x - CELL_SIZE / 2.0) / CELL_SIZE))
            row = int(round((ghost.y - CELL_SIZE / 2.0) / CELL_SIZE))
            path.append((col, row))
            if ghost.state == "CHASE" and exited_tick is None:
                exited_tick = tick

        door_passed = any(tile in self.door_tiles for tile in path)
        exited = any(r <= 11 for c, r in path)

        self.assertTrue(door_passed, f"Inky must pass through door tiles {self.door_tiles}.")
        self.assertTrue(exited, "Inky must reach corridor row <= 11 outside pen.")
        self.assertEqual(ghost.state, "CHASE", "Inky must transition to CHASE state.")
        self.assertIsNotNone(exited_tick)
        self.assertLessEqual(exited_tick, 60, f"Inky must exit quickly; took {exited_tick} ticks.")

    def test_clyde_exits_pen_through_door(self):
        """Clyde (col=15, row=14) must pass through door and exit pen into corridor row <= 11."""
        ghost = Ghost(col=15, row=14, color=ORANGE, name="Clyde", initial_dir=DIR_RIGHT)
        self.assertEqual(ghost.state, "EXITING", "Clyde should initialize in EXITING state.")

        path = []
        exited_tick = None
        for tick in range(1, 301):
            ghost.update(self.maze, self.pacman_pos)
            col = int(round((ghost.x - CELL_SIZE / 2.0) / CELL_SIZE))
            row = int(round((ghost.y - CELL_SIZE / 2.0) / CELL_SIZE))
            path.append((col, row))
            if ghost.state == "CHASE" and exited_tick is None:
                exited_tick = tick

        door_passed = any(tile in self.door_tiles for tile in path)
        exited = any(r <= 11 for c, r in path)

        self.assertTrue(door_passed, f"Clyde must pass through door tiles {self.door_tiles}.")
        self.assertTrue(exited, "Clyde must reach corridor row <= 11 outside pen.")
        self.assertEqual(ghost.state, "CHASE", "Clyde must transition to CHASE state.")
        self.assertIsNotNone(exited_tick)
        self.assertLessEqual(exited_tick, 60, f"Clyde must exit quickly; took {exited_tick} ticks.")

    def test_blinky_and_pinky_do_not_enter_pen(self):
        """Blinky and Pinky starting outside (row 11) must not enter the pen through the door."""
        blinky = Ghost(col=13, row=11, color=RED, name="Blinky", initial_dir=DIR_LEFT)
        pinky = Ghost(col=14, row=11, color=PINK, name="Pinky", initial_dir=DIR_RIGHT)

        self.assertEqual(blinky.state, "CHASE", "Blinky should initialize in CHASE state.")
        self.assertEqual(pinky.state, "CHASE", "Pinky should initialize in CHASE state.")

        b_path = self.simulate_ghost(blinky, max_ticks=300)
        p_path = self.simulate_ghost(pinky, max_ticks=300)

        # Neither ghost should ever step onto door tiles or enter pen interior
        for tile in b_path:
            self.assertNotIn(
                tile,
                self.door_tiles,
                f"Blinky must not pass through door tiles: visited {tile}"
            )
            self.assertNotIn(
                tile,
                self.pen_tiles,
                f"Blinky must not enter pen interior: visited {tile}"
            )

        for tile in p_path:
            self.assertNotIn(
                tile,
                self.door_tiles,
                f"Pinky must not pass through door tiles: visited {tile}"
            )
            self.assertNotIn(
                tile,
                self.pen_tiles,
                f"Pinky must not enter pen interior: visited {tile}"
            )

    def test_no_start_oscillation_and_diverse_corridor_exploration(self):
        """Ghosts must not oscillate or remain trapped at start positions upon game start."""
        inky = Ghost(col=12, row=14, color=CYAN, name="Inky", initial_dir=DIR_LEFT)
        clyde = Ghost(col=15, row=14, color=ORANGE, name="Clyde", initial_dir=DIR_RIGHT)

        # In first 60 ticks, ghosts must leave starting tile and reach corridor
        inky_path_early = self.simulate_ghost(inky, max_ticks=60)
        self.assertNotEqual(
            inky_path_early[-1], (12, 14),
            "Inky must not remain at starting tile after 60 ticks."
        )

        clyde_path_early = self.simulate_ghost(clyde, max_ticks=60)
        self.assertNotEqual(
            clyde_path_early[-1], (15, 14),
            "Clyde must not remain at starting tile after 60 ticks."
        )

        # Over 300 ticks, ghosts must explore a diverse set of maze corridor tiles
        inky.reset()
        inky_path_full = self.simulate_ghost(inky, max_ticks=300)
        unique_tiles_inky = set(inky_path_full)
        self.assertGreaterEqual(
            len(unique_tiles_inky), 10,
            f"Inky must explore diverse corridor tiles without oscillating, visited: {len(unique_tiles_inky)}"
        )

        clyde.reset()
        clyde_path_full = self.simulate_ghost(clyde, max_ticks=300)
        unique_tiles_clyde = set(clyde_path_full)
        self.assertGreaterEqual(
            len(unique_tiles_clyde), 10,
            f"Clyde must explore diverse corridor tiles without oscillating, visited: {len(unique_tiles_clyde)}"
        )

    def test_active_pursuit_outside_pen_no_pen_reentry(self):
        """Once outside the pen, ghosts actively navigate corridors without returning to the pen."""
        ghost = Ghost(col=12, row=14, color=CYAN, name="Inky", initial_dir=DIR_LEFT)

        # Step until exit
        while ghost.state == "EXITING":
            ghost.update(self.maze, self.pacman_pos)

        self.assertEqual(ghost.state, "CHASE")

        # Simulate subsequent 400 ticks of pursuit
        post_exit_path = []
        for _ in range(400):
            ghost.update(self.maze, self.pacman_pos)
            col = int(round((ghost.x - CELL_SIZE / 2.0) / CELL_SIZE))
            row = int(round((ghost.y - CELL_SIZE / 2.0) / CELL_SIZE))
            post_exit_path.append((col, row))

        # Must never re-enter pen tiles
        for tile in post_exit_path:
            self.assertNotIn(
                tile,
                self.pen_tiles,
                f"Ghost re-entered pen interior at tile {tile} during active pursuit."
            )
            self.assertNotIn(
                tile,
                self.door_tiles,
                f"Ghost stepped onto door tile {tile} during active pursuit."
            )

    def test_parametric_pen_spawns(self):
        """Parametric verification: all positions inside pen bounds (cols 11-16, rows 12-15) successfully exit."""
        for c in range(11, 17):
            for r in range(12, 16):
                with self.subTest(col=c, row=r):
                    ghost = Ghost(col=c, row=r, color=CYAN, name=f"Ghost_{c}_{r}")
                    self.assertEqual(
                        ghost.state, "EXITING",
                        f"Ghost at ({c}, {r}) should start in EXITING state."
                    )

                    exited = False
                    for _ in range(100):
                        ghost.update(self.maze, self.pacman_pos)
                        if ghost.state == "CHASE":
                            cur_c = int(round((ghost.x - CELL_SIZE / 2.0) / CELL_SIZE))
                            cur_r = int(round((ghost.y - CELL_SIZE / 2.0) / CELL_SIZE))
                            self.assertLessEqual(cur_r, 11)
                            self.assertIn(cur_c, (13, 14))
                            exited = True
                            break

                    self.assertTrue(exited, f"Ghost starting at ({c}, {r}) failed to exit pen.")


if __name__ == "__main__":
    unittest.main()
