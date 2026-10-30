"""
tests/test_capture_stress.py
Adversarial stress tests for CLI argument parsing, screen/camera capture abstraction,
and vision frame conversion in pacman/pacman_runner.py.
"""

import os
import sys
import unittest
from unittest.mock import patch, MagicMock
import numpy as np
from PIL import Image

# Ensure project root is in sys.path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import pacman.pacman_runner as runner


class TestCLIParsingStress(unittest.TestCase):
    """Stress tests for runner.parse_args."""

    def test_default_fallbacks(self):
        """CLI with empty arguments should default to capture_mode='camera' and camera=0."""
        args = runner.parse_args([])
        self.assertEqual(args.capture_mode, "camera")
        self.assertEqual(args.camera, 0)

    def test_screen_capture_mode(self):
        """CLI with --capture-mode screen should parse correctly."""
        args = runner.parse_args(["--capture-mode", "screen"])
        self.assertEqual(args.capture_mode, "screen")
        self.assertEqual(args.camera, 0)

    def test_screen_capture_mode_underscore(self):
        """CLI with --capture_mode screen alias should parse correctly."""
        args = runner.parse_args(["--capture_mode", "screen"])
        self.assertEqual(args.capture_mode, "screen")

    def test_camera_mode_with_custom_index(self):
        """CLI with --capture-mode camera --camera 3 should parse correctly."""
        args = runner.parse_args(["--capture-mode", "camera", "--camera", "3"])
        self.assertEqual(args.capture_mode, "camera")
        self.assertEqual(args.camera, 3)

    def test_invalid_capture_mode_raises_system_exit(self):
        """CLI with invalid capture mode should reject via SystemExit."""
        with patch("sys.stderr"):
            with self.assertRaises(SystemExit) as cm:
                runner.parse_args(["--capture-mode", "virtual"])
            self.assertNotEqual(cm.exception.code, 0)

    def test_invalid_capture_mode_empty_raises_system_exit(self):
        """CLI with --capture-mode and no value should reject via SystemExit."""
        with patch("sys.stderr"):
            with self.assertRaises(SystemExit) as cm:
                runner.parse_args(["--capture-mode"])
            self.assertNotEqual(cm.exception.code, 0)

    def test_invalid_camera_index_raises_system_exit(self):
        """CLI with non-integer --camera should reject via SystemExit."""
        with patch("sys.stderr"):
            with self.assertRaises(SystemExit) as cm:
                runner.parse_args(["--camera", "not_a_number"])
            self.assertNotEqual(cm.exception.code, 0)

    def test_float_camera_index_raises_system_exit(self):
        """CLI with float --camera should reject via SystemExit."""
        with patch("sys.stderr"):
            with self.assertRaises(SystemExit) as cm:
                runner.parse_args(["--camera", "1.5"])
            self.assertNotEqual(cm.exception.code, 0)

    def test_uppercase_capture_mode_raises_system_exit(self):
        """CLI with uppercase mode e.g. SCREEN should reject via SystemExit."""
        with patch("sys.stderr"):
            with self.assertRaises(SystemExit) as cm:
                runner.parse_args(["--capture-mode", "SCREEN"])
            self.assertNotEqual(cm.exception.code, 0)

    def test_repeated_capture_mode_overrides_to_last(self):
        """CLI with multiple --capture-mode flags should resolve to the last supplied value."""
        args = runner.parse_args(["--capture-mode", "camera", "--capture-mode", "screen"])
        self.assertEqual(args.capture_mode, "screen")

    def test_extra_unrecognized_args_raises_system_exit(self):
        """CLI with unrecognized extra arguments should reject via SystemExit."""
        with patch("sys.stderr"):
            with self.assertRaises(SystemExit) as cm:
                runner.parse_args(["--capture-mode", "screen", "--extra-unknown-flag"])
            self.assertNotEqual(cm.exception.code, 0)


