"""
Unit and Integration Tests for Launcher Auto Mode Submenu (R1).
Validates:
- Auto Mode submenu options ("In-Computer Game" and "External Computer").
- Selecting "In-Computer Game" launches pacman_game.py with ["--auto"] and
  pacman_runner.py with ["--capture-mode", "screen"].
- Selecting "External Computer" launches pacman_runner.py with ["--capture-mode", "camera"].
- Backward compatibility for run_pacman_auto(mode).
- GUI Menu invoke actions.
- Runner CLI argument parsing and vision engine screen capture mode.
"""

import os
import sys
import unittest
from unittest.mock import patch, MagicMock
import tkinter as tk

# Ensure project root is in sys.path for direct script execution and test discovery
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from main import AILauncher
import pacman.pacman_runner as runner


class TestLauncher(unittest.TestCase):
    """Test suite for PathFinder Control Center Launcher Auto Mode submenus."""

    @classmethod
    def setUpClass(cls):
        cls.root = tk.Tk()
        cls.root.withdraw()

    @classmethod
    def tearDownClass(cls):
        try:
            cls.root.destroy()
        except Exception:
            pass

    def setUp(self):
        self.app = AILauncher(self.root)

    def test_launcher_menu_attributes(self):
        """Verify Auto Mode Menubutton and its attached Menu with R1 entries."""
        self.assertIsInstance(self.app.btn_pacman_auto, tk.Menubutton)
        self.assertIsInstance(self.app.pacman_auto_menu, tk.Menu)
        self.assertIs(self.app.auto_menu, self.app.pacman_auto_menu)

        menu = self.app.pacman_auto_menu
        entry_count = menu.index("end") + 1 if menu.index("end") is not None else 0
        self.assertEqual(entry_count, 2, "Menu should contain exactly 2 entries.")

        self.assertEqual(menu.entrycget(0, "label"), "In-Computer Game")
        self.assertEqual(menu.entrycget(1, "label"), "External Computer")

    @patch("subprocess.Popen")
    def test_in_computer_game_launch(self, mock_popen):
        """Verify In-Computer Game launch runs both pacman_game (--auto) and runner (--capture-mode screen)."""
        m_game = MagicMock()
        m_run = MagicMock()
        mock_popen.side_effect = [m_game, m_run]

        p1, p2 = self.app.run_pacman_auto_in_computer()
        self.assertIs(p1, m_game)
        self.assertIs(p2, m_run)
        self.assertEqual(mock_popen.call_count, 2)

        call1 = mock_popen.call_args_list[0]
        self.assertIn("pacman_game.py", call1[0][0][1])
        self.assertIn("--auto", call1[0][0])
        self.assertEqual(call1[1]["cwd"], self.app.pacman_dir)

        call2 = mock_popen.call_args_list[1]
        self.assertIn("pacman_runner.py", call2[0][0][1])
        self.assertIn("--capture-mode", call2[0][0])
        self.assertIn("screen", call2[0][0])
        self.assertEqual(call2[1]["cwd"], self.app.pacman_dir)
        self.assertEqual(self.app.status_var.get(), "Pac-Man Game & Runner (In-Computer) launched.")

    @patch("subprocess.Popen")
    def test_external_computer_launch(self, mock_popen):
        """Verify External Computer launch runs runner (--capture-mode camera)."""
        m_run = MagicMock()
        mock_popen.return_value = m_run

        p = self.app.run_pacman_auto_external()
        self.assertIs(p, m_run)
        self.assertEqual(mock_popen.call_count, 1)

        call = mock_popen.call_args_list[0]
        self.assertIn("pacman_runner.py", call[0][0][1])
        self.assertIn("--capture-mode", call[0][0])
        self.assertIn("camera", call[0][0])
        self.assertEqual(call[1]["cwd"], self.app.pacman_dir)
        self.assertEqual(self.app.status_var.get(), "Pac-Man Runner (External Camera) launched.")

    @patch("subprocess.Popen")
    def test_menu_invoke_commands(self, mock_popen):
        """Verify menu items 0 and 1 invoke the expected commands via auto_menu.invoke()."""
        mock_popen.return_value = MagicMock()

        self.app.auto_menu.invoke(0)
        self.assertEqual(mock_popen.call_count, 2)

        mock_popen.reset_mock()
        self.app.auto_menu.invoke(1)
        self.assertEqual(mock_popen.call_count, 1)

    @patch("subprocess.Popen")
    def test_run_pacman_auto_backward_compatibility(self, mock_popen):
        """Verify run_pacman_auto() delegates properly based on mode argument."""
        mock_popen.return_value = MagicMock()

        # Default mode (in_computer)
        self.app.run_pacman_auto()
        self.assertEqual(mock_popen.call_count, 2)

        mock_popen.reset_mock()
        # Explicit "external" mode
        self.app.run_pacman_auto(mode="external")
        self.assertEqual(mock_popen.call_count, 1)

    @patch("subprocess.Popen")
    def test_manual_mode_launch(self, mock_popen):
        """Verify Manual Mode launch runs pacman_game.py without extra args."""
        m_game = MagicMock()
        mock_popen.return_value = m_game

        p = self.app.run_pacman_manual()
        self.assertIs(p, m_game)
        self.assertEqual(mock_popen.call_count, 1)

        call = mock_popen.call_args_list[0]
        cmd = call[0][0]
        self.assertIn("pacman_game.py", cmd[1])
        self.assertNotIn("--auto", cmd)
        self.assertEqual(call[1]["cwd"], self.app.pacman_dir)

    def test_runner_args_and_vision_screen_mode(self):
        """Verify runner parses --capture-mode screen and camera, and VisionEngine operates headless."""
        args_screen = runner.parse_args(["--capture-mode", "screen"])
        self.assertEqual(args_screen.capture_mode, "screen")

        args_camera = runner.parse_args(["--capture-mode", "camera", "--camera", "2"])
        self.assertEqual(args_camera.capture_mode, "camera")
        self.assertEqual(args_camera.camera, 2)

        engine = runner.VisionEngine(capture_mode="screen")
        self.assertTrue(engine.open_camera())
        frame = engine.grab_screen()
        self.assertIsNotNone(frame)
        self.assertEqual(len(frame.shape), 3)


if __name__ == "__main__":
    unittest.main()
