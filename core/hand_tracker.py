"""
MediaPipe HandLandmarker → Observation.  ── FROZEN FILE, DO NOT EDIT ──

Wraps the MediaPipe hand model and turns its raw output into the `Observation`
objects your recognizer consumes.  Adapted from
g1_control/advanced_move/hand_pose_detector.py, extended from three fingers to
all five.
"""
from __future__ import annotations

import math
from pathlib import Path

import cv2
import mediapipe as mp
import numpy as np
from mediapipe.tasks import python as mp_python
from mediapipe.tasks.python import vision

from .observation import FINGER_LANDMARKS, FINGERS, WRIST, Hand, Observation

_DEFAULT_MODEL = Path(__file__).resolve().parents[1] / "models" / "hand_landmarker.task"

# Curl (degrees) below which a finger counts as extended, used to fill
# Hand.extended.  The thumb gets its own value because its curl signal is much
# weaker — it folds across the palm by rotating at the base rather than by
# bending, so a tucked thumb produces far less curl than a tucked finger.
# These are deliberately naive.  Your recognizer is free to ignore
# Hand.extended and threshold Hand.curl itself.
EXTENDED_BELOW_DEG = 70.0
THUMB_EXTENDED_BELOW_DEG = 60.0


def _angle_deg(a, b, c) -> float:
    """Angle at vertex b between rays b->a and b->c, in degrees.

    180 when a-b-c are collinear (joint straight), falling toward 0 as it bends.
    """
    ba = np.asarray(a) - np.asarray(b)
    bc = np.asarray(c) - np.asarray(b)
    denom = float(np.linalg.norm(ba) * np.linalg.norm(bc))
    if denom < 1e-9:
        return 180.0
    return math.degrees(math.acos(float(np.clip(np.dot(ba, bc) / denom, -1.0, 1.0))))


def _finger_curl(world, finger: str) -> float:
    """Total bend of one finger, in degrees.  0 = straight.

    Sum of the bend at the two outer joints, measured on the metric world
    landmarks so the number does not change with camera distance.
    """
    a, b, c, d = (world[i] for i in FINGER_LANDMARKS[finger])
    return (180.0 - _angle_deg(a, b, c)) + (180.0 - _angle_deg(b, c, d))


class HandTracker:
    def __init__(
        self,
        model_path: str | Path = _DEFAULT_MODEL,
        max_hands: int = 2,
        static: bool = False,
        min_detection_confidence: float = 0.5,
    ) -> None:
        """`static=True` treats every frame as an unrelated still image (used by
        --image and the test suite); the default streams video and lets
        MediaPipe track hands across frames."""
        model_path = Path(model_path)
        if not model_path.is_file():
            raise SystemExit(
                f"Hand model not found at {model_path}\n"
                "Download it with:\n"
                "  wget -O models/hand_landmarker.task https://storage.googleapis.com/"
                "mediapipe-models/hand_landmarker/hand_landmarker/float16/latest/"
                "hand_landmarker.task"
            )
        self._static = static
        options = vision.HandLandmarkerOptions(
            base_options=mp_python.BaseOptions(model_asset_path=str(model_path)),
            running_mode=vision.RunningMode.IMAGE if static else vision.RunningMode.VIDEO,
            num_hands=max_hands,
            min_hand_detection_confidence=min_detection_confidence,
            min_hand_presence_confidence=0.5,
            min_tracking_confidence=0.5,
        )
        self._landmarker = vision.HandLandmarker.create_from_options(options)

    def close(self) -> None:
        self._landmarker.close()

    def observe(self, frame: np.ndarray, t: float, dt: float) -> Observation:
        """Run the model on one BGR frame and package the result."""
        h, w = frame.shape[:2]
        mp_image = mp.Image(
            image_format=mp.ImageFormat.SRGB,
            data=cv2.cvtColor(frame, cv2.COLOR_BGR2RGB),
        )
        if self._static:
            result = self._landmarker.detect(mp_image)
        else:
            result = self._landmarker.detect_for_video(mp_image, max(int(t * 1000), 0))

        hands: list[Hand] = []
        frame_diag = math.hypot(w, h) or 1.0

        for image_lm, world_lm, handed in zip(
            result.hand_landmarks, result.hand_world_landmarks, result.handedness
        ):
            lm = [(p.x, p.y, p.z) for p in image_lm]
            world = [(p.x, p.y, p.z) for p in world_lm]
            px = [(int(p[0] * w), int(p[1] * h)) for p in lm]

            xs = [p[0] for p in px]
            ys = [p[1] for p in px]
            bbox = (min(xs), min(ys), max(xs), max(ys))
            scale = math.hypot(bbox[2] - bbox[0], bbox[3] - bbox[1]) / frame_diag

            curl = {f: _finger_curl(world, f) for f in FINGERS}
            extended = {
                f: curl[f] < (THUMB_EXTENDED_BELOW_DEG if f == "thumb" else EXTENDED_BELOW_DEG)
                for f in FINGERS
            }

            side = handed[0].category_name.lower()
            hands.append(
                Hand(
                    side=side if side in ("left", "right") else "unknown",
                    score=float(handed[0].score),
                    curl=curl,
                    extended=extended,
                    lm=lm,
                    world=world,
                    px=px,
                    bbox=bbox,
                    scale=scale,
                )
            )

        # Largest hand first — the one most likely to be the operator's.
        hands.sort(key=lambda hd: hd.scale, reverse=True)
        return Observation(hands=hands, t=t, dt=dt, width=w, height=h)


__all__ = ["HandTracker", "EXTENDED_BELOW_DEG", "THUMB_EXTENDED_BELOW_DEG", "WRIST"]