class TestVisionEngineCaptureStress(unittest.TestCase):
    """Stress tests for VisionEngine capture mechanisms."""

    def setUp(self):
        self.engine = runner.VisionEngine(capture_mode="screen")

    def tearDown(self):
        self.engine.stop()
        self.engine.close_camera()

    def test_grab_when_game_window_does_not_exist(self):
        """When Pac-Man window does not exist, grab_screen should fallback to full screen grab."""
        with patch("pacman.pacman_runner.pygetwindow") as mock_pw, \
             patch("pacman.pacman_runner.ImageGrab.grab") as mock_grab:
            # Simulate window not found
            mock_pw.getWindowsWithTitle.return_value = []
            synthetic_img = Image.new("RGB", (640, 480), color=(10, 20, 30))
            mock_grab.return_value = synthetic_img

            frame = self.engine.grab_screen()

            # Verify ImageGrab was called with bbox=None (full screen)
            mock_grab.assert_called_once_with(bbox=None)
            self.assertIsInstance(frame, np.ndarray)
            self.assertEqual(frame.shape, (480, 640, 3))
            self.assertEqual(frame.dtype, np.uint8)
            # In BGR, color (10, 20, 30) RGB becomes (30, 20, 10)
            self.assertEqual(tuple(frame[0, 0]), (30, 20, 10))

    def test_grab_when_pygetwindow_is_none(self):
        """When pygetwindow module is None, grab_screen should fallback to full screen grab."""
        with patch("pacman.pacman_runner.pygetwindow", None), \
             patch("pacman.pacman_runner.ImageGrab.grab") as mock_grab:
            synthetic_img = Image.new("RGB", (640, 480), color=(50, 60, 70))
            mock_grab.return_value = synthetic_img

            frame = self.engine.grab_screen()

            mock_grab.assert_called_once_with(bbox=None)
            self.assertEqual(frame.shape, (480, 640, 3))
            self.assertEqual(frame.dtype, np.uint8)

    def test_grab_when_window_exists_active(self):
        """When Pac-Man window exists and is active, grab_screen should use window bounding box."""
        mock_win = MagicMock()
        mock_win.width = 640
        mock_win.height = 480
        mock_win.left = 100
        mock_win.top = 150
        mock_win.right = 740
        mock_win.bottom = 630
        mock_win.isMinimized = False

        with patch("pacman.pacman_runner.pygetwindow") as mock_pw, \
             patch("pacman.pacman_runner.ImageGrab.grab") as mock_grab:
            mock_pw.getWindowsWithTitle.return_value = [mock_win]
            synthetic_img = Image.new("RGB", (640, 480), color=(0, 100, 200))
            mock_grab.return_value = synthetic_img

            frame = self.engine.grab_screen()

            mock_grab.assert_called_once_with(bbox=(100, 150, 740, 630))
            self.assertEqual(frame.shape, (480, 640, 3))
            self.assertEqual(frame.dtype, np.uint8)

    def test_grab_when_window_minimized(self):
        """When Pac-Man window is minimized, bbox should fallback to None (full screen)."""
        mock_win = MagicMock()
        mock_win.width = 640
        mock_win.height = 480
        mock_win.left = -32000
        mock_win.top = -32000
        mock_win.right = -31360
        mock_win.bottom = -31520
        mock_win.isMinimized = True

        with patch("pacman.pacman_runner.pygetwindow") as mock_pw, \
             patch("pacman.pacman_runner.ImageGrab.grab") as mock_grab:
            mock_pw.getWindowsWithTitle.return_value = [mock_win]
            mock_grab.return_value = Image.new("RGB", (320, 240), color=(0, 0, 0))

            frame = self.engine.grab_screen()

            mock_grab.assert_called_once_with(bbox=None)
            self.assertEqual(frame.shape, (240, 320, 3))

    def test_grab_when_imagegrab_raises_oserror(self):
        """When ImageGrab.grab raises OSError, grab_screen must catch and return black frame (480, 640, 3) uint8."""
        with patch("pacman.pacman_runner.ImageGrab.grab", side_effect=OSError("screen grab failed")):
            frame = self.engine.grab_screen()

            self.assertIsInstance(frame, np.ndarray)
            self.assertEqual(frame.shape, (480, 640, 3))
            self.assertEqual(frame.dtype, np.uint8)
            self.assertTrue(np.all(frame == 0), "Fallback frame must be completely black")

    def test_grab_when_imagegrab_raises_unexpected_exception(self):
        """When ImageGrab.grab raises any unexpected exception, grab_screen must not crash."""
        with patch("pacman.pacman_runner.ImageGrab.grab", side_effect=RuntimeError("DirectX device lost")):
            frame = self.engine.grab_screen()

            self.assertIsInstance(frame, np.ndarray)
            self.assertEqual(frame.shape, (480, 640, 3))
            self.assertEqual(frame.dtype, np.uint8)
            self.assertTrue(np.all(frame == 0))

    def test_grab_when_pygetwindow_raises_exception(self):
        """When pygetwindow raises an exception querying windows, grab_screen must not crash."""
        with patch("pacman.pacman_runner.pygetwindow") as mock_pw:
            mock_pw.getWindowsWithTitle.side_effect = Exception("PyGetWindow internal fault")
            frame = self.engine.grab_screen()

            self.assertIsInstance(frame, np.ndarray)
            self.assertEqual(frame.shape, (480, 640, 3))
            self.assertEqual(frame.dtype, np.uint8)
            self.assertTrue(np.all(frame == 0))

    def test_grab_when_window_negative_coordinates(self):
        """When Pac-Man window has negative coordinates, ImageGrab OSError triggers safe black fallback."""
        mock_win = MagicMock()
        mock_win.width = 640
        mock_win.height = 480
        mock_win.left = -500
        mock_win.top = -100
        mock_win.right = 140
        mock_win.bottom = 380
        mock_win.isMinimized = False

        with patch("pacman.pacman_runner.pygetwindow") as mock_pw, \
             patch("pacman.pacman_runner.ImageGrab.grab", side_effect=OSError("screen grab failed")):
            mock_pw.getWindowsWithTitle.return_value = [mock_win]
            frame = self.engine.grab_screen()

            self.assertIsInstance(frame, np.ndarray)
            self.assertEqual(frame.shape, (480, 640, 3))
            self.assertEqual(frame.dtype, np.uint8)
            self.assertTrue(np.all(frame == 0))

    def test_grab_when_imagegrab_returns_zero_dimension_image(self):
        """When ImageGrab returns a 0x0 image, cv2.cvtColor error triggers safe black fallback."""
        with patch("pacman.pacman_runner.ImageGrab.grab", return_value=Image.new("RGB", (0, 0))):
            frame = self.engine.grab_screen()

            self.assertIsInstance(frame, np.ndarray)
            self.assertEqual(frame.shape, (480, 640, 3))
            self.assertEqual(frame.dtype, np.uint8)
            self.assertTrue(np.all(frame == 0))


