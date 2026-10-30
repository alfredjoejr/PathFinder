"""
Comprehensive Adversarial Stress Test Suite for AILauncher Auto Mode Submenu.

Covers:
1. Menu structure, entries, and invoke() methods
2. Precise Popen arguments and working directories per R1
3. Rapid sequential invocations (stress / spam resistance)
4. Edge cases: missing files, bad directories, non-string args, Popen errors
5. Live OS process spawning, polling, and termination
"""

import os
import sys
import unittest
from unittest.mock import patch, MagicMock
import tkinter as tk
import subprocess

from main import AILauncher


class BaseLauncherTestCase(unittest.TestCase):
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


class TestLauncherMenu(BaseLauncherTestCase):
    """Stress tests on the Menu and Menubutton widgets."""

    def test_menubutton_structure_and_labels(self):
        """Verify Menubutton and Menu instances and exact R1 labels."""
        self.assertIsInstance(self.app.btn_pacman_auto, tk.Menubutton)
        self.assertIsInstance(self.app.pacman_auto_menu, tk.Menu)
        self.assertIs(self.app.auto_menu, self.app.pacman_auto_menu)
        self.assertEqual(self.app.btn_pacman_auto["text"], "Auto Mode ▾")

        # Verify exact labels
        self.assertEqual(self.app.pacman_auto_menu.entrycget(0, "label"), "In-Computer Game")
        self.assertEqual(self.app.pacman_auto_menu.entrycget(1, "label"), "External Computer")

    def test_menu_entry_count(self):
        """Verify exactly 2 menu entries exist (index 0 and 1)."""
        self.assertEqual(self.app.pacman_auto_menu.index("end"), 1)

    def test_menu_invoke_0_triggers_in_computer(self):
        """Invoke menu item 0 and verify Popen launches game and runner with screen capture."""
        with patch("subprocess.Popen") as mock_popen:
            mock_popen.return_value = MagicMock()
            self.app.auto_menu.invoke(0)
            self.assertEqual(mock_popen.call_count, 2)
            call1_args = mock_popen.call_args_list[0][0][0]
            call2_args = mock_popen.call_args_list[1][0][0]
            self.assertIn("pacman_game.py", call1_args[1])
            self.assertIn("--auto", call1_args)
            self.assertIn("pacman_runner.py", call2_args[1])
            self.assertIn("screen", call2_args)

    def test_menu_invoke_1_triggers_external(self):
        """Invoke menu item 1 and verify Popen launches runner with camera capture."""
        with patch("subprocess.Popen") as mock_popen:
            mock_popen.return_value = MagicMock()
            self.app.auto_menu.invoke(1)
            self.assertEqual(mock_popen.call_count, 1)
            call_args = mock_popen.call_args_list[0][0][0]
            self.assertIn("pacman_runner.py", call_args[1])
            self.assertIn("camera", call_args)

    def test_menu_invoke_negative_index_raises_error(self):
        """Verify invoking negative menu entry index raises TclError."""
        with self.assertRaises(tk.TclError):
            self.app.auto_menu.invoke(-1)


