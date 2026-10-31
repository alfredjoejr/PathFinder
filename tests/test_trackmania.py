"""
Tests for trackmania/trackmania_runner.py — vision decisions on synthetic
road frames and the stepper-wheel position controller.
"""

import os
import sys
import time
import unittest
from unittest import mock

import cv2
import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "trackmania"))
sys.path.insert(0, ROOT)

from trackmania_runner import VisionEngine, WheelStepperController  # noqa: E402


def make_road(shift_far=0, w=640, h=480):
    """Green grass with a grey road trapezoid; shift_far bends the far end (px)."""
    img = np.zeros((h, w, 3), np.uint8)
    img[:] = (40, 140, 40)                       # grass (BGR)
    img[: int(h * 0.4)] = (230, 180, 120)        # sky
    near_l, near_r = int(w * 0.25), int(w * 0.75)
    far_l, far_r = int(w * 0.45) + shift_far, int(w * 0.55) + shift_far
    pts = np.array([[near_l, h], [near_r, h], [far_r, int(h * 0.4)], [far_l, int(h * 0.4)]], np.int32)
    cv2.fillPoly(img, [pts], (90, 90, 90))       # asphalt
    return img


class TestVision(unittest.TestCase):
    def setUp(self):
        self.v = VisionEngine()

    def run_frames(self, frame, n=5):
        out = None
        t = 1000.0
        for _ in range(n):
            t += 0.033
            out = self.v.analyze(frame, now=t)
        return out

    def test_straight_road(self):
        action, steer, throttle, (off, curv, cov), dbg = self.run_frames(make_road(0))
        self.assertEqual(action, "STRAIGHT")
        self.assertLess(abs(steer), 0.08)
        self.assertTrue(throttle)
        self.assertGreater(cov, 10)
        self.assertIsNotNone(dbg)

    def test_left_curve_steers_left(self):
        action, steer, *_ = self.run_frames(make_road(-200))
        self.assertEqual(action, "LEFT")
        self.assertLess(steer, 0)

    def test_right_curve_steers_right(self):
        action, steer, *_ = self.run_frames(make_road(+200))
        self.assertEqual(action, "RIGHT")
        self.assertGreater(steer, 0)

    def test_sharp_curve_releases_throttle(self):
        self.v.brake_curve = 0.3
        _, _, throttle, (_, curv, _), _ = self.run_frames(make_road(260))
        self.assertGreater(curv, 0.3)
        self.assertFalse(throttle)

    def test_edge_method_runs(self):
        self.v.method = "EDGE"
        action, steer, throttle, metrics, dbg = self.run_frames(make_road(0))
        self.assertIn(action, ("LEFT", "RIGHT", "STRAIGHT", "LOST"))
        self.assertTrue(-1.0 <= steer <= 1.0)

    def test_stuck_detection(self):
        frame = make_road(0)
        t = 0.0
        for _ in range(150):           # ~5 s of identical frames
            t += 0.033
            self.v.analyze(frame, now=t)
        self.assertTrue(self.v.stuck)


class TestWheelController(unittest.TestCase):
    def setUp(self):
        self.ctrl = mock.Mock()
        self.w = WheelStepperController(self.ctrl)
        self.w.wheel_range = 600

    def test_turns_right_toward_target(self):
        self.w.tick(0.5)
        self.ctrl.steer_right.assert_called()
        self.assertEqual(self.w.dir, 1)

    def test_turns_left_toward_target(self):
        self.w.tick(-0.5)
        self.ctrl.steer_left.assert_called()
        self.assertEqual(self.w.dir, -1)

    def test_stops_inside_deadband(self):
        self.w.pos = 300.0
        self.w.dir, self.w.hz = 1, 400
        self.w._last = time.time()
        self.w.tick(0.5)                # target 300 → within deadband
        self.ctrl.steer_stop.assert_called()
        self.assertEqual(self.w.dir, 0)

    def test_recentres_on_straight(self):
        self.w.pos = 200.0
        self.w._last = time.time()
        self.w.tick(0.0)
        self.ctrl.steer_left.assert_called()

    def test_position_integration(self):
        self.w.dir, self.w.hz = 1, 500
        self.w._last = time.time() - 0.2
        self.w._integrate()
        self.assertAlmostEqual(self.w.pos, 100, delta=15)


class TestLauncherButton(unittest.TestCase):
    def test_trackmania_route(self):
        import main
        app = main.AILauncher.__new__(main.AILauncher)
        app.trackmania_dir = os.path.join(ROOT, "trackmania")
        with mock.patch.object(main.AILauncher, "run_script") as rs:
            app.run_trackmania()
            rs.assert_called_once_with("trackmania_runner.py", app.trackmania_dir)
        self.assertTrue(os.path.exists(os.path.join(app.trackmania_dir, "trackmania_runner.py")))


if __name__ == "__main__":
    unittest.main()