class TestColorConversionStress(unittest.TestCase):
    """Stress tests verifying color format handling and channel conversion."""

    def setUp(self):
        self.engine = runner.VisionEngine(capture_mode="screen")

    def test_rgb_to_bgr_conversion(self):
        """RGB PIL image must be converted to 3-channel BGR ndarray."""
        # Pure Red in RGB: (255, 0, 0)
        img = Image.new("RGB", (64, 64), color=(255, 0, 0))
        with patch("pacman.pacman_runner.ImageGrab.grab", return_value=img):
            frame = self.engine.grab_screen()

            self.assertEqual(frame.shape, (64, 64, 3))
            self.assertEqual(frame.dtype, np.uint8)
            # In BGR: Red is at channel index 2, channel 0 (Blue) is 0
            b, g, r = frame[32, 32]
            self.assertEqual(b, 0)
            self.assertEqual(g, 0)
            self.assertEqual(r, 255)

    def test_rgba_to_bgr_conversion(self):
        """RGBA PIL image must drop alpha and convert to 3-channel BGR ndarray."""
        # Pure Green in RGBA: (0, 255, 0, 128)
        img = Image.new("RGBA", (64, 64), color=(0, 255, 0, 128))
        with patch("pacman.pacman_runner.ImageGrab.grab", return_value=img):
            frame = self.engine.grab_screen()

            self.assertEqual(frame.shape, (64, 64, 3))
            self.assertEqual(frame.dtype, np.uint8)
            # In BGR: Green is at channel index 1
            b, g, r = frame[32, 32]
            self.assertEqual(b, 0)
            self.assertEqual(g, 255)
            self.assertEqual(r, 0)

    def test_grayscale_to_bgr_conversion(self):
        """Grayscale (mode 'L') PIL image must be converted to 3-channel BGR ndarray."""
        img = Image.new("L", (64, 64), color=180)
        with patch("pacman.pacman_runner.ImageGrab.grab", return_value=img):
            frame = self.engine.grab_screen()

            self.assertEqual(frame.shape, (64, 64, 3))
            self.assertEqual(frame.dtype, np.uint8)
            b, g, r = frame[32, 32]
            self.assertEqual((b, g, r), (180, 180, 180))

    def test_downstream_analyze_with_black_fallback_frame(self):
        """Downstream _analyze() must handle fallback black frames without throwing exceptions."""
        black_frame = np.zeros((480, 640, 3), dtype=np.uint8)
        action, servos, densities, debug_img = self.engine._analyze(black_frame)

        self.assertIn(action, ["UP", "DOWN", "LEFT", "RIGHT", "IDLE"])
        self.assertEqual(len(servos), 5)
        self.assertEqual(len(densities), 3)
        expected_crop_h = int(480 * self.engine.hud_crop_pct)
        self.assertEqual(debug_img.shape, (expected_crop_h, 640, 3))

    def test_downstream_analyze_with_rgba_converted_frame(self):
        """Downstream _analyze() must handle RGBA converted frames without throwing exceptions."""
        img = Image.new("RGBA", (640, 480), color=(255, 255, 0, 255))  # Yellow background
        with patch("pacman.pacman_runner.ImageGrab.grab", return_value=img):
            frame = self.engine.grab_screen()
            action, servos, densities, debug_img = self.engine._analyze(frame)

            self.assertIn(action, ["UP", "DOWN", "LEFT", "RIGHT", "IDLE"])
            self.assertEqual(len(servos), 5)
            self.assertEqual(len(densities), 3)
            self.assertIsInstance(debug_img, np.ndarray)