class TestLauncherR1Compliance(BaseLauncherTestCase):
    """Verify compliance with R1 specification for launch parameters."""

    @patch("subprocess.Popen")
    def test_in_computer_game_popen_args_and_cwd(self, mock_popen):
        """Verify exact arguments, python binary, cwd, and return values for In-Computer."""
        mock_game_proc = MagicMock()
        mock_runner_proc = MagicMock()
        mock_popen.side_effect = [mock_game_proc, mock_runner_proc]

        result = self.app.run_pacman_auto_in_computer()

        self.assertIsInstance(result, tuple)
        self.assertEqual(len(result), 2)
        self.assertIs(result[0], mock_game_proc)
        self.assertIs(result[1], mock_runner_proc)

        # Call 1: Game
        c1_args, c1_kwargs = mock_popen.call_args_list[0]
        expected_game = os.path.join(self.app.pacman_dir, "pacman_game.py")
        self.assertEqual(c1_args[0], [sys.executable, expected_game, "--auto"])
        self.assertEqual(c1_kwargs["cwd"], self.app.pacman_dir)

        # Call 2: Runner
        c2_args, c2_kwargs = mock_popen.call_args_list[1]
        expected_runner = os.path.join(self.app.pacman_dir, "pacman_runner.py")
        self.assertEqual(c2_args[0], [sys.executable, expected_runner, "--capture-mode", "screen"])
        self.assertEqual(c2_kwargs["cwd"], self.app.pacman_dir)

        # Status label
        self.assertEqual(self.app.status_var.get(), "Pac-Man Game & Runner (In-Computer) launched.")

    @patch("subprocess.Popen")
    def test_external_computer_popen_args_and_cwd(self, mock_popen):
        """Verify exact arguments, python binary, cwd, and return value for External Computer."""
        mock_runner_proc = MagicMock()
        mock_popen.return_value = mock_runner_proc

        result = self.app.run_pacman_auto_external()

        self.assertIs(result, mock_runner_proc)
        self.assertEqual(mock_popen.call_count, 1)

        c_args, c_kwargs = mock_popen.call_args_list[0]
        expected_runner = os.path.join(self.app.pacman_dir, "pacman_runner.py")
        self.assertEqual(c_args[0], [sys.executable, expected_runner, "--capture-mode", "camera"])
        self.assertEqual(c_kwargs["cwd"], self.app.pacman_dir)

        self.assertEqual(self.app.status_var.get(), "Pac-Man Runner (External Camera) launched.")

    @patch("subprocess.Popen")
    def test_backward_compatible_run_pacman_auto(self, mock_popen):
        """Verify run_pacman_auto backward compatibility with both mode values."""
        p_game = MagicMock()
        p_run = MagicMock()
        mock_popen.side_effect = [p_game, p_run, p_run]

        # Default mode: in_computer
        res1 = self.app.run_pacman_auto()
        self.assertEqual(res1, (p_game, p_run))

        # Explicit mode: external
        res2 = self.app.run_pacman_auto(mode="external")
        self.assertEqual(res2, p_run)


class TestLauncherRapidSequentialStress(BaseLauncherTestCase):
    """Stress testing rapid, burst, and spam invocations."""

    @patch("subprocess.Popen")
    def test_rapid_50x_in_computer_invocations(self, mock_popen):
        """Execute 50 rapid sequential calls to in-computer launcher."""
        mock_popen.return_value = MagicMock()
        for i in range(50):
            p1, p2 = self.app.run_pacman_auto_in_computer()
            self.assertIsNotNone(p1)
            self.assertIsNotNone(p2)
        self.assertEqual(mock_popen.call_count, 100)

    @patch("subprocess.Popen")
    def test_rapid_50x_external_invocations(self, mock_popen):
        """Execute 50 rapid sequential calls to external launcher."""
        mock_popen.return_value = MagicMock()
        for i in range(50):
            p = self.app.run_pacman_auto_external()
            self.assertIsNotNone(p)
        self.assertEqual(mock_popen.call_count, 50)

    @patch("subprocess.Popen")
    def test_rapid_alternating_menu_invoke_stress(self, mock_popen):
        """Execute 50 alternating menu invokes (0 and 1)."""
        mock_popen.return_value = MagicMock()
        for _ in range(50):
            self.app.auto_menu.invoke(0)  # spawns 2
            self.app.auto_menu.invoke(1)  # spawns 1
        self.assertEqual(mock_popen.call_count, 150)