class TestCameraOpenBehaviorStress(unittest.TestCase):
    """Stress tests verifying open_camera() behavior across screen vs camera modes."""

    def test_open_camera_in_screen_mode(self):
        """In screen mode, open_camera() must return True immediately without opening cv2.VideoCapture."""
        engine = runner.VisionEngine(capture_mode="screen")
        with patch("cv2.VideoCapture") as mock_vc:
            result = engine.open_camera(index=0)
            self.assertTrue(result)
            mock_vc.assert_not_called()
            self.assertIsNone(engine.cap)

    def test_open_camera_in_camera_mode_device_found(self):
        """In camera mode with working device, open_camera() opens capture and returns True."""
        engine = runner.VisionEngine(capture_mode="camera")
        mock_cap = MagicMock()
        mock_cap.isOpened.return_value = True

        with patch("cv2.VideoCapture", return_value=mock_cap):
            result = engine.open_camera(index=1)
            self.assertTrue(result)
            self.assertIs(engine.cap, mock_cap)

        engine.close_camera()
        mock_cap.release.assert_called_once()
        self.assertIsNone(engine.cap)

    def test_open_camera_in_camera_mode_device_missing(self):
        """In camera mode with missing device, open_camera() returns False and cleans up cap."""
        engine = runner.VisionEngine(capture_mode="camera")
        mock_cap = MagicMock()
        mock_cap.isOpened.return_value = False

        with patch("cv2.VideoCapture", return_value=mock_cap):
            result = engine.open_camera(index=99)
            self.assertFalse(result)
            self.assertIsNone(engine.cap)

    def test_repeated_open_camera_in_screen_mode(self):
        """Repeated calls to open_camera() in screen mode should consistently return True."""
        engine = runner.VisionEngine(capture_mode="screen")
        for _ in range(5):
            self.assertTrue(engine.open_camera(0))
        self.assertIsNone(engine.cap)

    def test_close_camera_when_no_active_capture(self):
        """close_camera() when self.cap is already None must safely no-op."""
        engine = runner.VisionEngine(capture_mode="screen")
        engine.close_camera()
        self.assertIsNone(engine.cap)


class TestVisionEngineLifecycleStress(unittest.TestCase):
    """Stress tests verifying background thread lifecycle under screen and camera modes."""

    def test_screen_mode_background_thread_execution(self):
        """VisionEngine in screen mode should process frames and stop cleanly."""
        engine = runner.VisionEngine(capture_mode="screen")
        try:
            self.assertTrue(engine.open_camera())
            engine.start()
            self.assertTrue(engine.running)
            # Give background thread a moment to grab and analyze at least one frame
            import time
            start_t = time.time()
            while engine.last_frame is None and time.time() - start_t < 1.0:
                time.sleep(0.02)

            self.assertIsNotNone(engine.last_frame)
            self.assertIn(engine.last_action, ["UP", "DOWN", "LEFT", "RIGHT", "IDLE"])
        finally:
            engine.stop()
            self.assertFalse(engine.running)
            self.assertIsNone(engine._thread)

    def test_camera_mode_background_thread_without_camera(self):
        """VisionEngine in camera mode without device should idle without crashing and stop cleanly."""
        engine = runner.VisionEngine(capture_mode="camera")
        try:
            engine.start()
            self.assertTrue(engine.running)
            import time
            time.sleep(0.05)
            self.assertIsNone(engine.last_frame)
        finally:
            engine.stop()
            self.assertFalse(engine.running)
            self.assertIsNone(engine._thread)


class TestAppGUIStress(unittest.TestCase):
    """Stress tests verifying PacmanAutoPilotApp initialization across capture modes."""

    def test_app_init_screen_mode(self):
        """PacmanAutoPilotApp in screen mode initializes with [SCREEN] badge and proper defaults."""
        import tkinter as tk
        root = tk.Tk()
        root.withdraw()
        try:
            app = runner.PacmanAutoPilotApp(root, capture_mode="screen", camera_index=0)
            self.assertEqual(app.capture_mode, "screen")
            self.assertEqual(app.vision.capture_mode, "screen")
            self.assertEqual(app.cam_var.get(), 0)
        finally:
            root.destroy()

    def test_app_init_camera_mode(self):
        """PacmanAutoPilotApp in camera mode initializes with standard camera defaults."""
        import tkinter as tk
        root = tk.Tk()
        root.withdraw()
        try:
            app = runner.PacmanAutoPilotApp(root, capture_mode="camera", camera_index=2)
            self.assertEqual(app.capture_mode, "camera")
            self.assertEqual(app.vision.capture_mode, "camera")
            self.assertEqual(app.cam_var.get(), 2)
        finally:
            root.destroy()


if __name__ == "__main__":
    unittest.main()