class TestRunScriptEdgeCases(BaseLauncherTestCase):
    """Test adversarial edge cases in run_script."""

    @patch("tkinter.messagebox.showerror")
    def test_nonexistent_script(self, mock_error):
        """Verify handling of missing script file."""
        res = self.app.run_script("phantom_file.py", self.app.pacman_dir)
        self.assertIsNone(res)
        mock_error.assert_called_once()
        title, msg = mock_error.call_args[0]
        self.assertEqual(title, "Error")
        self.assertIn("File not found", msg)

    @patch("tkinter.messagebox.showerror")
    def test_nonexistent_folder(self, mock_error):
        """Verify handling of invalid directory."""
        fake_dir = os.path.join(self.app.base_dir, "ghost_dir_99999")
        res = self.app.run_script("pacman_game.py", fake_dir)
        self.assertIsNone(res)
        mock_error.assert_called_once()
        self.assertIn("File not found", mock_error.call_args[0][1])

    @patch("tkinter.messagebox.showerror")
    @patch("subprocess.Popen", side_effect=OSError("Windows error: 5 Access is denied"))
    def test_popen_oserror_handling(self, mock_popen, mock_error):
        """Verify handling when subprocess.Popen raises OSError."""
        res = self.app.run_script("pacman_game.py", self.app.pacman_dir)
        self.assertIsNone(res)
        mock_error.assert_called_once()
        self.assertEqual(mock_error.call_args[0][0], "Execution Error")
        self.assertEqual(self.app.status_var.get(), "Ready")

    @patch("tkinter.messagebox.showerror")
    @patch("subprocess.Popen", side_effect=TypeError("can only concatenate str (not 'int') to str"))
    def test_non_string_arguments_handling(self, mock_popen, mock_error):
        """Verify handling when non-string arguments cause Popen TypeError."""
        res = self.app.run_script("pacman_game.py", self.app.pacman_dir, extra_args=[999])
        self.assertIsNone(res)
        mock_error.assert_called_once()
        self.assertEqual(self.app.status_var.get(), "Ready")

    @patch("subprocess.Popen")
    def test_arguments_with_spaces_and_quotes(self, mock_popen):
        """Verify arguments with spaces and quotes are passed directly without mangling."""
        mock_popen.return_value = MagicMock()
        special_args = ["--title", "Pac-Man Arcade Game", "--custom='quoted value'"]
        self.app.run_script("pacman_game.py", self.app.pacman_dir, extra_args=special_args)
        cmd_sent = mock_popen.call_args[0][0]
        self.assertEqual(cmd_sent[2:], special_args)

    @patch("tkinter.messagebox.showerror")
    def test_in_computer_game_missing_partial_behavior(self, mock_error):
        """Adversarial check: what happens if pacman_game.py is missing?
        Game fails, but runner is still attempted and status string is set."""
        with patch.object(self.app, "run_script") as mock_rs:
            mock_runner_proc = MagicMock()
            mock_rs.side_effect = [None, mock_runner_proc]
            res = self.app.run_pacman_auto_in_computer()
            self.assertEqual(res, (None, mock_runner_proc))
            self.assertEqual(self.app.status_var.get(), "Pac-Man Game & Runner (In-Computer) launched.")


class TestLiveProcessSpawning(BaseLauncherTestCase):
    """Empirical verification with actual operating system processes."""

    def test_real_pacman_runner_help_flag(self):
        """Execute pacman_runner.py with --help as a real OS process."""
        proc = self.app.run_script("pacman_runner.py", self.app.pacman_dir, extra_args=["--help"])
        self.assertIsNotNone(proc)
        self.assertIsInstance(proc, subprocess.Popen)
        stdout, stderr = proc.communicate(timeout=5)
        self.assertEqual(proc.returncode, 0)

    def test_real_subprocess_termination(self):
        """Spawn a python sleep process via run_script and cleanly terminate it."""
        # Execute python -c "import time; time.sleep(10)" by running python on a real script
        proc = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(10)"], cwd=self.app.pacman_dir)
        self.assertIsNone(proc.poll())  # Should be running
        proc.terminate()
        proc.wait(timeout=5)
        self.assertIsNotNone(proc.poll())  # Terminated successfully


if __name__ == "__main__":
    unittest.main()
